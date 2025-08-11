import asyncio
import os
import sys
import traceback
from pathlib import Path

import pyrogram
import nsdev
from nsdev import listen

_ = listen

import VvipBot as handlers
from bot_manager import BotManager
from config import API_HASH, API_ID, BOT_TOKEN, OWNER_ID
from database import db
from services import initialize_bot_services

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


async def main():
    log = nsdev.LoggerHandler()
    os.system("rm -f *.session* /tmp/*.png")

    strings_dir = "strings"
    if not os.path.exists(strings_dir):
        os.makedirs(strings_dir)
        log.print(f"{log.YELLOW}Direktori '{strings_dir}' tidak ditemukan, telah dibuat.")

    manager = BotManager(db, OWNER_ID, log)

    app = pyrogram.Client(
        name="vvip_manager_main",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    handlers.register_all_handlers(app, db, manager, OWNER_ID)

    try:
        await app.start()
        log.print(f"{log.GREEN}Bot utama '{app.me.first_name}' berhasil dimulai.")
        initialize_bot_services(app, db)

        manager.main_bot_client = app
        manager.main_bot_id = app.me.id

        manager.running_bots[app.me.id] = app
        await manager.start_all_bots()
        asyncio.create_task(manager.expiration_checker())
        await pyrogram.idle()
    except Exception as e:
        log.print(f"{log.RED}[FATAL] Terjadi error: {e}\n{traceback.format_exc()}")
    finally:
        log.print(f"{log.YELLOW}Menghentikan semua bot...")
        for bot_id in list(manager.running_bots.keys()):
            await manager.stop_bot(bot_id)
        if app.is_connected:
            await app.stop()


if __name__ == "__main__":
    log = nsdev.LoggerHandler()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.print(f"{log.ORANGE}Bot dihentikan oleh pengguna.")
