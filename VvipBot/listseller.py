from . import *


@command(lambda ctx: filters.command("listseller") & filters.user(ctx.owner_id))
async def list_seller_handler(client, message):
    seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
    if not seller_list:
        return await message.reply_text("Belum ada seller yang terdaftar.")
    text = f"**{client.ns.emoji.bust_in_silhouette} Daftar Seller Aktif**\n\n"
    keyboard = []
    for index, user_id in enumerate(seller_list, 1):
        try:
            user_obj = await client.get_users(user_id)
            mention = client.ns.telegram.arg.getMention(user_obj)
        except Exception:
            mention = f"ID: `{user_id}`"
        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"Hapus Seller 🗑️ ({user_id})",
                    "callback_data": f"del_sell_{user_id}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await message.reply_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^del_sell_(\\d+)"), handler_type="callback")
async def delete_seller_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    target_id = int(callback_query.matches[0].group(1))
    await ctx.db.removeListVars(ctx.owner_id, "seller_id_list", target_id)
    await callback_query.answer(
        "Seller `{user_id}` berhasil dihapus.".format(user_id=target_id),
        show_alert=True,
    )
    seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
    if not seller_list:
        await callback_query.edit_message_text("Belum ada seller yang terdaftar.")
        return
    text = f"**{client.ns.emoji.bust_in_silhouette} Daftar Seller Aktif**\n\n"
    keyboard = []
    for index, user_id in enumerate(seller_list, 1):
        try:
            user_obj = await client.get_users(user_id)
            mention = client.ns.telegram.arg.getMention(user_obj)
        except Exception:
            mention = f"ID: `{user_id}`"
        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"Hapus Seller 🗑️ ({user_id})",
                    "callback_data": f"del_sell_{user_id}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await callback_query.edit_message_text(text, reply_markup=btn)
