import asyncio
import glob
import importlib
import math
import os
import random
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

import pyrogram
from pyrogram import filters
from pyrogram.enums import ParseMode

from helpers import listen
from helpers.saweria_message_generator import (
    generate_safe_saweria_message,
)

ALL_HANDLERS = []


class HandlerContext(SimpleNamespace):
    pass


ctx = HandlerContext()


def command(filter_lambda, handler_type="message"):

    def decorator(func):
        ALL_HANDLERS.append((func, filter_lambda, handler_type))
        return func

    return decorator


def seller_only(func):

    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        user_id = update.from_user.id
        seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
        if user_id == ctx.owner_id or user_id in seller_list:
            return await func(client, update, *args, **kwargs)
        else:
            error_message = f"{client.ns.emoji.cross_mark} **Akses Ditolak!**\nAnda tidak memiliki izin untuk menggunakan perintah ini."
            if isinstance(update, pyrogram.types.CallbackQuery):
                return await update.answer(error_message, show_alert=True)
            elif isinstance(update, pyrogram.types.Message):
                return await update.reply_text(error_message, quote=True)

    return wrapper


async def is_bot_owner(client, user_id):
    owner_of_this_bot = await ctx.db.getVars(client.me.id, "owner_id")
    return user_id == ctx.owner_id or (
        owner_of_this_bot and user_id == owner_of_this_bot
    )


async def get_notification_target(client):
    raw = await ctx.db.getVars(client.me.id, "notif_chat_id")

    if raw is not None:
        value = str(raw).strip()
        if value and not value.startswith("/"):
            return raw

    return await ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id


LIST_VVIP_ICON_DEFAULT = {
    "normal": "open_folder",
    "promo": "party_popper",
}


def _sanitize_emoji_id(value):
    if value is None or isinstance(value, bool):
        return None

    try:
        emoji_id = int(str(value).strip())
    except (TypeError, ValueError):
        return None

    return emoji_id if emoji_id > 0 else None


async def get_list_vvip_icon(client, kind):
    if kind not in LIST_VVIP_ICON_DEFAULT:
        return client.ns.emoji.id(LIST_VVIP_ICON_DEFAULT["normal"])

    saved = await ctx.db.getVars(client.me.id, "list_vvip_icon")
    if isinstance(saved, dict):
        emoji_id = _sanitize_emoji_id(saved.get(kind))
        if emoji_id:
            return emoji_id

    return client.ns.emoji.id(LIST_VVIP_ICON_DEFAULT[kind])


async def check_new_user(client, update):
    if not update or not getattr(update, "from_user", None):
        return

    user_list = await ctx.db.getListVars(client.me.id, "user_ids") or []
    if update.from_user.id not in user_list:
        await ctx.db.setListVars(
            client.me.id,
            "user_ids",
            update.from_user.id,
        )
        owner_of_this_bot = (
            await ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id
        )

        try:
            mention_user = client.ns.telegram.arg.getMention(update.from_user)
            notification_text = (
                f"**{client.ns.emoji.bust_in_silhouette} Pengguna Baru Telah Memulai Bot Anda!**\n\n"
                f"**Bot:** {client.me.mention}\n"
                f"**Pengguna:** {mention_user}\n"
                f"**ID:** `{update.from_user.id}`"
            )
            await client.send_message(owner_of_this_bot, notification_text)
        except Exception:
            pass

        ctx.log.print(
            f"{ctx.log.CYAN}User baru {client.ns.telegram.arg.getMention(update.from_user, logs=True)} memulai bot {client.me.first_name}"
        )


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


def register_all_handlers(
    client: pyrogram.Client,
    db_instance,
    bot_manager,
    owner_id,
):
    ctx.db = db_instance
    ctx.manager = bot_manager
    ctx.owner_id = owner_id
    ctx.log = client.ns.utils.log()
    ctx.ACTIVE_MEMBERS_CACHE = {}
    HANDLER_MAP = {
        "message": pyrogram.handlers.MessageHandler,
        "callback": pyrogram.handlers.CallbackQueryHandler,
        "pre_checkout": pyrogram.handlers.PreCheckoutQueryHandler,
    }
    for func, filter_lambda, handler_type in ALL_HANDLERS:
        actual_filter = filter_lambda(ctx)
        HandlerClass = HANDLER_MAP.get(handler_type)
        if not HandlerClass:
            ctx.log.print(
                f"{ctx.log.YELLOW}Handler type '{handler_type}' tidak dikenal. Melewati pendaftaran."
            )
            continue

        async def handler_wrapper(original_func, c, u):
            if hasattr(u, "from_user") and u.from_user:
                u.from_user.id
            elif hasattr(u, "sender_chat") and u.sender_chat:
                u.sender_chat.id
            try:
                await original_func(c, u)
            except (
                pyrogram.errors.MessageNotModified,
                pyrogram.errors.MessageDeleteForbidden,
            ):
                pass
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb_info = traceback.extract_tb(exc_traceback)[-1]
                filename = os.path.basename(tb_info.filename)
                func_name = tb_info.name
                line_no = tb_info.lineno
                log_message = f"{ctx.log.RED}[ERROR]: {ctx.log.CYAN}{filename}:{func_name}:{line_no} {ctx.log.WHITE}| {ctx.log.YELLOW}{type(e).__name__}: {ctx.log.RED}{e}"
                ctx.log.print(log_message)

        wrapped_func = partial(handler_wrapper, func)
        if handler_type == "pre_checkout":
            client.add_handler(HandlerClass(wrapped_func))
        else:
            client.add_handler(HandlerClass(wrapped_func, filters=actual_filter))
