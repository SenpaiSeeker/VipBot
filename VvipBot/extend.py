from . import *


@command(lambda ctx: filters.command("extend") & filters.user(ctx.owner_id))
async def extend_command_handler(client, message):
    bot_id, days_str = await client.ns.telegram.arg.getReasonAndId(message)
    if not bot_id or not days_str:
        return await message.reply_text(
            "**Format salah.**\nGunakan: `/extend <bot_id/@username> <jumlah_hari>` atau reply ke pesan bot.\nContoh: `/extend 12345678 30` atau `/extend @namabot 30`"
        )
    try:
        days_to_add = int(days_str.strip())
    except ValueError:
        return await message.reply_text(
            "**Format salah.** `jumlah_hari` harus berupa angka bulat.\nContoh: `/extend 12345678 30`"
        )
    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    current_exp_date = (
        datetime.fromisoformat(exp_date_str)
        if exp_date_str
        else datetime.now(timezone.utc)
    )
    new_exp_date = current_exp_date + timedelta(days=days_to_add)
    await ctx.db.setVars(bot_id, "bot_expiration_date", new_exp_date.isoformat())

    formatted_new_date = new_exp_date.strftime("%d %b %Y")
    await message.reply_text(
        f"{client.ns.emoji.white_check_mark} **Sukses!** Durasi bot `{bot_id}` berhasil diubah. Masa aktif baru: `{formatted_new_date}`."
    )
    owner_bot_id = await ctx.db.getVars(bot_id, "owner_id")
    if owner_bot_id:
        try:
            bot_instance = ctx.manager.running_bots.get(bot_id)
            bot_name = bot_instance.me.first_name if bot_instance else f"ID {bot_id}"
            await client.send_message(
                owner_bot_id,
                f"{client.ns.emoji.party_popper} **Kabar Baik!**\n\nMasa aktif bot Anda **{bot_name}** telah diperpanjang oleh Owner Utama.",
            )
        except Exception:
            pass
