from .. import *
from .helpers import invalidate_page_cache, send_allbots_list


def _expiry_delta_layout(client, bot_id: int, page: int, sign: str, days: int):
    callback_prefix = f"allbots_do_{'extend' if sign == '+' else 'reduce'}"
    style = "green" if sign == "+" else "red"
    emoji = client.ns.emoji.id("plus") if sign == "+" else client.ns.emoji.id("minus")
    return {
        "text": f"{sign}{days} hari",
        "callback_data": f"{callback_prefix}_{bot_id}_{days}_{page}",
        "style": style,
        "emoji": emoji,
    }


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
        _expiry_delta_layout(client, bot_id, page, "+", days) for days in [7, 30, 90]
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
        _expiry_delta_layout(client, bot_id, page, "-", days) for days in [7, 30, 90]
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