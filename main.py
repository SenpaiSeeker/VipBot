import asyncio
import logging
import os
import signal
import traceback

import tornado.ioloop
import tornado.locks
from telethon import TelegramClient
from telethon.sessions import MemorySession

import VvipBot as handlers
from bot_manager import BotManager
from config import API_HASH, API_ID, BOT_TOKEN, OWNER_ID
from database import db, schedule
from helpers.logger import CustomLogHandler, LoggerHandler
from services import initialize_bot_services

log = LoggerHandler()

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

root_logger.addHandler(CustomLogHandler())

log_levels = {
    "telethon": logging.WARNING,
    "telethon.network.mtprotosender": logging.CRITICAL,
    "telethon.network.connection.core": logging.CRITICAL,
}

for logger_name, level in log_levels.items():
    logging.getLogger(logger_name).setLevel(level)


async def shutdown(app, manager):
    log.print(f"{log.ORANGE}Memulai proses shutdown...")

    try:
        if app and app.is_connected():
            await app.disconnect()
    except Exception:
        pass

    try:
        stop_tasks = [
            manager.stop_bot(bot_id) for bot_id in list(manager.running_bots.keys())
        ]
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
    except Exception:
        pass

    try:
        if hasattr(db, "close_async"):
            await db.close_async()
    except Exception:
        pass

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    log.print(f"{log.RED}Semua proses telah dimatikan.")


async def main():
    os.system("rm -rf *.session* /tmp/*.session*")

    manager = BotManager(db, OWNER_ID)
    handlers.ctx.manager = manager

    app = TelegramClient(MemorySession(), API_ID, API_HASH)
    handlers.register_all_handlers(app, db, manager, OWNER_ID)

    try:
        app.ns.utils.grad.render_text("VVIP Meneger")
        log.print(f"{log.MAGENTA}Developed by NorSodikin")

        await app.start(bot_token=BOT_TOKEN)
        me = await app.get_me()

        app.uid = me.id
        app.me = me

        log.info(f"Bot utama '{me.first_name}' berhasil dimulai.")
        await initialize_bot_services(app, db)

        manager.main_bot_client = app
        manager.main_bot_id = me.id
        manager.running_bots[me.id] = app

        await manager.start_all_bots()

        if schedule.jobs:
            schedule.start()

        log.print(f"{log.CYAN}Bot sekarang berjalan. Tekan Ctrl+C untuk berhenti.")

        stop_event = tornado.locks.Event()

        def signal_handler(sig, frame):
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        await stop_event.wait()

    except Exception as e:
        log.print(
            f"{log.RED}[FATAL] Terjadi error saat memulai: {e}\n{traceback.format_exc()}"
        )

    finally:
        await shutdown(app, manager)


if __name__ == "__main__":
    try:
        tornado.ioloop.IOLoop.current().run_sync(main)
    except (KeyboardInterrupt, SystemExit):
        pass
