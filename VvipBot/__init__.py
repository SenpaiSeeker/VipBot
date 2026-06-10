import asyncio
import glob
import importlib
import math
import os
import random
import re
import string
import sys
import traceback
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from functools import partial, wraps
from io import BytesIO, StringIO
from time import time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from telethon import errors, events

_original_new_message_init = events.NewMessage.__init__


def _custom_new_message_init(self, *args, **kwargs):
    pattern = kwargs.get("pattern")

    if isinstance(pattern, str) and pattern.startswith("^/"):
        kwargs["pattern"] = re.compile(pattern, re.IGNORECASE)

    _original_new_message_init(self, *args, **kwargs)


events.NewMessage.__init__ = _custom_new_message_init

ALL_HANDLERS = []


class HandlerContext(SimpleNamespace):
    pass


ctx = HandlerContext()


def command(filter_lambda):
    def decorator(func):
        ALL_HANDLERS.append((func, filter_lambda))
        return func

    return decorator


def seller_only(func):
    @wraps(func)
    async def wrapper(client, event, *args, **kwargs):
        user_id = event.sender_id
        seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
        if user_id == ctx.owner_id or user_id in seller_list:
            return await func(client, event, *args, **kwargs)
        else:
            em = client.ns.emoji
            error_message = (
                f"{em.no_entry_age} <b>Akses Ditolak!</b>\n"
                "Anda tidak memiliki izin untuk menggunakan perintah ini."
            )
            if isinstance(event, events.CallbackQuery.Event):
                return await event.answer(error_message, alert=True)
            return await event.respond(error_message, parse_mode="html")

    return wrapper


async def is_bot_owner(client, user_id):
    owner_of_this_bot = await ctx.db.getVars(client.uid, "owner_id")
    return user_id == ctx.owner_id or (
        owner_of_this_bot and user_id == owner_of_this_bot
    )


async def _send_new_user_notification(client, user, owner_id):
    try:
        mention_user = client.ns.telegram.arg.getMention(user)
        me = await client.get_me()
        mention_bot = client.ns.telegram.arg.getMention(me)
        em = client.ns.emoji
        notification_text = (
            f"{em.bust_in_silhouette} <b>Pengguna Baru Telah Memulai Bot Anda!</b>"
            f"\n\n<b>Bot:</b> {mention_bot}"
            f"\n<b>Pengguna:</b> {mention_user}"
            f"\n<b>ID:</b> <code>{user.id}</code>"
        )
        await client.send_message(owner_id, notification_text, parse_mode="html")
    except Exception:
        pass


def check_new_user(func):
    @wraps(func)
    async def wrapper(client, event):
        user_list = await ctx.db.getListVars(client.uid, "user_ids") or []
        sender = await event.get_sender()
        if sender.id not in user_list:
            await ctx.db.setListVars(client.uid, "user_ids", sender.id)
            owner_of_this_bot = (
                await ctx.db.getVars(client.uid, "owner_id") or ctx.owner_id
            )
            asyncio.create_task(
                _send_new_user_notification(client, sender, owner_of_this_bot)
            )
            ctx.log.print(
                f"User baru {client.ns.telegram.arg.getMention(sender, logs=True)} memulai bot {client.me.username}"
            )
        return await func(client, event)

    return wrapper


def _load_all_handlers():
    current_dir = os.path.dirname(__file__)
    flat_paths = glob.glob(os.path.join(current_dir, "*.py"))
    flat_modules = sorted(
        os.path.basename(f)[:-3]
        for f in flat_paths
        if os.path.isfile(f) and not f.endswith("__init__.py")
    )
    for module_name in flat_modules:
        importlib.import_module(f".{module_name}", package=__name__)
    for entry in sorted(os.scandir(current_dir), key=lambda e: e.name):
        if entry.is_dir() and not entry.name.startswith("_"):
            pkg_init = os.path.join(entry.path, "__init__.py")
            if os.path.isfile(pkg_init):
                importlib.import_module(f".{entry.name}", package=__name__)


_load_all_handlers()


def register_all_handlers(client, db_instance, bot_manager, owner_id):
    ctx.db = db_instance
    ctx.manager = bot_manager
    ctx.owner_id = owner_id
    ctx.log = client.ns.utils.log()
    ctx.ACTIVE_MEMBERS_CACHE = {}
    for func, filter_lambda in ALL_HANDLERS:
        event_instance = filter_lambda(ctx)

        async def handler_wrapper(original_func, ev):
            try:
                await original_func(client, ev)
            except (
                errors.rpcerrorlist.MessageNotModifiedError,
                errors.rpcerrorlist.MessageDeleteForbiddenError,
            ):
                pass
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb_info = traceback.extract_tb(exc_traceback)[-1]
                filename = os.path.basename(tb_info.filename)
                func_name = tb_info.name
                line_no = tb_info.lineno
                log_message = (
                    f"{ctx.log.RED}[ERROR]: {ctx.log.CYAN}{filename}:{func_name}:{line_no} "
                    f"{ctx.log.WHITE}| {ctx.log.YELLOW}{type(e).__name__}: {ctx.log.RED}{e}"
                )
                ctx.log.print(log_message)

        client.add_event_handler(partial(handler_wrapper, func), event_instance)
