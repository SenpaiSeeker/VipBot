import math

from helpers import parse_dt

from .. import *
from ..admin.cache import _user_cache

_page_cache: dict[int, dict] = {}


async def _resolve_owner_text(client, owner_id: int) -> str:
    if not owner_id:
        return "Tidak diketahui"
    cached = _user_cache.get(owner_id)
    if cached is not None:
        return client.ns.telegram.arg.getMention(cached)
    try:
        owner_user = await client.get_users(owner_id)
        _user_cache.set(owner_id, owner_user)
        return client.ns.telegram.arg.getMention(owner_user)
    except Exception:
        return f"ID <code>{owner_id}</code>"


async def _build_page(client, page: int) -> dict:
    all_bots = await ctx.db.getBots(is_token=True)
    if not all_bots:
        return {"empty": True}

    items_per_page = 25
    total_pages = math.ceil(len(all_bots) / items_per_page)
    page = (page + total_pages) % total_pages
    paginated_bots = all_bots[page * items_per_page : (page + 1) * items_per_page]

    owner_ids: dict[int, int] = {}
    for bot_data in paginated_bots:
        bot_id = int(bot_data["name"])
        owner_ids[bot_id] = await ctx.db.getVars(bot_id, "owner_id")

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

    text_lines = [
        f"<b>{client.ns.emoji.open_folder} Daftar Semua Bot ({page + 1}/{total_pages})</b>\n"
    ]
    layout = []
    button_row = []
    bot_rows: list[dict] = []

    for index, bot_data in enumerate(paginated_bots, start=1):
        bot_id = int(bot_data["name"])
        bot_username = "Offline"
        try:
            bot_instance = ctx.manager.running_bots.get(bot_id)
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

        exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
        try:
            exp_date = parse_dt(exp_date_str)
            days_left = (
                (exp_date - datetime.now(timezone.utc)).days if exp_date else "N/A"
            )
        except (TypeError, ValueError):
            days_left = "N/A"

        text_lines.append(
            f"<b>{index:2}:</b> {bot_username} (<code>{bot_id}</code>)\n"
            f" ├ {client.ns.emoji.bust_in_silhouette} Owner: {owner_text}\n"
            f" ├ {client.ns.emoji.hourglass} Aktif: <code>{days_left}</code> hari lagi"
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

    return {
        "empty": False,
        "page": page,
        "total_pages": total_pages,
        "text": "\n".join(text_lines),
        "layout": layout,
        "bot_rows": bot_rows,
    }


async def send_allbots_list(
    client, message_or_query, page: int, force_refresh: bool = False
):
    if force_refresh:
        _page_cache.pop(page, None)

    if page not in _page_cache:
        _page_cache[page] = await _build_page(client, page)

    cached = _page_cache[page]

    if cached.get("empty"):
        text = "Belum ada bot yang dibuat oleh pengguna manapun."
        if isinstance(message_or_query, pyrogram.types.Message):
            return await message_or_query.reply_text(text)
        return await message_or_query.answer(text, show_alert=True)

    btn = client.ns.telegram.button.build_button_grid(cached["layout"])
    if isinstance(message_or_query, pyrogram.types.Message):
        await message_or_query.reply_text(
            cached["text"], reply_markup=btn, parse_mode=ParseMode.HTML
        )
    else:
        await message_or_query.edit_message_text(
            cached["text"], reply_markup=btn, parse_mode=ParseMode.HTML
        )


def invalidate_page_cache(page: int | None = None):
    if page is None:
        _page_cache.clear()
    else:
        _page_cache.pop(page, None)
