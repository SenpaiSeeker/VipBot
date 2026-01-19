import pyrogram
from pyrogram import filters
from pyrogram.raw import functions, types

from . import command, ctx

async def send_star_gift_raw(client, user_id: int, gift_id: int):
    peer = await client.resolve_peer(user_id)

    invoice = types.InputInvoiceStarGift(
        peer=peer,
        gift_id=int(gift_id)
    )

    payment_form = await client.invoke(
        functions.payments.GetPaymentForm(
            invoice=invoice
        )
    )

    form_id = payment_form.form_id

    result = await client.invoke(
        functions.payments.SendStarsForm(
            form_id=form_id,
            invoice=invoice
        )
    )

    return result

@command(lambda ctx: filters.command("gift") & filters.user(ctx.owner_id))
async def send_gift_handler(client, message):
    try:
        user_id_target = None
        gift_id_arg = None

        if message.reply_to_message:
            user_id_target = message.reply_to_message.from_user.id
            if len(message.command) > 1:
                gift_id_arg = message.command[1]
        elif len(message.command) > 2:
            try:
                user = await client.get_users(message.command[1])
                user_id_target = user.id
                gift_id_arg = message.command[2]
            except Exception:
                pass
        
        if not user_id_target:
            return await message.reply_text("❌ Target pengguna tidak ditemukan. Balas pesan pengguna atau gunakan format: `/gift [username] [gift_id]`")

        if not gift_id_arg or not gift_id_arg.isdigit():
            return await message.reply_text("❌ ID Hadiah tidak valid. Gunakan `/listgift` untuk melihat ID.")

        gift_id = int(gift_id_arg)
        
        status_msg = await message.reply_text("🔄 Memproses pengiriman hadiah...")

        available_gifts = await client.get_available_gifts()
        target_gift = next((g for g in available_gifts if g.id == gift_id), None)

        if not target_gift:
            return await status_msg.edit(f"❌ Gift ID `{gift_id}` tidak ditemukan atau tidak tersedia.")

        target_user = await client.get_users(user_id_target)
        mention = client.ns.telegram.arg.getMention(target_user)

        await status_msg.edit(f"🎁 Mengirim hadiah **Star** (ID: {gift_id}) ke {mention}...")

        await send_star_gift_raw(client, target_user.id, gift_id)

        await status_msg.edit(f"✅ Berhasil mengirim hadiah ke {mention}!")

    except Exception as e:
        error_text = str(e)
        if "BALANCE_TOO_LOW" in error_text:
            error_text = "Saldo Telegram Stars Anda tidak mencukupi."
        await message.reply_text(f"❌ Gagal mengirim hadiah: {error_text}")

@command(lambda ctx: filters.command("listgift") & filters.user(ctx.owner_id))
async def list_gift_handler(client, message):
    status_msg = await message.reply_text("🔄 Mengambil daftar hadiah...")

    try:
        gifts = await client.get_available_gifts()
        
        if not gifts:
            return await status_msg.edit("ℹ️ Tidak ada hadiah yang tersedia saat ini.")

        output = "**🎁 Daftar Hadiah Tersedia**\n\n"
        
        for gift in gifts:
            price = gift.stars
            output += f"• ID: `{gift.id}` - ⭐ {price}\n"

        await status_msg.edit(output)

    except Exception as e:
        await status_msg.edit(f"❌ Gagal mengambil daftar hadiah: {e}")
