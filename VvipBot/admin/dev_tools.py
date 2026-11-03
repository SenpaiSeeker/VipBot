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
import traceback
from datetime import datetime, timedelta, timezone
from time import time
from typing import Any, Dict, Optional, Tuple

import pyrogram
from pyrogram import filters
from pyrogram.types import LinkPreviewOptions, Message, ReplyParameters

from helpers import parse_dt
from helpers.modules import Modules

from .. import SAWERIA_BLOCK_OVERRIDE_ID, set_purchase_block


def get_eval_history(client):
    history = getattr(client, "eval_history", None)
    if history is None:
        history = {
            "last_code": None,
            "last_result": None,
            "last_stdout": None,
            "last_error": None,
            "last_time": None,
        }
        client.eval_history = history
    return history


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
    if not hasattr(client, "kwargs"):
        client.kwargs = {}
    scope = {
        "client": client,
        "c": client,
        "app": client,
        "message": message,
        "m": message,
        "msg": message,
        "r": message.reply_to_message,
        "rep": message.reply_to_message,
        "ctx": client,
        "db": client.db,
        "manager": getattr(client, "manager", None),
        "bots": client.manager.running_bots if hasattr(client, "manager") else None,
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

    get_eval_history(client).update(
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


async def eval_bot_handler(client: pyrogram.Client, message: Message):
    code = get_eval_payload(message)
    if not code:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} Berikan kode untuk "
                "dievaluasi atau balas ke sebuah pesan."
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
        rows = [
            ["Status", "Gagal"],
            ["Traceback", f"```\n{traceback.format_exc()}\n```"],
        ]
        error_text = (
            f"{client.ns.emoji.md('cross_mark')} **Kesalahan Handler**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
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


async def block_purchase_handler(client, message):
    args_text = client.ns.telegram.arg.getMessage(message, is_arg=True)
    arg = (args_text or "").strip().lower()

    bot_id = client.me.id
    bot_mention = client.ns.telegram.arg.getMention(client.me, md=True)
    current = bool(await client.db.getVars(bot_id, "purchase_block") or False)

    def _status_rows(value):
        state = "ON" if value else "OFF"
        return [
            ["Bot", f"{bot_mention}"],
            ["Status", f"`{state}`"],
            [
                "Efek ON",
                "Pencatatan dilewati; notifikasi dialihkan ke owner utama; "
                "link pembeli tetap dikirim; SAWERIA_USER_ID diganti sementara",
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
        rows = [
            ["Bot", bot_mention],
            ["Gunakan", "`/block on` atau `/block off`"],
            ["Status Saat Ini", f"`{'ON' if current else 'OFF'}`"],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )

    value = arg == "on"
    await set_purchase_block(client.db, bot_id, value)

    if value:
        title = f"{client.ns.emoji.md('lock')} **Block Mode Diaktifkan**"
        rows = [
            ["Bot", f"{bot_mention}"],
            ["Status", "`ON`"],
            ["Notifikasi", "Dialihkan ke owner utama"],
            ["Pencatatan", "Dilewati"],
            ["Link Pembeli", "Tetap dikirim"],
            ["Saweria", f"`{SAWERIA_BLOCK_OVERRIDE_ID}` (asli disimpan)"],
        ]
    else:
        title = f"{client.ns.emoji.md('white_check_mark')} **Block Mode Dinonaktifkan**"
        rows = [
            ["Bot", f"{bot_mention}"],
            ["Status", "`OFF`"],
            ["Notifikasi", "Normal"],
            ["Pencatatan", "Normal"],
            ["Link Pembeli", "Tetap dikirim"],
            ["Saweria", "Dikembalikan ke semula"],
        ]

    await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=f"{title}\n\n" f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
        )
    )


async def bot_owners_handler(client, message):
    rows = [["Status", "Mengumpulkan daftar owner bot"]]
    status_msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('repeat')} **Memproses**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
    )

    rows = []
    for _, x in client.manager.running_bots.items():
        try:
            uname = f"@{x.me.username}" if x.me.username else f"ID {x.me.id}"
        except Exception:
            uname = "Tidak diketahui"
        try:
            exp_date = parse_dt(await client.db.getVars(x.me.id, "bot_expiration_date"))
            if exp_date:
                days_left = (exp_date - datetime.now(timezone.utc)).days
                if days_left >= 0:
                    exp_text = f"`{exp_date.strftime('%d %b %Y')}` ({days_left} hari)"
                else:
                    exp_text = "Habis"
            else:
                exp_text = "Belum diatur"
        except Exception:
            exp_text = "-"
        try:
            sold_count = int(await client.db.getVars(x.me.id, "sales_count") or 0)
        except (TypeError, ValueError):
            sold_count = 0
        try:
            owner_id = await client.db.getVars(x.me.id, "owner_id")

            if not owner_id:
                rows.append(
                    [uname, "Owner belum diatur", "-", exp_text, f"`{sold_count}`"]
                )
                continue

            user = await x.get_users(owner_id)

            mention = (
                f"@{user.username}"
                if user.username
                else client.ns.telegram.arg.getMention(user, md=True)
            )

            token_hint = "-"
            if x.bot_token:
                token_prefix = x.bot_token.split(":", 1)[0]
                token_hint = f"`{token_prefix}:***`"

            rows.append([uname, mention, token_hint, exp_text, f"`{sold_count}`"])
        except Exception as e:
            rows.append([uname, "Error", f"`{e}`", exp_text, f"`{sold_count}`"])

    text = (
        f"{client.ns.emoji.md('busts_in_silhouette')} **Daftar Owner Bot**\n\n"
        f"{client.ns.table.md(['Bot', 'Owner', 'Token', 'Expired', 'Terjual'], rows)}"
    )
    await status_msg.edit(rich_message=pyrogram.types.InputRichMessage(markdown=text))


class AdminDevTools(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_message(
            filters.command("eval") & filters.user(self.client.owner_id)
        )(self.handle(eval_bot_handler))
        self.client.on_callback_query(
            filters.regex(r"^eval_") & filters.user(self.client.owner_id)
        )(self.handle(eval_callback_handler))
        self.client.on_message(
            filters.command("block") & filters.user(self.client.owner_id)
        )(self.handle(block_purchase_handler))
        self.client.on_message(
            filters.command("botowners") & filters.user(self.client.owner_id)
        )(self.handle(bot_owners_handler))
