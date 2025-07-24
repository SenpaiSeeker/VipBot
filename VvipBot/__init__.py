import asyncio
import os
import math
import sys
import zipfile
import traceback
import uuid
import glob
import importlib
from functools import partial
from zoneinfo import ZoneInfo
from io import BytesIO, StringIO
from time import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import aiohttp
import pyrogram
from pyrogram import filters
import nsdev

from strings import Language

ALL_HANDLERS = []


class HandlerContext(SimpleNamespace):
    pass


ctx = HandlerContext()


def command(filter_lambda, handler_type="message"):
    def decorator(func):
        ALL_HANDLERS.append((func, filter_lambda, handler_type))
        return func

    return decorator


async def is_bot_owner(client, user_id):
    owner_of_this_bot = ctx.db.getVars(client.me.id, "owner_id")
    return user_id == ctx.owner_id or (
        owner_of_this_bot and user_id == owner_of_this_bot
    )


async def check_new_user(client, message):
    user_id = message.from_user.id
    user_list = ctx.db.getListVars(client.me.id, "user_ids") or []
    if user_id not in user_list:
        ctx.db.setListVars(client.me.id, "user_ids", user_id)
        owner_of_this_bot = ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id
        try:
            await client.send_message(
                owner_of_this_bot,
                f"**👤 Pengguna Baru Telah Memulai Bot Anda!**\n\n"
                f"**Bot:** {client.me.mention}\n"
                f"**Pengguna:** {client.ns.arg.getMention(message.from_user)}\n"
                f"**ID:** `{user_id}`",
            )
        except Exception as e:
            ctx.log.print(
                f"{ctx.log.YELLOW}Gagal notifikasi user baru ke owner {owner_of_this_bot} dari bot {client.me.id}: {e}"
            )
        ctx.log.print(
            f"{ctx.log.CYAN}User baru {client.ns.arg.getMention(message.from_user, logs=True)} memulai bot {client.me.first_name}"
        )


def _load_all_handlers():
    current_dir = os.path.dirname(__file__)
    module_paths = glob.glob(os.path.join(current_dir, "*.py"))

    all_modules = sorted(
        os.path.basename(f)[:-3]
        for f in module_paths
        if os.path.isfile(f) and f.endswith(".py") and not f.endswith("__init__.py")
    )

    for module_name in all_modules:
        importlib.import_module(f".{module_name}", package=__name__)


_load_all_handlers()


def register_all_handlers(client: pyrogram.Client, db_instance, bot_manager, owner_id):
    ctx.db = db_instance
    ctx.manager = bot_manager
    ctx.owner_id = owner_id
    ctx.log = nsdev.LoggerHandler()
    ctx.ACTIVE_MEMBERS_CACHE = {}
    ctx.L = Language

    HANDLER_MAP = {
        "message": pyrogram.handlers.MessageHandler,
        "callback": pyrogram.handlers.CallbackQueryHandler,
        "pre_checkout": pyrogram.handlers.PreCheckoutQueryHandler,
    }

    for func, filter_lambda, handler_type in ALL_HANDLERS:
        actual_filter = filter_lambda(ctx)

        HandlerClass = HANDLER_MAP.get(handler_type)
        if not HandlerClass:
            ctx.log.warning(
                f"Handler type '{handler_type}' tidak dikenal. Melewati pendaftaran."
            )
            continue

        async def handler_wrapper(original_func, c, u):
            if hasattr(u, "from_user") and u.from_user:
                u.lang = Language(db_instance, u.from_user.id)
            else:
                u.lang = Language(db_instance, u.user_id)

            try:
                await original_func(c, u)
            except pyrogram.errors.MessageNotModified:
                if isinstance(u, pyrogram.types.CallbackQuery):
                    await u.answer("MessageNotModified")
                ctx.log.print(f"{ctx.log.YELLOW}Caught and handled MessageNotModified.")
            except Exception as e:
                ctx.log.print(
                    f"{ctx.log.RED}An error occurred in handler: {e}\n{traceback.format_exc()}"
                )
                if isinstance(u, pyrogram.types.CallbackQuery):
                    try:
                        await u.answer(
                            u.lang.get("general.error", e=type(e).__name__),
                            show_alert=True,
                        )
                    except Exception:
                        pass

        wrapped_func = partial(handler_wrapper, func)

        if handler_type == "pre_checkout":
            client.add_handler(HandlerClass(wrapped_func))
        else:
            client.add_handler(HandlerClass(wrapped_func, filters=actual_filter))
