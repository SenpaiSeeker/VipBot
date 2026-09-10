import asyncio
import logging
import signal
import traceback

import pyrogram

try:
    import uvloop
except ImportError:
    loop = asyncio.new_event_loop()
else:
    loop = uvloop.new_event_loop()
finally:
    asyncio.set_event_loop(loop)

import VvipBot as handlers
from bot_manager import BotManager
from config import API_HASH, API_ID, BOT_TOKEN, OWNER_ID
from database import db, schedule
from helpers.logger import CustomLogHandler, LoggerHandler
from services import initialize_bot_services

log = LoggerHandler()

LOGGER_LEVELS = {
    "pyrogram": logging.WARNING,
    "pyrogram.client": logging.WARNING,
    "pyrogram.session.auth": logging.CRITICAL,
    "pyrogram.session.session": logging.CRITICAL,
}


def configure_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    root_logger.addHandler(CustomLogHandler())
    for logger_name, level in LOGGER_LEVELS.items():
        logging.getLogger(logger_name).setLevel(level)


def build_main_client():
    return pyrogram.Client(
        name="vvip_manager_main",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir="/tmp",
        in_memory=True,
    )


async def clean_sessions():
    try:
        process = await asyncio.create_subprocess_shell(
            "rm -rf *.session* /tmp/*.session*",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.communicate()
    except Exception:
        pass


async def shutdown(app, manager):
    log.print(f"{log.ORANGE}Memulai proses shutdown...")
    if getattr(app, "is_connected", False):
        try:
            await app.stop()
        except Exception:
            pass
    bot_ids = list(manager.running_bots.keys())
    if bot_ids:
        try:
            await asyncio.gather(
                *(manager.stop_bot(bot_id) for bot_id in bot_ids),
                return_exceptions=True,
            )
        except Exception:
            pass
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    log.print(f"{log.RED}Semua proses telah dimatikan.")


def register_signal_handlers(stop_event):
    def signal_handler():
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            signal.signal(sig, lambda *_: signal_handler())


async def main():
    await clean_sessions()

    manager = BotManager(db, OWNER_ID)
    handlers.ctx.manager = manager

    app = build_main_client()
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

        stop_event = asyncio.Event()
        register_signal_handlers(stop_event)
        await stop_event.wait()

    except Exception as e:
        log.print(
            f"{log.RED}[FATAL] Terjadi error saat memulai: {e}\n{traceback.format_exc()}"
        )
    finally:
        await shutdown(app, manager)


configure_logging()

if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        try:
            loop.close()
        except Exception:
            pass