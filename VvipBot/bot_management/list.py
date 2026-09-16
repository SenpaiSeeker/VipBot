from datetime import datetime, timezone

from pyrogram import filters

from .. import command, ctx


@command(
    lambda ctx: filters.regex("^list_my_bots(_\\d+)?$"),
    handler_type="callback",
)
async def list_my_bots_callback(client, callback_query):
    user_id = callback_query.from_user.id
    my_bots = []
    all_bots_data = await ctx.db.getBots(is_token=True)

    for b in all_bots_data:
        owner = await ctx.db.getVars(int(b["name"]), "owner_id")

        if (owner or 0) == user_id:
            my_bots.append(b)

    if not my_bots:
        return await callback_query.answer(
            "Anda belum memiliki bot. Tekan 'Buat Bot' untuk memulai.",
            show_alert=True,
        )

    parts = callback_query.data.split("_")
    page = int(parts[-1]) if len(parts) > 2 and parts[-1].isdigit() else 0

    total_pages = len(my_bots)
    page = (page + total_pages) % total_pages

    bot_data = my_bots[page]
    bot_id = int(bot_data["name"])

    bot_name = f"ID {bot_id} (Offline)"
    bot_username = "N/A"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username
    except Exception:
        bot_name = f"ID {bot_id} (Error)"

    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    days_left = (
        (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days
        if exp_date_str
        else "N/A"
    )

    text = (
        f"**{client.ns.emoji.folder} Daftar Bot Saya ({page + 1}/{total_pages})**\n\n"
        f"• **Nama Bot:** {bot_name}\n"
        f"• **ID Bot:** `{bot_id}`\n"
        f"• **Username Bot:** @{bot_username}\n"
        f"• **Sisa Masa Aktif:** `{days_left}` hari"
    )

    layout = []
    pagination_row = []

    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages

        pagination_row.extend(
            [
                {
                    "text": "« Sebelumnya",
                    "callback_data": f"list_my_bots_{prev_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                },
                {
                    "text": "Selanjutnya »",
                    "callback_data": f"list_my_bots_{next_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("right_pointing"),
                },
            ]
        )

    if pagination_row:
        layout.append(pagination_row)

    layout.extend(
        [
            [
                {
                    "text": f"⚙️ Kelola {bot_name}",
                    "callback_data": f"manage_bot {bot_id}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("toolbox"),
                }
            ],
            [
                {
                    "text": "• Kembali •",
                    "callback_data": "start",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^manage_bot\\s(\\d+)"),
    handler_type="callback",
)
async def manage_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    owner_of_target_bot = await ctx.db.getVars(bot_id_to_manage, "owner_id") or 0

    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await callback_query.answer("Ini bukan bot milik Anda.", show_alert=True)

    bot_name = f"ID {bot_id_to_manage}"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    exp_date_str = await ctx.db.getVars(bot_id_to_manage, "bot_expiration_date")
    days_left_text = "Tidak diatur"

    if exp_date_str:
        days_left = (
            datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)
        ).days
        days_left_text = f"{days_left} hari"

    layout = [
        [
            {
                "text": "➕ Minta Perpanjangan",
                "callback_data": f"request_extend_duration {bot_id_to_manage}",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            }
        ],
        [
            {
                "text": "🗑️ Hapus Bot Ini",
                "callback_data": f"confirm_delete_bot {bot_id_to_manage}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ],
        [
            {
                "text": "⬅️ Kembali ke Daftar Bot",
                "callback_data": "list_my_bots_0",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]

    text = (
        f"**{client.ns.emoji.toolbox} Kelola Bot: {bot_name}**\n\n"
        f"**ID Bot:** `{bot_id_to_manage}`\n"
        f"**Sisa Masa Aktif:** `{days_left_text}`\n\n"
        f"Pilih tindakan yang ingin Anda lakukan:"
    )

    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)
