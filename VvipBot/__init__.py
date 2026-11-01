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
from weakref import WeakValueDictionary
from zoneinfo import ZoneInfo

import pyrogram
from pyrogram import filters
from pyrogram.enums import ParseMode

from helpers import listen
from helpers.saweria_message_generator import (
    generate_safe_saweria_message,
)


def seller_only(func):

    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        user_id = update.from_user.id
        seller_list = (
            await client.db.getListVars(client.owner_id, "seller_id_list") or []
        )
        if user_id == client.owner_id or user_id in seller_list:
            return await func(client, update, *args, **kwargs)
        else:
            rows = [
                ["Status", "Ditolak"],
                [
                    "Keterangan",
                    "Anda tidak memiliki izin untuk menggunakan perintah ini",
                ],
            ]
            error_message = (
                f"{client.ns.emoji.md('cross_mark')} **Akses Ditolak**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
            if isinstance(update, pyrogram.types.CallbackQuery):
                return await update.answer(error_message, show_alert=True)
            elif isinstance(update, pyrogram.types.Message):
                return await update.reply_rich(
                    pyrogram.types.InputRichMessage(markdown=error_message)
                )

    return wrapper


async def is_bot_owner(client, user_id):
    owner_of_this_bot = await client.db.getVars(client.me.id, "owner_id")
    return user_id == client.owner_id or (
        owner_of_this_bot and user_id == owner_of_this_bot
    )


async def get_notification_target(client):
    raw = await client.db.getVars(client.me.id, "notif_chat_id")

    if raw is not None:
        value = str(raw).strip()
        if value and not value.startswith("/"):
            return raw

    return await client.db.getVars(client.me.id, "owner_id") or client.owner_id


def get_member_lock(client):
    locks = getattr(client, "_member_locks", None)
    if locks is None:
        locks = WeakValueDictionary()
        setattr(client, "_member_locks", locks)
    bot_id = client.me.id
    lock = locks.get(bot_id)
    if lock is None:
        lock = asyncio.Lock()
        locks[bot_id] = lock
    return lock


def get_bot_cache(client, name):
    store = getattr(client, name, None)
    if not isinstance(store, dict):
        store = {}
        setattr(client, name, store)
    key = str(client.me.id)
    bucket = store.get(key)
    if not isinstance(bucket, dict):
        bucket = {}
        store[key] = bucket
    return bucket


async def get_sales_count(client):
    count = await client.db.getVars(client.me.id, "sales_count")
    if count is None:
        history = await client.db.getListVars(client.me.id, "vip_revenue_history") or []
        count = len(history)
        await client.db.setVars(client.me.id, "sales_count", count)

    try:
        return int(count)
    except (TypeError, ValueError):
        return 0


LIST_VVIP_ICON_DEFAULT = {
    "normal": "open_folder",
    "promo": "party_popper",
    "buy_all": "shopping_cart",
}

LIST_VVIP_ICON_BUY_ALL_KEY = "!_buy_all_"

SAWERIA_BLOCK_OVERRIDE_ID = "9a163754-ab11-46e9-9253-60fa0ff70dea"
SALES_ROUTE_INTERVAL = 10
MAX_BOT_CAPACITY = 30


def _sanitize_emoji_id(value):
    if value is None or isinstance(value, bool):
        return None

    try:
        emoji_id = int(str(value).strip())
    except (TypeError, ValueError):
        return None

    return emoji_id if emoji_id > 0 else None


async def get_list_vvip_icons(client):
    saved = await client.db.getVars(client.me.id, "list_vvip_icon")

    if not isinstance(saved, dict):
        return {}

    icons = {}
    for name, raw in saved.items():
        if isinstance(raw, dict):
            emoji_id = _sanitize_emoji_id(raw.get("id"))
            if emoji_id:
                icons[str(name)] = {"id": emoji_id, "char": raw.get("char")}
        else:
            emoji_id = _sanitize_emoji_id(raw)
            if emoji_id:
                icons[str(name)] = {"id": emoji_id, "char": None}

    return icons


def render_list_vvip_icon_html(client, icons, name, kind="normal"):
    entry = icons.get(name)
    if entry and entry.get("char"):
        return f'<tg-emoji emoji-id="{entry["id"]}">{entry["char"]}</tg-emoji>'

    default_name = LIST_VVIP_ICON_DEFAULT.get(kind, LIST_VVIP_ICON_DEFAULT["normal"])
    return getattr(client.ns.emoji, default_name)


async def check_new_user(client, update):
    if not update or not getattr(update, "from_user", None):
        return

    already_seen = await client.db.isMemberOf(
        client.me.id, "user_ids", update.from_user.id
    )
    if not already_seen:
        await client.db.setListVars(
            client.me.id,
            "user_ids",
            update.from_user.id,
            check_duplicate=False,
        )
        owner_of_this_bot = (
            await client.db.getVars(client.me.id, "owner_id") or client.owner_id
        )

        try:
            mention_user = client.ns.telegram.arg.getMention(update.from_user, md=True)
            rows = [
                ["Bot", client.ns.telegram.arg.getMention(client.me, md=True)],
                ["Pengguna", mention_user],
                ["ID", f"`{update.from_user.id}`"],
            ]
            notification_text = (
                f"{client.ns.emoji.md('bust_in_silhouette')} **Pengguna Baru "
                "Telah Memulai Bot Anda**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
            await client.send_rich_message(
                owner_of_this_bot,
                pyrogram.types.InputRichMessage(markdown=notification_text),
            )
        except Exception:
            pass

        client.log.print(
            f"{client.log.CYAN}User baru "
            f"{client.ns.telegram.arg.getMention(update.from_user, logs=True)} "
            f"memulai bot {client.me.first_name}"
        )
