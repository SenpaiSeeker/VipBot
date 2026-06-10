import asyncio
import os
import shutil
import sys
import tempfile
import traceback
import zipfile
from io import BytesIO, StringIO
from time import time

import aiofiles.os
from telethon import events

from .. import command, ctx


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/eval(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def eval_bot_handler(client, event):
    async def aexec(code, client, event):
        replied_msg = await event.get_reply_message()
        local_vars = {}
        exec(
            "async def __aexec(client, event, r):\n    p = print\n    c = client\n    e = event\n    "
            + "\n    ".join(code.split("\n")),
            globals(),
            local_vars,
        )
        return await local_vars["__aexec"](client, event, replied_msg)

    em = client.ns.emoji
    msg = await event.respond(
        f"{em.repeat} <code>Memproses kode...</code>",
        parse_mode="html",
    )
    cmd = await client.ns.telegram.arg.getMessage(event, is_arg=True, raw=True)

    if not cmd:
        return await msg.edit(
            f"{em.cross_mark} <b>Perintah Gagal:</b> Harap berikan kode untuk dievaluasi.",
            parse_mode="html",
        )

    reply_to_msg = await event.get_reply_message()
    reply_to_id = reply_to_msg.id if reply_to_msg else None

    old_stdout, old_stderr = (sys.stdout, sys.stderr)
    redirected_output, redirected_error = (StringIO(), StringIO())
    sys.stdout, sys.stderr = (redirected_output, redirected_error)
    exc = None
    start_time = time()

    try:
        await aexec(cmd, client, event)
    except Exception:
        exc = traceback.format_exc()

    end_time = time()
    sys.stdout, sys.stderr = (old_stdout, old_stderr)
    stdout, stderr = (redirected_output.getvalue(), redirected_error.getvalue())
    evaluation = (
        exc or stderr or stdout or f"{em.white_check_mark} <b>Eksekusi Berhasil</b>"
    )

    final_output = (
        f"{em.laptop} <b>OUTPUT:</b>\n<pre>{evaluation.strip()}</pre>\n\n"
        f"{em.hourglass} <b>Waktu Eksekusi:</b> <code>{end_time - start_time:.4f}</code> detik"
    )

    if len(final_output) > 4096:
        with BytesIO(str.encode(evaluation)) as out_file:
            out_file.name = "eval_result.txt"
            await client.send_file(
                event.chat_id,
                out_file,
                caption=f"{em.open_book} Hasil evaluasi terlalu panjang. Dikirim sebagai file.",
                parse_mode="html",
            )
    else:
        await event.respond(final_output, reply_to=reply_to_id, parse_mode="html")

    await msg.delete()


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/restore$",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def restore_database_handler(client, event):
    reply = await event.get_reply_message()
    em = client.ns.emoji

    if not reply or not reply.document:
        return await event.respond(
            f"{em.anger} <b>Cara Penggunaan Salah:</b>\n"
            f"Balas (reply) ke file backup <code>.zip</code> yang dikirim oleh bot dengan perintah ini.",
            parse_mode="html",
        )

    doc = reply.document
    if not doc.mime_type == "application/zip" and not doc.attributes[
        0
    ].file_name.endswith(".zip"):
        return await event.respond(
            f"{em.cross_mark} <b>Format File Salah:</b>\n"
            f"Hanya file backup dengan format <code>.zip</code> yang bisa dipulihkan.",
            parse_mode="html",
        )

    status_msg = await event.respond(
        f"{em.hourglass} <code>Mendownload &amp; mengekstrak file backup...</code>",
        parse_mode="html",
    )
    downloaded_zip_path = None

    try:
        downloaded_zip_path = await reply.download_media()

        def _do_restore():
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(downloaded_zip_path, "r") as zf:
                    if not zf.namelist():
                        raise ValueError("File .zip ini kosong atau rusak.")
                    zf.extractall(path=temp_dir)

                restored_files = []
                current_db_path = getattr(ctx.db, "data_file", None)

                if not current_db_path:
                    raise ValueError("Tidak dapat menentukan path database aktif.")

                db_ext = ".json"
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
                        "Tidak ada file database JSON yang valid ditemukan."
                    )

                return restored_files

        restored_files = await asyncio.to_thread(_do_restore)
        await status_msg.edit(
            f"{em.white_check_mark} <b>Pemulihan Berhasil!</b>\n"
            f"Database <code>{', '.join(restored_files)}</code> telah dipulihkan.\n\n"
            f"{em.anger} <b>PENTING:</b> Mohon <b>restart</b> bot agar dapat menggunakan database baru.",
            parse_mode="html",
        )
        ctx.log.print(
            f"File database dipulihkan oleh admin: {', '.join(restored_files)}"
        )

    except Exception as e:
        await status_msg.edit(
            f"{em.cross_mark} <b>Pemulihan Gagal!</b>\n\n<b>Error:</b> <code>{e}</code>",
            parse_mode="html",
        )
        ctx.log.print(f"Restore failed: {e}")

    finally:
        if downloaded_zip_path and await aiofiles.os.path.exists(downloaded_zip_path):
            await aiofiles.os.remove(downloaded_zip_path)


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/tfdatabase(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def tfdatabase_command_handler(client, event):
    args = event.text.split()
    em = client.ns.emoji

    if len(args) != 3:
        return await event.respond(
            f"Format salah. Gunakan: <code>/tfdatabase &lt;source_id&gt;:&lt;source_db&gt; &lt;target_id&gt;:&lt;target_db&gt;</code>\n"
            f"Contoh: <code>/tfdatabase 123455:databaseV1 666999:databaseV2</code>",
            parse_mode="html",
        )

    source_part = args[1]
    target_part = args[2]

    try:
        source_id_str, source_db_name = source_part.split(":")
        target_id_str, target_db_name = target_part.split(":")
        source_id = int(source_id_str)
        target_id = int(target_id_str)
    except Exception:
        return await event.respond(
            f"Format salah. Pastikan menggunakan format <code>ID:NAMA_DB</code>. "
            f"Contoh: <code>/tfdatabase 123455:databaseV1 666999:databaseV2</code>",
            parse_mode="html",
        )

    msg = await event.respond(
        f"{em.repeat} Memproses transfer database...",
        parse_mode="html",
    )

    try:
        from helpers.database import DataBase

        source_db = (
            ctx.db
            if source_db_name == ctx.db.file_name
            else DataBase(
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
                file_name=target_db_name,
                keys_encrypt=ctx.db.keys_encrypt,
                method_encrypt=ctx.db.method_encrypt,
                auto_backup=False,
            )
        )

        source_data = await source_db._get_user_vars(source_id)

        if not source_data:
            return await msg.edit(
                f"{em.cross_mark} Data sumber tidak ditemukan pada database.",
                parse_mode="html",
            )

        await target_db._set_user_vars(target_id, source_data)

        await msg.edit(
            f"{em.white_check_mark} <b>Transfer Database Berhasil!</b>\n\n"
            f"<b>Sumber:</b> <code>{source_id}</code> (<code>{source_db_name}</code>)\n"
            f"<b>Tujuan:</b> <code>{target_id}</code> (<code>{target_db_name}</code>)\n\n"
            f"Semua data berhasil disalin secara lengkap.",
            parse_mode="html",
        )

    except Exception as e:
        await msg.edit(
            f"{em.cross_mark} Terjadi kesalahan saat mentransfer database:\n<pre>{e}</pre>",
            parse_mode="html",
        )


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/tfbot(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def tfbot_command_handler(client, event):
    args = event.text.split()
    em = client.ns.emoji

    if len(args) != 4:
        return await event.respond(
            f"Format salah. Gunakan: <code>/tfbot &lt;id_bot&gt; &lt;source_db&gt; &lt;target_db&gt;</code>\n"
            f"Contoh: <code>/tfbot 123456789 vvip_database vvip_databaseV2</code>",
            parse_mode="html",
        )

    try:
        bot_id = int(args[1])
    except ValueError:
        return await event.respond("ID Bot harus berupa angka.")

    source_db_name = args[2]
    target_db_name = args[3]

    msg = await event.respond(
        f"{em.repeat} Memproses migrasi bot...",
        parse_mode="html",
    )

    try:
        from helpers.database import DataBase

        source_db = (
            ctx.db
            if source_db_name == ctx.db.file_name
            else DataBase(
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
            return await msg.edit(
                f"{em.cross_mark} Bot dengan ID <code>{bot_id}</code> tidak ditemukan di <code>{source_db_name}</code>.",
                parse_mode="html",
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

        if bot_id in ctx.manager.running_bots:
            await ctx.manager.stop_bot(bot_id)

        await msg.edit(
            f"{em.white_check_mark} <b>Migrasi Bot Berhasil!</b>\n\n"
            f"<b>Bot ID:</b> <code>{bot_id}</code>\n"
            f"<b>Dari:</b> <code>{source_db_name}</code>\n"
            f"<b>Ke:</b> <code>{target_db_name}</code>\n\n"
            f"Bot beserta seluruh datanya telah dipindahkan dan dihapus dari database lama.\n\n"
            f"Jangan lupa restart bot tujuan agar bot ini segera menyala.",
            parse_mode="html",
        )

    except Exception as e:
        await msg.edit(
            f"{em.cross_mark} Terjadi kesalahan saat migrasi bot: <code>{e}</code>",
            parse_mode="html",
        )
