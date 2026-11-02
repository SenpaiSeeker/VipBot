import asyncio
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

import aiocron
import aiofiles.os
import pyrogram
from pyrogram import filters

from helpers.modules import Modules

BACKUP_CRON = "0 */3 * * *"
TIMEZONE = ZoneInfo("Asia/Jakarta")


def _now_label():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z")


def _is_main_bot(client):
    main_bot_id = getattr(client.manager, "main_bot_id", None)
    return not main_bot_id or client.me.id == main_bot_id


async def _deny_main_only(client, message):
    rows = [["Status", "Perintah hanya tersedia di bot utama"]]
    return await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('cross_mark')} **Akses Ditolak**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
    )


async def perform_database_backup(client):
    db_path = getattr(client.db, "data_file", None)
    if not db_path or not os.path.exists(db_path):
        raise ValueError("Tidak ada database yang ditemukan untuk dicadangkan.")

    timestamp = datetime.now(TIMEZONE).strftime("%Y%m%d_%H%M%S")
    zip_name = f"backup_all_{timestamp}.zip"
    temp_dir = tempfile.mkdtemp(prefix="vipbot_backup_")
    zip_path = os.path.join(temp_dir, zip_name)

    try:

        def _create_zip():
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(db_path, arcname=os.path.basename(db_path))

        db_lock = getattr(client.db, "_lock", None)
        if db_lock is None:
            await asyncio.to_thread(_create_zip)
        else:
            async with db_lock:
                await asyncio.to_thread(_create_zip)

        caption = (
            f"{client.ns.emoji.md('shield')} **Backup Database**\n\n"
            f"**File:** `{zip_name}`\n"
            f"**Database:** `{os.path.basename(db_path)}`\n"
            f"**Waktu:** `{_now_label()}`"
        )
        await client.send_document(
            chat_id=client.owner_id,
            document=zip_path,
            caption=caption,
            parse_mode=pyrogram.enums.ParseMode.MARKDOWN,
        )
        return zip_name
    finally:
        await asyncio.to_thread(shutil.rmtree, temp_dir, True)


def _restore_database_archive(downloaded_zip_path, current_db_path):
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(downloaded_zip_path, "r") as zf:
            if not zf.namelist():
                raise ValueError("File .zip ini kosong atau rusak.")
            temp_root = os.path.realpath(temp_dir)
            for member in zf.infolist():
                target_path = os.path.realpath(os.path.join(temp_dir, member.filename))
                if target_path != temp_root and not target_path.startswith(
                    temp_root + os.sep
                ):
                    raise ValueError("Arsip backup berisi path yang tidak aman.")
            zf.extractall(path=temp_dir)

        restored_files = []
        for root, _, files in os.walk(temp_dir):
            for filename in files:
                if not filename.endswith(".json"):
                    continue
                source_path = os.path.join(root, filename)
                shutil.move(source_path, current_db_path)
                restored_files.append(os.path.basename(current_db_path))
                break
            if restored_files:
                break

        if not restored_files:
            raise ValueError(
                "Tidak ada file database (.json) yang valid ditemukan dalam arsip."
            )
        return restored_files


async def backup_database_handler(client, message):
    if not _is_main_bot(client):
        return await _deny_main_only(client, message)

    rows = [["Status", "Membuat arsip database"]]
    status_msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('hourglass')} **Memproses Backup**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
    )

    try:
        zip_name = await perform_database_backup(client)
        rows = [
            ["File", f"`{zip_name}`"],
            ["Status", "Backup dikirim ke owner"],
        ]
        await status_msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Backup "
                    "Berhasil!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )
    except Exception as e:
        rows = [
            ["Status", "Backup gagal"],
            ["Error", f"`{e}`"],
        ]
        await status_msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Backup Gagal!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )


async def restore_database_handler(client, message):
    if not _is_main_bot(client):
        return await _deny_main_only(client, message)

    if not message.reply_to_message or not message.reply_to_message.document:
        rows = [
            ["Status", "Cara penggunaan salah"],
            [
                "Cara",
                "Balas (reply) ke file backup `.zip` yang dikirim oleh bot "
                "dengan perintah ini",
            ],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('exclamation')} **Cara Penggunaan Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

    doc = message.reply_to_message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".zip"):
        rows = [
            ["Status", "Format file salah"],
            ["Syarat", "Hanya file backup dengan format `.zip` yang bisa dipulihkan"],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format File Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

    rows = [["Status", "Mendownload & mengekstrak file backup"]]
    status_msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('hourglass')} **Memproses Backup**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
    )
    downloaded_zip_path = None

    try:
        downloaded_zip_path = await client.download_media(message.reply_to_message)
        current_db_path = getattr(client.db, "data_file", None)
        if not current_db_path:
            raise ValueError("Tidak dapat menentukan path database aktif.")

        restored_files = await asyncio.to_thread(
            _restore_database_archive, downloaded_zip_path, current_db_path
        )
        await client.db.close_async()

        restored_names = ", ".join(restored_files)
        rows = [
            ["Database", f"`{restored_names}`"],
            ["Status", "Telah dipulihkan"],
            ["Penting", "Bot akan restart otomatis"],
        ]
        await status_msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('white_check_mark')} **Pemulihan "
                "Berhasil!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
        client.log.print(
            f"{client.log.GREEN}File-file berikut dipulihkan: "
            f"{', '.join(restored_files)} oleh admin."
        )

        if downloaded_zip_path and await aiofiles.os.path.exists(downloaded_zip_path):
            await aiofiles.os.remove(downloaded_zip_path)
            downloaded_zip_path = None

        await asyncio.sleep(2)
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        rows = [["Status", "Pemulihan gagal"], ["Error", f"`{e}`"]]
        await status_msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Pemulihan Gagal!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
        client.log.print(f"{client.log.RED}Restore failed: {e}")
    finally:
        if downloaded_zip_path and await aiofiles.os.path.exists(downloaded_zip_path):
            await aiofiles.os.remove(downloaded_zip_path)


class Backup(Modules):
    _cron_started = False

    def __init__(self, client):
        super().__init__(client)

        self.client.on_message(
            filters.command("backup") & filters.user(self.client.owner_id)
        )(self.handle(backup_database_handler))
        self.client.on_message(
            filters.command("restore") & filters.user(self.client.owner_id)
        )(self.handle(restore_database_handler))

        if Backup._cron_started:
            return

        Backup._cron_started = True
        aiocron.crontab(BACKUP_CRON, func=self._scheduled_backup, loop=client.loop)

    async def _scheduled_backup(self):
        try:
            await perform_database_backup(self.client)
        except Exception as e:
            self.client.log.print(f"{self.client.log.RED}Backup otomatis gagal: {e}")
