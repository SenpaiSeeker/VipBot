import asyncio
import logging
import os
import signal
import traceback

import pyrogram
from tornado.ioloop import IOLoop

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
    "pyrogram": logging.WARNING,
    "pyrogram.client": logging.WARNING,
    "pyrogram.session.auth": logging.CRITICAL,
    "pyrogram.session.session": logging.CRITICAL,
}

for logger_name, level in log_levels.items():
    logging.getLogger(logger_name).setLevel(level)


async def main():
    os.system("rm -ff *.session*")

    manager = BotManager(db, OWNER_ID)

    app = pyrogram.Client(
        name="vvip_manager_main",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    handlers.register_all_handlers(app, db, manager, OWNER_ID)

    try:
        app.ns.utils.grad.render_text("VVIP Meneger")
        log.print(f"{log.MAGENTA}Developed by NorSodikin")
        await app.start()
        log.info(f"Bot utama '{app.me.first_name}' berhasil dimulai.")
        await initialize_bot_services(app, db)

        manager.main_bot_client = app
        manager.main_bot_id = app.me.id
        manager.running_bots[app.me.id] = app

        await manager.start_all_bots()

        if schedule.jobs:
            schedule.start()

        log.print(f"{log.CYAN}Bot sekarang berjalan. Tekan Ctrl+C untuk berhenti.")

    except Exception as e:
        log.print(f"{log.RED}[FATAL] Terjadi error saat memulai: {e}\n{traceback.format_exc()}")
        IOLoop.current().stop()


def stop_all_clients():
    log.print(f"{log.YELLOW}Memulai proses penghentian bot...")

    loop = IOLoop.current()

    async def gather_stops():
        manager = handlers.ctx.manager
        stop_tasks = [manager.stop_bot(bot_id) for bot_id in list(manager.running_bots.keys())]

        if stop_tasks:
            await asyncio.gather(*stop_tasks)

        await db.close_async()

        loop.stop()

    loop.add_callback(lambda: asyncio.ensure_future(gather_stops()))
    log.print(f"{log.ORANGE}Proses penghentian telah dimulai. Program akan segera keluar.")


if __name__ == "__main__":

    def handle_exit_signal(sig, frame):
        log.print(f"{log.ORANGE}Menerima sinyal berhenti ({sig})...")
        IOLoop.current().add_callback_from_signal(stop_all_clients)

    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)

    try:
        IOLoop.current().add_callback(main)
        IOLoop.current().start()
    except Exception as e:
        log.print(f"{log.RED}Terjadi error tak terduga di IOLoop: {e}")
    finally:
        log.print(f"{log.WHITE}Loop IOLoop telah berhenti. Program selesai.")
