from datetime import datetime, timezone

from telethon import events

from .. import command, ctx


@command(lambda ctx: events.CallbackQuery(pattern=b"^allbots_detail_"))
async def allbots_detail_callback(client, event):
    em = client.ns.emoji
    payload = event.data.decode("utf-8")
    parts = payload.split("_")
    bot_id = int(parts[2])

    bot_name = f"ID {bot_id} (Offline)"
    bot_username = "N/A"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected():
            bot_name = bot_instance.me.first_name
            bot_username = f"@{bot_instance.me.username}"
    except Exception:
        pass

    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    owner_id = await ctx.db.getVars(bot_id, "owner_id")
    days_left_text = "Tidak diatur"

    if exp_date_str:
        exp_date = datetime.fromisoformat(exp_date_str)
        days_left = (exp_date - datetime.now(timezone.utc)).days
        status_icon = em.white_check_mark if days_left > 0 else em.cross_mark
        days_left_text = f"{status_icon} {days_left} hari"

    text = (
        f"{em.robot} <b>Detail Bot</b>\n\n"
        f"<b>Nama:</b> {bot_name}\n"
        f"<b>Username:</b> {bot_username}\n"
        f"<b>ID:</b> <code>{bot_id}</code>\n"
        f"<b>Owner ID:</b> <code>{owner_id or 'N/A'}</code>\n"
        f"<b>Sisa Masa Aktif:</b> {days_left_text}"
    )

    layout = [
        [
            {
                "text": "🗑️ Hapus Bot",
                "callback_data": f"allbots_confirm_delete_{bot_id}",
                "style": "danger",
                "emoji": 5229113891081956317,
            },
            {
                "text": "⏳ Kelola Masa Aktif",
                "callback_data": f"allbots_duration_{bot_id}",
                "style": "primary",
                "emoji": 5449428597922079323,
            },
        ],
        [
            {
                "text": "◀️ Kembali ke Daftar",
                "callback_data": "allbots_list_0",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")
