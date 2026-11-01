import asyncio
import glob
import logging
import os
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

from bot_manager import BotManager
from config import API_HASH, API_ID, BOT_TOKEN, OWNER_ID
from database import db, schedule
from helpers.logger import CustomLogHandler, LoggerHandler

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


async def shutdown(app: pyrogram.Client, manager: BotManager):
    log.print(f"{log.ORANGE}Memulai proses shutdown...")

    try:
        if getattr(app, "is_connected", False):
            await app.stop()
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

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    log.print(f"{log.RED}Semua proses telah dimatikan.")


def _remove_stale_sessions():
    allowed_prefixes = ("vvip_manager_main", "temp_bot_name_fetcher")

    for directory in {os.getcwd(), "/tmp"}:
        for path in glob.glob(os.path.join(directory, "*.session*")):
            stem = os.path.basename(path).split(".session", 1)[0]
            if not (stem.startswith(allowed_prefixes) or stem.isdigit()):
                continue
            if directory == "/tmp" and not stem.startswith(allowed_prefixes):
                continue
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass


async def clean_sessions():
    try:
        await asyncio.to_thread(_remove_stale_sessions)
    except Exception:
        pass


async def main():
    await clean_sessions()

    manager = BotManager(db, OWNER_ID)

    app = pyrogram.Client(
        name="vvip_manager_main",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir="/tmp",
        in_memory=True,
    )

    app.db = db
    app.manager = manager
    app.owner_id = OWNER_ID
    app.broadcast_stop = {}
    app.eval_history = {
        "last_code": None,
        "last_result": None,
        "last_stdout": None,
        "last_error": None,
        "last_time": None,
    }
    app.kwargs = {}

    try:
        app.ns.utils.grad.render_text("VVIP Meneger")
        log.print(f"{log.MAGENTA}Developed by NorSodikin")

        app.load_all(directory="VvipBot")
        await app.start()
        log.info(f"Bot utama '{app.me.first_name}' berhasil dimulai.")

        manager.main_bot_client = app
        manager.main_bot_id = app.me.id
        manager.running_bots[app.me.id] = app

        await manager.start_all_bots()

        if schedule.jobs:
            schedule.start()

        log.print(f"{log.CYAN}Bot sekarang berjalan. Tekan Ctrl+C untuk berhenti.")

        stop_event = asyncio.Event()

        def signal_handler():
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                signal.signal(sig, lambda *_: signal_handler())

        await stop_event.wait()

    except Exception as e:
        log.print(
            f"{log.RED}[FATAL] Terjadi error saat memulai: {e}\n"
            f"{traceback.format_exc()}"
        )
    finally:
        await shutdown(app, manager)


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
