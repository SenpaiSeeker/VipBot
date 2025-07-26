import asyncio
import glob
import importlib
import math
import os
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

import aiohttp
import nsdev
import pyrogram
from pyrogram import filters

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


def seller_only(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        user_id = message.from_user.id
        
        seller_list = ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
        
        if user_id == ctx.owner_id or user_id in seller_list:
            return await func(client, message, *args, **kwargs)
        else:
            error_message = message.lang.get("general.no_access_decorator")
            await message.reply_text(error_message, quote=True)
            return
            
    return wrapper


async def is_bot_owner(client, user_id):
    owner_of_this_bot = ctx.db.getVars(client.me.id, "owner_id")
    return user_id == ctx.owner_id or (owner_of_this_bot and user_id == owner_of_this_bot)


async def check_new_user(client, message):
    user_id = message.from_user.id
    user_list = ctx.db.getListVars(client.me.id, "user_ids") or []
    if user_id not in user_list:
        ctx.db.setListVars(client.me.id, "user_ids", user_id)
        owner_of_this_bot = ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id

        try:
            owner_lang = Language(ctx.db, owner_of_this_bot)
            notification_text = owner_lang.get(
                "bot_management.create.new_user_notification",
                mention=client.me.mention,
                user_mention=client.ns.arg.getMention(message.from_user),
                user_id=user_id,
            )
            await client.send_message(
                owner_of_this_bot,
                notification_text,
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
            ctx.log.warning(f"Handler type '{handler_type}' tidak dikenal. Melewati pendaftaran.")
            continue

        async def handler_wrapper(original_func, c, u):
            if hasattr(u, "from_user") and u.from_user:
                u.lang = Language(db_instance, u.from_user.id)
            else:
                u.lang = Language(db_instance, u.user_id)

            try:
                await original_func(c, u)
            except pyrogram.errors.MessageNotModified:
                ctx.log.print(f"{ctx.log.YELLOW}Caught MessageNotModified in handler '{original_func.__name__}'")
                if isinstance(u, pyrogram.types.CallbackQuery):
                    await u.answer("MessageNotModified")
            except pyrogram.errors.MessageDeleteForbidden:
                ctx.log.print(
                    f"{ctx.log.YELLOW}Gagal menghapus pesan di handler '{original_func.__name__}'. "
                    f"Pesan mungkin sudah lama atau bot tidak punya izin. Mengabaikan error."
                )
            except Exception as e:
                ctx.log.print(f"{ctx.log.YELLOW}{e}")

        wrapped_func = partial(handler_wrapper, func)

        if handler_type == "pre_checkout":
            client.add_handler(HandlerClass(wrapped_func))
        else:
            client.add_handler(HandlerClass(wrapped_func, filters=actual_filter))
