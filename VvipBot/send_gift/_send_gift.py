import asyncio

import aiofiles.os
from pyrogram import filters
from pyrogram.raw import functions, types

from .. import command, is_bot_owner


async def send_star_gift_raw(client, user_id: int, gift_id: int):
    peer = await client.resolve_peer(user_id)
    invoice = types.InputInvoiceStarGift(peer=peer, gift_id=int(gift_id))
    payment_form = await client.invoke(
        functions.payments.GetPaymentForm(invoice=invoice)
    )
    form_id = payment_form.form_id
    result = await client.invoke(
        functions.payments.SendStarsForm(form_id=form_id, invoice=invoice)
    )
    return result


@command(lambda ctx: filters.command("gift") & filters.private)
async def send_gift_handler(client, message):
    if not await is_bot_owner(client, message.from_user.id):
        return
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
            return await message.reply_text(
                f"{client.ns.emoji.cross_mark} **Target tidak ditemukan.**\nBalas pesan pengguna atau gunakan format:\n`/gift [username] [gift_id]`"
            )
        if not gift_id_arg or not gift_id_arg.isdigit():
            return await message.reply_text(
                f"{client.ns.emoji.cross_mark} **ID Hadiah tidak valid.**\nGunakan `/listgift` untuk melihat ID."
            )
        gift_id = int(gift_id_arg)
        status_msg = await message.reply_text(
            f"{client.ns.emoji.repeat} Memproses pengiriman hadiah..."
        )
        available_gifts = await client.get_available_gifts()
        target_gift = next(
            (g for g in available_gifts if g.id == gift_id),
            None,
        )
        if not target_gift:
            return await status_msg.edit(
                f"{client.ns.emoji.cross_mark} Gift ID `{gift_id}` tidak ditemukan atau tidak tersedia."
            )
        target_user = await client.get_users(user_id_target)
        mention = client.ns.telegram.arg.getMention(target_user)
        await status_msg.edit(
            f"{client.ns.emoji.gift} Mengirim hadiah **Star** (ID: `{gift_id}`) ke **{mention}**..."
        )
        await send_star_gift_raw(client, target_user.id, gift_id)
        await status_msg.edit(
            f"{client.ns.emoji.white_check_mark} Berhasil mengirim hadiah ke **{mention}**!"
        )
    except Exception as e:
        await message.reply_text(
            f"{client.ns.emoji.cross_mark} Gagal mengirim hadiah: `{e}`"
        )


@command(lambda ctx: filters.command("listgift") & filters.private)
async def list_gift_handler(client, message):
    if not await is_bot_owner(client, message.from_user.id):
        return
    status_msg = await message.reply_text(
        f"{client.ns.emoji.repeat} Mengambil daftar hadiah..."
    )
    try:
        gifts = await client.get_available_gifts()
        if not gifts:
            return await status_msg.edit(
                f"{client.ns.emoji.exclamation} Tidak ada hadiah yang tersedia saat ini."
            )
        for gift in gifts:
            if not gift.is_sold_out:
                price = gift.star_count
                emoji = "❓️"
                if hasattr(gift, "sticker") and hasattr(gift.sticker, "emoji"):
                    emoji = f"{gift.sticker.emoji} "

                caption = (
                    f"<b>{client.ns.emoji.gift} Info Hadiah</b>\n\n"
                    f"<b>{client.ns.emoji.id_card} ID:</b> <code>{gift.id}</code>\n"
                    f"<b>{client.ns.emoji.money_bag} Harga:</b> <code>{price} Stars</code>\n"
                    f"<b>{client.ns.emoji.performing_arts} Emoji:</b> {emoji}\n"
                )
                buttons = [
                    [
                        {
                            "text": "🎁 Kirim ke Teman",
                            "callback_data": f"gift_send_ask_{gift.id}",
                            "style": "blue",
                            "emoji": client.ns.emoji.id("gift"),
                        }
                    ],
                    [
                        {
                            "text": "👤 Klaim Sendiri",
                            "callback_data": f"gift_claim_self_{gift.id}",
                            "style": "green",
                            "emoji": client.ns.emoji.id("bust_in_silhouette"),
                        }
                    ],
                ]
                markup = client.ns.telegram.button.build_button_grid(buttons)
                if hasattr(gift, "sticker") and gift.sticker.thumbs:
                    thumb = gift.sticker.thumbs[-1]
                    file_path = None
                    try:
                        file_path = await client.download_media(thumb.file_id)
                        await client.send_photo(
                            message.chat.id,
                            photo=file_path,
                            caption=caption,
                            reply_markup=markup,
                        )
                    except Exception:
                        await client.send_message(
                            message.chat.id,
                            text=caption,
                            reply_markup=markup,
                        )
                    finally:
                        if file_path and await aiofiles.os.path.exists(file_path):
                            await aiofiles.os.remove(file_path)
                else:
                    await client.send_message(
                        message.chat.id,
                        text=caption,
                        reply_markup=markup,
                    )
                await asyncio.sleep(1.5)
            await status_msg.delete()
    except Exception as e:
        await status_msg.edit(
            f"{client.ns.emoji.cross_mark} Gagal mengirim hadiah: `{e}`"
        )


@command(
    lambda ctx: filters.regex("^gift_claim_self_(\\d+)"),
    handler_type="callback",
)
async def claim_self_gift_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )
    gift_id = int(callback_query.data.split("_")[3])
    user_id = callback_query.from_user.id
    try:
        await callback_query.edit_message_reply_markup(None)
        await send_star_gift_raw(client, user_id, gift_id)
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.white_check_mark} Berhasil mengklaim hadiah (ID: {gift_id}) untuk diri sendiri!"
        )
    except Exception as e:
        await callback_query.answer(
            "❌ Gagal klaim: {e}".format(e=e),
            show_alert=True,
        )


@command(
    lambda ctx: filters.regex("^gift_send_ask_(\\d+)"),
    handler_type="callback",
)
async def ask_send_gift_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )
    gift_id = int(callback_query.data.split("_")[3])
    chat_id = callback_query.message.chat.id
    try:
        await callback_query.edit_message_reply_markup(None)
        prompt = (
            f"**{client.ns.emoji.bust_in_silhouette} Kirim Hadiah**\n\n"
            f"Silakan kirim **User ID** atau **Username** (@username) tujuan penerima hadiah.\n\n"
            f"Ketik `/batal` untuk membatalkan."
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=60)
        if ask_msg.text.lower() == "/batal":
            await client.send_message(
                chat_id,
                f"{client.ns.emoji.cross_mark} Pengiriman dibatalkan.",
            )
            return
        target_input = ask_msg.text
        processing_msg = await client.send_message(
            chat_id,
            f"{client.ns.emoji.repeat} Mencari pengguna `{target_input}`...",
        )
        try:
            target_user = await client.get_users(target_input)
        except Exception:
            await processing_msg.edit(
                f"{client.ns.emoji.cross_mark} Pengguna tidak ditemukan. Pastikan username/ID benar."
            )
            return
        await processing_msg.edit(
            f"{client.ns.emoji.gift} Mengirim hadiah **Star** (ID: `{gift_id}`) ke **{target_user.first_name}**..."
        )
        await send_star_gift_raw(client, target_user.id, gift_id)
        await processing_msg.edit(
            f"{client.ns.emoji.white_check_mark} Berhasil mengirim hadiah ke **{target_user.first_name}**!"
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.alarm_clock} Waktu habis. Silakan ulangi proses.",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} Gagal mengirim hadiah: `{e}`",
        )
