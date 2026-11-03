import math
from time import time

import pyrogram

from helpers import parse_dt

from .. import *
from ..admin.cache import _user_cache

_page_cache: dict[tuple[int, int], tuple[float, dict]] = {}
_PAGE_CACHE_TTL = 60


async def _resolve_owner_text(client, owner_id: int) -> str:
    if not owner_id:
        return "Tidak diketahui"
    cached = _user_cache.get(owner_id)
    if cached is not None:
        return client.ns.telegram.arg.getMention(cached, md=True)
    try:
        owner_user = await client.get_users(owner_id)
        _user_cache.set(owner_id, owner_user)
        return client.ns.telegram.arg.getMention(owner_user, md=True)
    except Exception:
        return f"`{owner_id}`"


async def _build_page(client, page: int) -> dict:
    all_bots = await client.db.getBots(is_token=True)
    if not all_bots:
        return {"empty": True}

    items_per_page = 25
    total_pages = math.ceil(len(all_bots) / items_per_page)
    page = (page + total_pages) % total_pages
    paginated_bots = all_bots[page * items_per_page : (page + 1) * items_per_page]

    owner_ids: dict[int, int] = {}
    for bot_data in paginated_bots:
        try:
            bot_id = int(bot_data["name"])
        except (KeyError, TypeError, ValueError):
            continue
        owner_ids[bot_id] = await client.db.getVars(bot_id, "owner_id")

    unique_uncached = {
        oid for oid in owner_ids.values() if oid and _user_cache.get(oid) is None
    }
    if unique_uncached:
        fetched = await asyncio.gather(
            *[client.get_users(oid) for oid in unique_uncached],
            return_exceptions=True,
        )
        for oid, result in zip(unique_uncached, fetched):
            if not isinstance(result, Exception):
                _user_cache.set(oid, result)

    table_rows = []
    layout = []
    button_row = []
    bot_rows: list[dict] = []

    for index, bot_data in enumerate(paginated_bots, start=1):
        try:
            bot_id = int(bot_data["name"])
        except (KeyError, TypeError, ValueError):
            continue
        bot_username = "Offline"
        try:
            bot_instance = client.manager.running_bots.get(bot_id)
            if bot_instance and bot_instance.is_connected:
                bot_username = (
                    f"@{bot_instance.me.username}"
                    if bot_instance.me.username
                    else bot_instance.me.first_name
                )
        except Exception:
            bot_username = "Error"

        owner_id = owner_ids.get(bot_id)
        owner_text = await _resolve_owner_text(client, owner_id)

        exp_date_str = await client.db.getVars(bot_id, "bot_expiration_date")
        try:
            exp_date = parse_dt(exp_date_str)
            if exp_date:
                days_left = (exp_date - datetime.now(timezone.utc)).days
                active_text = f"`{days_left}` hari lagi"
            else:
                days_left = "N/A"
                active_text = "Belum diatur"
        except (TypeError, ValueError):
            days_left = "N/A"
            active_text = "Belum diatur"

        table_rows.append(
            [
                f"`{index}.`",
                bot_username,
                f"`{bot_id}`",
                owner_text,
                active_text,
            ]
        )

        bot_rows.append(
            {"bot_id": bot_id, "owner_id": owner_id, "days_left": days_left}
        )

        button_row.append(
            {
                "text": str(index),
                "callback_data": f"allbots_detail_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("robot"),
            }
        )
        if len(button_row) == 5:
            layout.append(button_row)
            button_row = []

    if button_row:
        layout.append(button_row)

    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages
        layout.append(
            [
                {
                    "text": "« Prev",
                    "callback_data": f"allbots_{prev_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                },
                {
                    "text": "Next »",
                    "callback_data": f"allbots_{next_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("right_pointing"),
                },
            ]
        )

    layout.append(
        [
            {
                "text": "Tutup Panel",
                "callback_data": "close_panel",
                "style": "red",
                "emoji": client.ns.emoji.id("cross_mark"),
            }
        ]
    )

    page_text = (
        f"{client.ns.emoji.md('open_folder')} **Daftar Semua Bot "
        f"({page + 1}/{total_pages})**\n\n"
        f"{client.ns.table.md(['#', 'Bot', 'Bot ID', 'Owner', 'Aktif'], table_rows)}"
    )

    return {
        "empty": False,
        "page": page,
        "total_pages": total_pages,
        "text": page_text,
        "layout": layout,
        "bot_rows": bot_rows,
    }


async def send_allbots_list(
    client, message_or_query, page: int, force_refresh: bool = False
):
    cache_key = (client.me.id, page)
    now = time()
    cached_entry = _page_cache.get(cache_key)

    if force_refresh or cached_entry is None or now - cached_entry[0] > _PAGE_CACHE_TTL:
        cached_entry = (now, await _build_page(client, page))
        _page_cache[cache_key] = cached_entry

    cached = cached_entry[1]

    if cached.get("empty"):
        table = client.ns.table
        empty_rows = [
            ["Jumlah Bot", "`0`"],
            ["Status", "Belum ada bot dari pengguna lain"],
        ]
        text = (
            f"{client.ns.emoji.md('robot')} **Daftar Bot Pengguna**\n\n"
            f"{table.md(['Info', 'Nilai'], empty_rows)}"
        )
        if isinstance(message_or_query, pyrogram.types.Message):
            return await message_or_query.reply_rich(
                pyrogram.types.InputRichMessage(markdown=text)
            )
        return await message_or_query.answer(
            "Belum ada bot yang dibuat oleh pengguna manapun.", show_alert=True
        )

    btn = client.ns.telegram.button.build_button_grid(cached["layout"])
    if isinstance(message_or_query, pyrogram.types.Message):
        await message_or_query.reply_rich(
            pyrogram.types.InputRichMessage(markdown=cached["text"]), reply_markup=btn
        )
    else:
        await message_or_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=cached["text"]),
            reply_markup=btn,
        )


def invalidate_page_cache(page: int | None = None):
    if page is None:
        _page_cache.clear()
        return

    for key in [key for key in _page_cache if key[1] == page]:
        _page_cache.pop(key, None)
