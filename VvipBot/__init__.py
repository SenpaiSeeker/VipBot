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
    async def wrapper(client, update, *args, **kwargs):
        user_id = update.from_user.id

        seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []

        if user_id == ctx.owner_id or user_id in seller_list:
            return await func(client, update, *args, **kwargs)
        else:
            lang = update.lang
            error_message = lang.get("general.no_access_decorator")

            if isinstance(update, pyrogram.types.CallbackQuery):
                return await update.answer(error_message, show_alert=True)
            elif isinstance(update, pyrogram.types.Message):
                return await update.reply_text(error_message, quote=True)

    return wrapper


async def is_bot_owner(client, user_id):
    owner_of_this_bot = await ctx.db.getVars(client.me.id, "owner_id")
    return user_id == ctx.owner_id or (owner_of_this_bot and user_id == owner_of_this_bot)


def check_new_user(func):
    @wraps(func)
    async def wrapper(client, update):
        user_list = await ctx.db.getListVars(client.me.id, "user_ids") or []
        if update.from_user.id not in user_list:
            await ctx.db.setListVars(client.me.id, "user_ids", update.from_user.id)
            owner_of_this_bot = await ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id
            try:
                owner_lang = await Language.create(ctx.db, owner_of_this_bot)
                mention_user = client.ns.telegram.arg.getMention(update.from_user)

                notification_text = owner_lang.get(
                    "bot_management.create.new_user_notification",
                    mention=client.me.mention,
                    user_mention=mention_user,
                    user_id=update.from_user.id,
                )
                await client.send_message(owner_of_this_bot, notification_text)
            except Exception:
                pass

        return await func(client, update)

    return wrapper


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
    ctx.log = client.ns.utils.log()
    ctx.ACTIVE_MEMBERS_CACHE = {}
    ctx.L = Language

    HANDLER_MAP = {
        "message": pyrogram.handlers.MessageHandler,
        "callback": pyrogram.handlers.CallbackQueryHandler,
        "pre_checkout": pyrogram.handlers.PreCheckoutQueryHandler,
        "chat_join_request": pyrogram.handlers.ChatJoinRequestHandler,
    }

    for func, filter_lambda, handler_type in ALL_HANDLERS:
        actual_filter = filter_lambda(ctx)

        HandlerClass = HANDLER_MAP.get(handler_type)
        if not HandlerClass:
            ctx.log.print(f"{ctx.log.YELLOW}Handler type '{handler_type}' tidak dikenal. Melewati pendaftaran.")
            continue

        async def handler_wrapper(original_func, c, u):
            user_id = 0
            if hasattr(u, "from_user") and u.from_user:
                user_id = u.from_user.id
            elif hasattr(u, "sender_chat") and u.sender_chat:
                user_id = u.sender_chat.id

            u.lang = await Language.create(db_instance, user_id)

            try:
                await original_func(c, u)
            except (pyrogram.errors.MessageNotModified, pyrogram.errors.MessageDeleteForbidden):
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
