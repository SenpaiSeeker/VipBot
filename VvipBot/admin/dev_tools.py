import ast
import asyncio
import base64
import contextlib
import html
import importlib
import inspect
import io
import json
import logging
import os
import platform
import pprint
import random
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime, timedelta
from time import time
from typing import Any, Dict, Optional, Tuple

import aiofiles.os
import pyrogram
from pyrogram import filters
from pyrogram.types import LinkPreviewOptions, Message, ReplyParameters

from .. import command, ctx

if not hasattr(ctx, "eval_history"):
    ctx.eval_history = {
        "last_code": None,
        "last_result": None,
        "last_stdout": None,
        "last_error": None,
        "last_time": None,
    }


def shell(code: str) -> str:
    try:
        return subprocess.check_output(
            code, shell=True, stderr=subprocess.STDOUT, text=True
        )
    except subprocess.CalledProcessError as e:
        return e.output


def get_eval_payload(message: Message) -> str:
    cmd_len = (
        len(message.command) if hasattr(message, "command") and message.command else 0
    )
    text = message.text or message.caption or ""
    if cmd_len > 0:
        prefix_len = len(text.split()[0])
        args = text[prefix_len:].strip()
    else:
        args = ""
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            args = parts[1]
    if args:
        return args
    if message.reply_to_message:
        target_text = (
            message.reply_to_message.text or message.reply_to_message.caption or ""
        )
        return target_text
    return ""


async def resolve_awaitables(obj: Any) -> Any:
    if inspect.iscoroutine(obj) or inspect.isawaitable(obj):
        return await obj
    return obj


def create_exec_scope(
    client: pyrogram.Client, message: Message, **kwargs
) -> Dict[str, Any]:
    if not hasattr(ctx, "kwargs"):
        ctx.kwargs = {}
    scope = {
        "client": client,
        "c": client,
        "app": client,
        "message": message,
        "m": message,
        "msg": message,
        "r": message.reply_to_message,
        "rep": message.reply_to_message,
        "ctx": ctx,
        "db": ctx.db,
        "manager": getattr(ctx, "manager", None),
        "bots": ctx.manager.running_bots if hasattr(ctx, "manager") else None,
        "asyncio": asyncio,
        "os": os,
        "sys": sys,
        "re": re,
        "json": json,
        "random": random,
        "datetime": datetime,
        "timedelta": timedelta,
        "traceback": traceback,
        "io": io,
        "base64": base64,
        "logging": logging,
        "platform": platform,
        "shutil": shutil,
        "inspect": inspect,
        "importlib": importlib,
        "pyrogram": pyrogram,
        "shell": shell,
        "sh": shell,
        "print": pprint.pformat,
        "chat": message.chat,
        "user": message.from_user if message.from_user else client.me,
    }
    scope.update(kwargs)
    return scope


async def aexec(code: str, client: pyrogram.Client, message: Message, **kwargs) -> Any:
    exec_scope = create_exec_scope(client, message, **kwargs)
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        tree.body[-1] = ast.Return(value=tree.body[-1].value)
    func_def = ast.AsyncFunctionDef(
        name="__aexec",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=k) for k in exec_scope.keys()],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
            vararg=None,
            kwarg=ast.arg(arg="kwargs"),
        ),
        body=tree.body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    ast.fix_missing_locations(func_def)
    module = ast.Module(body=[func_def], type_ignores=[])
    compiled_src = compile(module, filename="<ast>", mode="exec")
    exec(compiled_src, exec_scope)
    runner = exec_scope["__aexec"]
    result = await runner(**exec_scope)
    return await resolve_awaitables(result)


def format_output(
    client: pyrogram.Client,
    code: str,
    result: Any,
    stdout_val: str,
    stderr_val: str,
    exc_str: Optional[str],
    exec_time: float,
) -> Tuple[str, str, str]:
    final_output = ""
    status_header = "Success"
    if exc_str:
        final_output = exc_str.strip()
        status_header = "Error"
    elif stderr_val:
        final_output = stderr_val.strip()
        status_header = "Stderr"
    elif stdout_val:
        final_output = stdout_val.strip()
        if result is not None:
            final_output += f"\n---\nReturn: {str(result)}"
    elif result is not None:
        final_output = str(result).strip()
    else:
        final_output = "None"

    escaped_code = html.escape(code)
    escaped_output = html.escape(final_output)

    out_len_limit = 777
    short_output = (
        final_output[:out_len_limit] + "..."
        if len(final_output) > out_len_limit
        else final_output
    )
    escaped_short_output = (
        escaped_output[:out_len_limit] + "..."
        if len(escaped_output) > out_len_limit
        else escaped_output
    )

    display_text = f"{client.ns.emoji.md('zap')} **Eval Result**\n\n"
    display_text += client.ns.table.md(
        ["Info", "Nilai"],
        [["Status", status_header], ["Waktu", f"`{exec_time:.4f}s`"]],
    )
    display_text += f"\n\n**{client.ns.emoji.md('zap')} Input:**\n"
    display_text += f"```python\n{code}\n```\n\n"
    display_text += f"**{client.ns.emoji.md('laptop')} Output:**\n"
    display_text += f"```\n{short_output}\n```"

    caption_text = f"{client.ns.emoji.zap} <b>Input:</b>\n"
    caption_text += (
        f"<pre><code class='language-python'>{escaped_code}</code></pre>\n\n"
    )
    caption_text += f"{client.ns.emoji.laptop} <b>Output ({status_header}):</b>\n"
    caption_text += f"<pre><code>{escaped_short_output}</code></pre>\n\n"
    caption_text += (
        f"{client.ns.emoji.hourglass} <b>Time: </b><code>{exec_time:.4f}s</code>"
    )

    return display_text, caption_text, final_output


async def execute_and_format(
    client: pyrogram.Client, message: Message, code: str, **kwargs
) -> Tuple[str, str, Any, Optional[io.BytesIO]]:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = None
    exc_traceback = None
    start_time = time()

    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(
            stderr_capture
        ):
            result = await asyncio.wait_for(
                aexec(code, client, message, **kwargs), timeout=60.0
            )
    except asyncio.TimeoutError:
        exc_traceback = (
            f"{client.ns.emoji.cross_mark} TimeoutError: Execution exceeded 60 seconds."
        )
    except asyncio.CancelledError:
        exc_traceback = "CancelledError: Execution was cancelled."
    except Exception:
        exc_traceback = traceback.format_exc()

    end_time = time()
    execution_time = end_time - start_time
    stdout_val = stdout_capture.getvalue()
    stderr_val = stderr_capture.getvalue()

    ctx.eval_history.update(
        {
            "last_code": code,
            "last_result": str(result) if result is not None else None,
            "last_stdout": stdout_val,
            "last_error": exc_traceback or stderr_val,
            "last_time": execution_time,
        }
    )

    display_text, caption_text, raw_output = format_output(
        client,
        code,
        result,
        stdout_val,
        stderr_val,
        exc_traceback,
        execution_time,
    )

    document = None
    if len(raw_output) > 777:
        document = io.BytesIO(str.encode(raw_output))
        document.name = "output.txt"

    layout = [
        [
            {
                "text": "Run Again",
                "callback_data": f"eval_run_{message.chat.id}_{message.id}",
                "style": "green",
            },
            {
                "text": "Delete",
                "callback_data": f"eval_del_{message.chat.id}_{message.id}",
                "style": "red",
            },
        ]
    ]
    keyboard = client.ns.telegram.button.build_button_grid(layout)

    return display_text, caption_text, keyboard, document


@command(lambda ctx: filters.command("eval") & filters.user(ctx.owner_id))
async def eval_bot_handler(client: pyrogram.Client, message: Message):
    code = get_eval_payload(message)
    if not code:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} Berikan kode untuk dievaluasi atau balas ke sebuah pesan."
            )
        )

    status_msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=f"{client.ns.emoji.md('repeat')} `Memproses kode...`"
        )
    )
    try:
        text, caption_text, keyboard, document = await execute_and_format(
            client, message, code, update=message
        )
        if document:
            await status_msg.delete()
            await client.send_document(
                chat_id=message.chat.id,
                document=document,
                caption=caption_text,
                reply_markup=keyboard,
                reply_parameters=ReplyParameters(message_id=message.id),
            )
        else:
            await status_msg.edit_text(
                rich_message=pyrogram.types.InputRichMessage(markdown=text),
                reply_markup=keyboard,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
    except Exception:
        error_text = (
            f"{client.ns.emoji.md('cross_mark')} **Kesalahan Handler**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal'], ['Traceback', f'```\n{traceback.format_exc()}\n```']])}"
        )
        if status_msg:
            try:
                await status_msg.edit_text(
                    rich_message=pyrogram.types.InputRichMessage(markdown=error_text)
                )
            except Exception:
                await message.reply_rich(
                    pyrogram.types.InputRichMessage(markdown=error_text)
                )
        else:
            await message.reply_rich(
                pyrogram.types.InputRichMessage(markdown=error_text)
            )


@command(
    lambda ctx: filters.regex(r"^eval_") & filters.user(ctx.owner_id),
    handler_type="callback",
)
async def eval_callback_handler(
    client: pyrogram.Client, query: pyrogram.types.CallbackQuery
):
    data = query.data.split("_")
    if len(data) < 4:
        return

    action = data[1]
    chat_id = int(data[2])
    message_id = int(data[3])

    if action == "del":
        try:
            await client.delete_messages(chat_id, [message_id, query.message.id])
        except Exception:
            await query.answer("Tidak bisa menghapus pesan.")

    elif action == "run":
        try:
            trigger_message = await client.get_messages(chat_id, message_id)
            code = get_eval_payload(trigger_message)
            if not code:
                return await query.answer(
                    "Kode tidak ditemukan untuk dijalankan kembali.", show_alert=True
                )

            await query.answer("Menjalankan kembali kode...")

            text, caption_text, keyboard, document = await execute_and_format(
                client,
                trigger_message,
                code,
                update=query,
            )

            if code.endswith("return"):
                return

            is_current_msg_media = bool(query.message.document or query.message.photo)

            if document:
                if is_current_msg_media:
                    await query.edit_message_media(
                        media=pyrogram.types.InputMediaDocument(
                            media=document, caption=caption_text
                        ),
                        reply_markup=keyboard,
                    )
                else:
                    await query.message.delete()
                    await client.send_document(
                        chat_id=chat_id,
                        document=document,
                        caption=caption_text,
                        reply_markup=keyboard,
                        reply_parameters=ReplyParameters(message_id=message_id),
                    )
            else:
                if is_current_msg_media:
                    await query.message.delete()
                    await client.send_rich_message(
                        chat_id=chat_id,
                        rich_message=pyrogram.types.InputRichMessage(markdown=text),
                        reply_markup=keyboard,
                        reply_parameters=ReplyParameters(message_id=message_id),
                    )
                else:
                    await query.edit_message_text(
                        rich_message=pyrogram.types.InputRichMessage(markdown=text),
                        reply_markup=keyboard,
                        link_preview_options=LinkPreviewOptions(is_disabled=True),
                    )
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)


@command(lambda ctx: filters.command("restore") & filters.user(ctx.owner_id))
async def restore_database_handler(client, message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('exclamation')} **Cara Penggunaan Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Cara penggunaan salah'], ['Cara', 'Balas (reply) ke file backup `.zip` yang dikirim oleh bot dengan perintah ini']])}"
                )
            )
        )
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".zip"):
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format File Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Format file salah'], ['Syarat', 'Hanya file backup dengan format `.zip` yang bisa dipulihkan']])}"
                )
            )
        )
    status_msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('hourglass')} **Memproses Backup**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Mendownload & mengekstrak file backup']])}"
            )
        )
    )
    downloaded_zip_path = None
    try:
        downloaded_zip_path = await client.download_media(message.reply_to_message)

        def _do_restore():
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(downloaded_zip_path, "r") as zf:
                    if not zf.namelist():
                        raise ValueError("File .zip ini kosong atau rusak.")
                    zf.extractall(path=temp_dir)
                restored_files = []
                current_db_path = getattr(
                    ctx.db, "data_file", getattr(ctx.db, "db_file", None)
                )
                if not current_db_path:
                    raise ValueError("Tidak dapat menentukan path database aktif.")
                db_ext = ".db" if current_db_path.endswith(".db") else ".json"
                for root, _, files in os.walk(temp_dir):
                    for filename in files:
                        if filename.endswith(db_ext):
                            source_path = os.path.join(root, filename)
                            shutil.move(source_path, current_db_path)
                            restored_files.append(os.path.basename(current_db_path))
                            break
                    if restored_files:
                        break
                if not restored_files:
                    raise ValueError(
                        f"Tidak ada file database ({db_ext}) yang valid ditemukan dalam arsip."
                    )
                return restored_files

        restored_files = await asyncio.to_thread(_do_restore)
        restored_names = ", ".join(restored_files)
        await status_msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('white_check_mark')} **Pemulihan Berhasil!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Database', f'`{restored_names}`'], ['Status', 'Telah dipulihkan'], ['Penting', 'Mohon **restart** bot agar dapat menggunakan database baru']])}"
            )
        )
        ctx.log.print(
            f"{ctx.log.GREEN}File-file berikut dipulihkan: {', '.join(restored_files)} oleh admin."
        )
    except Exception as e:
        await status_msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Pemulihan Gagal!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Pemulihan gagal'], ['Error', f'`{e}`']])}"
            )
        )
        ctx.log.print(f"{ctx.log.RED}Restore failed: {e}")
    finally:
        if downloaded_zip_path and await aiofiles.os.path.exists(downloaded_zip_path):
            await aiofiles.os.remove(downloaded_zip_path)


@command(lambda ctx: filters.command("tfdatabase") & filters.user(ctx.owner_id))
async def tfdatabase_command_handler(client, message):
    args = message.command
    if len(args) != 3:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Gunakan', '`/tfdatabase <source_id>:<source_db> <target_id>:<target_db>`'], ['Contoh', '`/tfdatabase 123455:databaseV1 666999:databaseV2`']])}"
                )
            )
        )
    source_part = args[1]
    target_part = args[2]
    try:
        source_id_str, source_db_name = source_part.split(":")
        target_id_str, target_db_name = target_part.split(":")
        source_id = int(source_id_str)
        target_id = int(target_id_str)
    except Exception:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Format', '`ID:NAMA_DB`'], ['Contoh', '`/tfdatabase 123455:databaseV1 666999:databaseV2`']])}"
                )
            )
        )
    msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('repeat')} **Memproses Transfer**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Memproses transfer database']])}"
            )
        )
    )
    try:
        from helpers.database import DataBase

        source_db = (
            ctx.db
            if source_db_name == ctx.db.file_name
            else DataBase(
                storage_type=ctx.db.storage_type,
                file_name=source_db_name,
                keys_encrypt=ctx.db.keys_encrypt,
                method_encrypt=ctx.db.method_encrypt,
                auto_backup=False,
            )
        )
        target_db = (
            ctx.db
            if target_db_name == ctx.db.file_name
            else DataBase(
                storage_type=ctx.db.storage_type,
                file_name=target_db_name,
                keys_encrypt=ctx.db.keys_encrypt,
                method_encrypt=ctx.db.method_encrypt,
                auto_backup=False,
            )
        )
        source_data = await source_db._get_user_vars(source_id)
        if not source_data:
            if source_db != ctx.db:
                await source_db.close_async()
            if target_db != ctx.db:
                await target_db.close_async()
            return await msg.edit_text(
                rich_message=pyrogram.types.InputRichMessage(
                    markdown=f"{client.ns.emoji.md('cross_mark')} Data sumber tidak ditemukan pada database."
                )
            )
        await target_db._set_user_vars(target_id, source_data)
        if source_db != ctx.db:
            await source_db.close_async()
        if target_db != ctx.db:
            await target_db.close_async()
        await msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('white_check_mark')} **Transfer Database Berhasil!**\n\n"
                f"**Sumber:** `{source_id}` (`{source_db_name}`)\n"
                f"**Tujuan:** `{target_id}` (`{target_db_name}`)\n\n"
                f"Semua data berhasil disalin secara lengkap."
            )
        )
    except Exception as e:
        await msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Transfer Gagal**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Terjadi kesalahan saat mentransfer database'], ['Error', f'`{e}`']])}"
                )
            )
        )


@command(lambda ctx: filters.command("tfbot") & filters.user(ctx.owner_id))
async def tfbot_command_handler(client, message):
    args = message.command
    if len(args) != 4:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Gunakan', '`/tfbot <id_bot> <source_db> <target_db>`'], ['Contoh', '`/tfbot 123456789 vvip_database vvip_databaseV2`']])}"
                )
            )
        )
    try:
        bot_id = int(args[1])
    except ValueError:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Detail', 'ID Bot harus berupa angka']])}"
                )
            )
        )
    source_db_name = args[2]
    target_db_name = args[3]
    msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('repeat')} **Memproses Migrasi**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Memproses migrasi bot']])}"
            )
        )
    )
    try:
        from helpers.database import DataBase

        source_db = (
            ctx.db
            if source_db_name == ctx.db.file_name
            else DataBase(
                storage_type=ctx.db.storage_type,
                file_name=source_db_name,
                keys_encrypt=ctx.db.keys_encrypt,
                method_encrypt=ctx.db.method_encrypt,
                auto_backup=False,
            )
        )
        target_db = (
            ctx.db
            if target_db_name == ctx.db.file_name
            else DataBase(
                storage_type=ctx.db.storage_type,
                file_name=target_db_name,
                keys_encrypt=ctx.db.keys_encrypt,
                method_encrypt=ctx.db.method_encrypt,
                auto_backup=False,
            )
        )
        bots_token = await source_db.getBots(is_token=True)
        bots_session = await source_db.getBots(is_token=False)
        all_bots = bots_token + bots_session
        bot_data = next((b for b in all_bots if str(b["name"]) == str(bot_id)), None)
        if not bot_data:
            if source_db != ctx.db:
                await source_db.close_async()
            if target_db != ctx.db:
                await target_db.close_async()
            return await msg.edit_text(
                rich_message=pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Bot Tidak Ditemukan**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Bot ID', f'`{bot_id}`'], ['Status', 'Tidak ditemukan'], ['Database', f'`{source_db_name}`']])}"
                    )
                )
            )
        source_vars = await source_db._get_user_vars(bot_id)
        api_id = bot_data.get("api_id")
        api_hash = bot_data.get("api_hash")
        bot_token = bot_data.get("bot_token")
        session_string = bot_data.get("session_string")
        if bot_token:
            await target_db.saveBot(bot_id, api_id, api_hash, bot_token, is_token=True)
        elif session_string:
            await target_db.saveBot(
                bot_id, api_id, api_hash, session_string, is_token=False
            )
        if source_vars:
            await target_db._set_user_vars(bot_id, source_vars)
        await source_db.removeBot(bot_id)
        await source_db.removeAllVars(bot_id)
        if bot_id in getattr(ctx.manager, "running_bots", {}):
            await ctx.manager.stop_bot(bot_id)
        if source_db != ctx.db:
            await source_db.close_async()
        if target_db != ctx.db:
            await target_db.close_async()
        await msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('white_check_mark')} **Migrasi Bot Berhasil!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Bot ID', f'`{bot_id}`'], ['Dari', f'`{source_db_name}`'], ['Ke', f'`{target_db_name}`'], ['Status', 'Bot beserta seluruh datanya telah dipindahkan dan dihapus dari database lama'], ['Penting', 'Jangan lupa restart bot tujuan agar bot ini segera menyala']])}"
            )
        )
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Error saat tfbot: {e}")


@command(lambda ctx: filters.command("block") & filters.user(ctx.owner_id))
async def block_purchase_handler(client, message):
    args_text = client.ns.telegram.arg.getMessage(message, is_arg=True)
    arg = (args_text or "").strip().lower()

    current = bool(await ctx.db.getVars(ctx.owner_id, "purchase_block") or False)

    def _status_rows(value):
        state = "ON" if value else "OFF"
        return [
            ["Status", f"`{state}`"],
            [
                "Efek ON",
                "Pencatatan dilewati; notifikasi dialihkan ke owner utama; link pembeli tetap dikirim",
            ],
            ["Ubah", "`/block on` atau `/block off`"],
        ]

    if not arg:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('lock')} **Mode Block Pembelian**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], _status_rows(current))}"
            )
        )

    if arg not in ("on", "off"):
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Gunakan', '`/block on` atau `/block off`'], ['Status Saat Ini', f"`{'ON' if current else 'OFF'}`"]])}"
            )
        )

    value = arg == "on"
    await ctx.db.setVars(ctx.owner_id, "purchase_block", value)

    if value:
        title = f"{client.ns.emoji.md('lock')} **Block Mode Diaktifkan**"
        rows = [
            ["Status", "`ON`"],
            ["Notifikasi", "Dialihkan ke owner utama"],
            ["Pencatatan", "Dilewati"],
            ["Link Pembeli", "Tetap dikirim"],
        ]
    else:
        title = f"{client.ns.emoji.md('white_check_mark')} **Block Mode Dinonaktifkan**"
        rows = [
            ["Status", "`OFF`"],
            ["Notifikasi", "Normal"],
            ["Pencatatan", "Normal"],
            ["Link Pembeli", "Tetap dikirim"],
        ]

    await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=f"{title}\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
        )
    )
