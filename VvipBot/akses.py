from . import *


@command(lambda ctx: filters.command("akses"))
@seller_only
async def access_command_handler(client, message):
    user_id_target, _ = await client.ns.telegram.arg.getReasonAndId(message)
    if not user_id_target:
        return await message.reply_text(
            "**Format Salah.**\nGunakan: `/akses <user_id atau @username>`",
            parse_mode=ParseMode.MARKDOWN,
        )
    try:
        target_user = await client.get_users(user_id_target)
        has_access = False
        user_expiry_str = await ctx.db.getVars(target_user.id, "user_expiry_date")
        if user_expiry_str:
            expiry_date = datetime.fromisoformat(user_expiry_str)
            if expiry_date > datetime.now(timezone.utc):
                has_access = True
        status_text = (
            f"{client.ns.emoji.white_check_mark} Memiliki Akses"
            if has_access
            else f"{client.ns.emoji.cross_mark} Tidak Memiliki Akses"
        )
        text = (
            f"**{client.ns.emoji.key} Kelola Akses Pembuatan Bot**\n\n"
            f"**Pengguna:** {client.ns.telegram.arg.getMention(target_user)}\n"
            f"**ID:** `{target_user.id}`\n"
            f"**Status:** `{status_text}`\n\n"
            f"Pilih tindakan untuk pengguna ini:"
        )
        layout = [
            [
                {
                    "text": "✅ Beri Akses",
                    "callback_data": f"give_access_{target_user.id}",
                    "style": "green",
                    "emoji": client.ns.emoji.id("white_check_mark"),
                },
                {
                    "text": "❌ Cabut Akses",
                    "callback_data": f"revoke_access_{target_user.id}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("cross_mark"),
                },
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await message.reply_text(text, reply_markup=btn)
    except Exception as e:
        await message.reply_text(f"Gagal memproses. Error: `{e}`")


@command(lambda ctx: filters.regex("^give_access_(\\d+)"), handler_type="callback")
@seller_only
async def give_access_callback(client, callback_query):
    target_id = int(callback_query.data.split("_")[-1])
    layout = [
        [
            {
                "text": f"{m} Bulan",
                "callback_data": f"do_give_{target_id}_{m}",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            }
            for m in [1, 3, 6, 12]
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": "close_panel",
                "style": "red",
                "emoji": client.ns.emoji.id("cross_mark"),
            }
        ],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_text(
        "Pilih durasi akses yang ingin diberikan:", reply_markup=btn
    )


@command(lambda ctx: filters.regex("^do_give_(\\d+)_(\\d+)"), handler_type="callback")
@seller_only
async def do_give_access_callback(client, callback_query):
    _, _, target_id_str, months_str = callback_query.data.split("_")
    target_id = int(target_id_str)
    months_to_add = int(months_str)
    try:
        target_user = await client.get_users(target_id)
        current_expiry_str = await ctx.db.getVars(target_id, "user_expiry_date")
        start_date = datetime.now(timezone.utc)
        if current_expiry_str:
            current_expiry = datetime.fromisoformat(current_expiry_str)
            if current_expiry > start_date:
                start_date = current_expiry
        new_expiry_date = start_date + timedelta(days=30 * months_to_add)
        await ctx.db.setVars(target_id, "user_expiry_date", new_expiry_date.isoformat())
        expiry_in_jakarta = new_expiry_date.astimezone(ZoneInfo("Asia/Jakarta"))

        mention_str = client.ns.telegram.arg.getMention(target_user)
        formatted_jakarta_date = expiry_in_jakarta.strftime("%d %B %Y, %H:%M %Z")
        await callback_query.edit_message_text(
            f"{client.ns.emoji.white_check_mark} **Akses Diberikan!**\n\n"
            f"Pengguna {mention_str} sekarang memiliki akses untuk membuat bot selama **{months_to_add} bulan**.\n\n"
            f"Masa aktif akses hingga: `{formatted_jakarta_date}`"
        )
        await callback_query.answer(
            "<emoji id=6296367896398399651>✅</emoji> Akses berhasil diberikan kepada {target_id}".format(
                target_id=target_id
            )
        )
    except Exception as e:
        await callback_query.answer(f"Gagal memproses. Error: `{e}`", show_alert=True)


@command(lambda ctx: filters.regex("^revoke_access_(\\d+)"), handler_type="callback")
@seller_only
async def revoke_access_callback(client, callback_query):
    target_id = int(callback_query.data.split("_")[-1])
    try:
        target_user = await client.get_users(target_id)
        mention = client.ns.telegram.arg.getMention(target_user)
        await ctx.db.removeVars(target_id, "user_expiry_date")
        await callback_query.answer(
            "<emoji id=6298671811345254603>❌</emoji> Akses berhasil dicabut dari {target_id}".format(
                target_id=target_id
            )
        )
        await callback_query.edit_message_text(
            f"{client.ns.emoji.cross_mark} **Akses Dicabut!**\n\n"
            f"Pengguna {mention} tidak lagi memiliki hak untuk membuat bot."
        )
    except Exception as e:
        await callback_query.answer(f"Gagal memproses. Error: `{e}`", show_alert=True)
