import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

import asyncio
import os
import traceback
import pyrogram
from nsdev import LoggerHandler
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from database import db
from bot_manager import BotManager
from services import initialize_bot_services
import VipBot as handlers
from VipBot.lang import Language

log = LoggerHandler()


async def main():
    os.system("rm -f *.session* /tmp/*.png")
    
    strings_dir = "strings"
    if not os.path.exists(strings_dir):
        os.makedirs(strings_dir)
        log.print(f"{log.YELLOW}Direktori '{strings_dir}' tidak ditemukan, telah dibuat.")

    manager = BotManager(db, OWNER_ID)

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
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.print(f"{log.ORANGE}Bot dihentikan oleh pengguna.")
