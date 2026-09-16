from . import *


@command(lambda ctx: filters.command("addseller") & filters.user(ctx.owner_id))
async def add_seller_handler(client, message):
    user_id_target, _ = await client.ns.telegram.arg.getReasonAndId(message)
    if not user_id_target:
        return await message.reply_text(
            f"{client.ns.emoji.cross_mark} Pengguna tidak ditemukan. Pastikan ID/Username benar atau balas pesan pengguna."
        )
    try:
        target_user = await client.get_users(user_id_target)
        seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
        if target_user.id in seller_list:
            return await message.reply_text(
                f"{client.ns.emoji.cross_mark} User `{target_user.id}` sudah terdaftar sebagai seller."
            )
        await ctx.db.setListVars(ctx.owner_id, "seller_id_list", target_user.id)
        user_mention = client.ns.telegram.arg.getMention(target_user)
        await message.reply_text(
            f"{client.ns.emoji.white_check_mark} Berhasil menambahkan `{user_mention}` sebagai seller."
        )
    except Exception as e:
        await message.reply_text(
            f"{client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>{e}</pre>"
        )
