import math

from . import *
from .cache import _user_cache

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
        days_left = (
            (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days
            if exp_date_str
            else "N/A"
        )

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


@command(lambda ctx: filters.command("allbots") & filters.user(ctx.owner_id))
async def allbots_command_handler(client, message):
    invalidate_page_cache()
    msg_process = await message.reply(
        f"{client.ns.emoji.repeat} Sedang memproses mengumpulkan bot"
    )
    await send_allbots_list(client, message, 0, force_refresh=True)
    await msg_process.delete()


@command(lambda ctx: filters.regex("^allbots_(\\-?\\d+)"), handler_type="callback")
async def allbots_pagination_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    page = int(callback_query.data.split("_")[1])
    await send_allbots_list(client, callback_query, page)


@command(
    lambda ctx: filters.regex("^allbots_detail_(\\d+)_(\\d+)"), handler_type="callback"
)
async def allbots_detail_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))

    bot_username = "Offline"
    bot_name = f"Bot ID {bot_id}"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username or "Tidak Ada"
    except Exception:
        pass

    owner_id = await ctx.db.getVars(bot_id, "owner_id")
    owner_text = await _resolve_owner_text(client, owner_id)

    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    days_left = (
        (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days
        if exp_date_str
        else "N/A"
    )

    text = (
        f"**{client.ns.emoji.toolbox} Kelola Bot Spesifik**\n\n"
        f"• **Nama Bot:** {bot_name}\n"
        f"• **ID Bot:** `{bot_id}`\n"
        f"• **Username Bot:** @{bot_username}\n"
        f"• **Pemilik:** {owner_text}\n"
        f"• **Sisa Aktif:** `{days_left}` hari"
    )

    layout = [
        [
            {
                "text": "🗑️ Hapus Bot",
                "callback_data": f"allbots_confirm_delete_{bot_id}_{page}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ],
        [
            {
                "text": "🗓️ Kelola Masa Aktif",
                "callback_data": f"allbots_duration_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            }
        ],
        [
            {
                "text": "🔙 Kembali ke Daftar",
                "callback_data": f"allbots_back_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    await callback_query.edit_message_text(
        text, reply_markup=client.ns.telegram.button.build_button_grid(layout)
    )


@command(lambda ctx: filters.regex("^allbots_back_(\\d+)"), handler_type="callback")
async def allbots_back_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    page = int(callback_query.matches[0].group(1))
    await send_allbots_list(client, callback_query, page)


@command(
    lambda ctx: filters.regex("^allbots_confirm_delete_(\\d+)_(\\d+)"),
    handler_type="callback",
)
async def allbots_confirm_delete_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))
    layout = [
        [
            {
                "text": "✅ Ya, Hapus",
                "callback_data": f"allbots_do_delete_{bot_id}_{page}",
                "style": "red",
                "emoji": client.ns.emoji.id("white_check_mark"),
            },
            {
                "text": "❌ Tidak",
                "callback_data": f"allbots_back_{page}",
                "style": "green",
                "emoji": client.ns.emoji.id("cross_mark"),
            },
        ]
    ]

    text = (
        f"**{client.ns.emoji.warning} Konfirmasi Penghapusan**\n\n"
        f"Anda yakin ingin menghapus bot dengan ID `{bot_id}` secara permanen?"
    )
    await callback_query.edit_message_text(
        text,
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


@command(
    lambda ctx: filters.regex("^allbots_do_delete_(\\d+)_(\\d+)"),
    handler_type="callback",
)
async def allbots_do_delete_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))

    await callback_query.edit_message_text(
        f"{client.ns.emoji.hourglass} Menghapus bot..."
    )
    try:
        owner_id_to_invalidate = await ctx.db.getVars(bot_id, "owner_id")
        await ctx.manager.stop_bot(bot_id)
        await asyncio.sleep(1)
        await ctx.db.removeBot(bot_id)
        await ctx.db.removeAllVars(bot_id)
        if owner_id_to_invalidate:
            _user_cache.invalidate(owner_id_to_invalidate)
        invalidate_page_cache(page)
        await send_allbots_list(client, callback_query, page, force_refresh=True)
        await callback_query.answer("✅ Bot berhasil dihapus.", show_alert=True)
    except Exception as e:
        await callback_query.answer("❌Gagal menghapus bot: {e}".format(e=e), show_alert=True)
        await send_allbots_list(client, callback_query, 0, force_refresh=True)


@command(
    lambda ctx: filters.regex("^allbots_duration_(\\d+)_(\\d+)"),
    handler_type="callback",
)
async def allbots_duration_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))
    layout = [
        [
            {
                "text": "➕ Tambah Masa Aktif",
                "callback_data": f"allbots_extend_{bot_id}_{page}",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            }
        ],
        [
            {
                "text": "➖ Kurangi Masa Aktif",
                "callback_data": f"allbots_reduce_{bot_id}_{page}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": f"allbots_back_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    await callback_query.edit_message_text(
        f"**{client.ns.emoji.calendar} Kelola Masa Aktif untuk Bot `{bot_id}`**",
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


@command(
    lambda ctx: filters.regex("^allbots_extend_(\\d+)_(\\d+)"), handler_type="callback"
)
async def allbots_extend_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))
    buttons = [
        {
            "text": f"+{days} hari",
            "callback_data": f"allbots_do_extend_{bot_id}_{days}_{page}",
            "style": "green",
            "emoji": client.ns.emoji.id("plus"),
        }
        for days in [7, 30, 90]
    ]
    layout = [
        buttons,
        [
            {
                "text": "• Kembali •",
                "callback_data": f"allbots_duration_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    await callback_query.edit_message_text(
        f"Pilih durasi untuk ditambahkan ke Bot `{bot_id}`:",
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


@command(
    lambda ctx: filters.regex("^allbots_do_extend_(\\d+)_(\\d+)_(\\d+)"),
    handler_type="callback",
)
async def allbots_do_extend_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    days = int(callback_query.matches[0].group(2))
    page = int(callback_query.matches[0].group(3))
    current_expiry_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    start_date = datetime.now(timezone.utc)
    if current_expiry_str:
        current_expiry = datetime.fromisoformat(current_expiry_str)
        if current_expiry > start_date:
            start_date = current_expiry
    await ctx.db.setVars(
        bot_id, "bot_expiration_date", (start_date + timedelta(days=days)).isoformat()
    )
    await callback_query.answer(
        f"{days} hari berhasil ditambahkan ke bot {bot_id}.",
        show_alert=True,
    )
    invalidate_page_cache(page)
    await send_allbots_list(client, callback_query, page, force_refresh=True)


@command(
    lambda ctx: filters.regex("^allbots_reduce_(\\d+)_(\\d+)"), handler_type="callback"
)
async def allbots_reduce_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))
    buttons = [
        {
            "text": f"-{days} hari",
            "callback_data": f"allbots_do_reduce_{bot_id}_{days}_{page}",
            "style": "red",
            "emoji": client.ns.emoji.id("minus"),
        }
        for days in [7, 30, 90]
    ]
    layout = [
        buttons,
        [
            {
                "text": "• Kembali •",
                "callback_data": f"allbots_duration_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    await callback_query.edit_message_text(
        f"Pilih durasi untuk dikurangi dari Bot `{bot_id}`:",
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


@command(
    lambda ctx: filters.regex("^allbots_do_reduce_(\\d+)_(\\d+)_(\\d+)"),
    handler_type="callback",
)
async def allbots_do_reduce_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    days = int(callback_query.matches[0].group(2))
    page = int(callback_query.matches[0].group(3))
    current_expiry_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    if not current_expiry_str:
        await callback_query.answer(
            "Bot ini tidak memiliki tanggal kedaluwarsa untuk dikurangi.",
            show_alert=True,
        )
        return
    new_expiry_date = datetime.fromisoformat(current_expiry_str) - timedelta(days=days)
    await ctx.db.setVars(bot_id, "bot_expiration_date", new_expiry_date.isoformat())
    await callback_query.answer(
        f"Masa aktif bot {bot_id} berhasil dikurangi {days} hari.",
        show_alert=True,
    )
    invalidate_page_cache(page)
    await send_allbots_list(client, callback_query, page, force_refresh=True)