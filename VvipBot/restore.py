import asyncio
import os
import shutil
import tempfile
import zipfile

import aiofiles.os

from . import command, ctx, filters


@command(lambda ctx: filters.command("restore") & filters.user(ctx.owner_id))
async def restore_database_handler(client, message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text(
            f"{client.ns.emoji.exclamation} **Cara Penggunaan Salah:**\nBalas (reply) ke file backup `.zip` yang dikirim oleh bot dengan perintah ini."
        )
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".zip"):
        return await message.reply_text(
            f"{client.ns.emoji.cross_mark} **Format File Salah:**\nHanya file backup dengan format `.zip` yang bisa dipulihkan."
        )
    status_msg = await message.reply_text(
        f"{client.ns.emoji.hourglass} `Mendownload & mengekstrak file backup...`"
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
            f"{client.ns.emoji.white_check_mark} **Pemulihan Berhasil!**\n"
            f"Database `{restored_names}` telah dipulihkan.\n\n"
            f"{client.ns.emoji.exclamation} **PENTING:** Mohon **restart** bot agar dapat menggunakan database baru."
        )
        ctx.log.print(
            f"{ctx.log.GREEN}File-file berikut dipulihkan: {', '.join(restored_files)} oleh admin."
        )
    except Exception as e:
        await status_msg.edit_text(
            f"{client.ns.emoji.cross_mark} **Pemulihan Gagal!**\n\n**Error:** `{e}`"
        )
        ctx.log.print(f"{ctx.log.RED}Restore failed: {e}")
    finally:
        if downloaded_zip_path and await aiofiles.os.path.exists(downloaded_zip_path):
            await aiofiles.os.remove(downloaded_zip_path)