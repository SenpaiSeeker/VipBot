from . import *


@command(lambda ctx: filters.command("listakses") & filters.user(ctx.owner_id))
async def list_akses_handler(client, message):
    user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
    access_users = []
    for uid in user_ids:
        if await ctx.db.getVars(uid, "user_expiry_date"):
            access_users.append(uid)
    if not access_users:
        return await message.reply_text(
            "Tidak ada pengguna yang memiliki akses aktif saat ini."
        )
    text = f"**{client.ns.emoji.key} Daftar Pengguna Berakses**\n\n"
    keyboard = []
    for index, uid in enumerate(access_users, 1):
        try:
            user_obj = await client.get_users(uid)
            mention = client.ns.telegram.arg.getMention(user_obj)
        except Exception:
            mention = f"ID: `{uid}`"
        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"Cabut Akses 🚫 ({uid})",
                    "callback_data": f"del_acc_{uid}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await message.reply_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^del_acc_(\\d+)"), handler_type="callback")
async def delete_access_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    target_id = int(callback_query.matches[0].group(1))
    await ctx.db.removeVars(target_id, "user_expiry_date")
    await callback_query.answer(
        "Akses untuk `{user_id}` telah dicabut.".format(user_id=target_id),
        show_alert=True,
    )
    user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
    access_users = [
        uid for uid in user_ids if await ctx.db.getVars(uid, "user_expiry_date")
    ]
    if not access_users:
        await callback_query.edit_message_text(
            "Tidak ada pengguna yang memiliki akses aktif saat ini."
        )
        return
    text = f"**{client.ns.emoji.key} Daftar Pengguna Berakses**\n\n"
    keyboard = []
    for index, uid in enumerate(access_users, 1):
        try:
            user_obj = await client.get_users(uid)
            mention = client.ns.telegram.arg.getMention(user_obj)
        except Exception:
            mention = f"ID: `{uid}`"
        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"Cabut Akses 🚫 ({uid})",
                    "callback_data": f"del_acc_{uid}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await callback_query.edit_message_text(text, reply_markup=btn)
