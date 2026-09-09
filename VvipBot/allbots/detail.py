from .. import *
from .helpers import _resolve_owner_text, send_allbots_list


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
