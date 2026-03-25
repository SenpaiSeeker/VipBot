import asyncio
import os
from pyrogram import filters
from pyrogram.raw import functions, types
from . import command, ctx


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
            return await message.reply_text(
                "<emoji id=6298671811345254603>❌</emoji> **Target tidak ditemukan.**\nBalas pesan pengguna atau gunakan format:\n`/gift [username] [gift_id]`"
            )
        if not gift_id_arg or not gift_id_arg.isdigit():
            return await message.reply_text(
                "<emoji id=6298671811345254603>❌</emoji> **ID Hadiah tidak valid.**\nGunakan `/listgift` untuk melihat ID."
            )
        gift_id = int(gift_id_arg)
        status_msg = await message.reply_text(
            "<emoji id=5264727218734524899>🔄</emoji> Memproses pengiriman hadiah..."
        )
        available_gifts = await client.get_available_gifts()
        target_gift = next((g for g in available_gifts if g.id == gift_id), None)
        if not target_gift:
            return await status_msg.edit(
                "<emoji id=6298671811345254603>❌</emoji> Gift ID `{id}` tidak ditemukan atau tidak tersedia.".format(
                    id=gift_id
                )
            )
        target_user = await client.get_users(user_id_target)
        mention = client.ns.telegram.arg.getMention(target_user)
        await status_msg.edit(
            "<emoji id=6283073379184415506>🎁</emoji> Mengirim hadiah **Star** (ID: `{id}`) ke **{mention}**...".format(
                id=gift_id, mention=mention
            )
        )
        await send_star_gift_raw(client, target_user.id, gift_id)
        await status_msg.edit(
            "<emoji id=6296367896398399651>✅</emoji> Berhasil mengirim hadiah ke **{mention}**!".format(
                mention=mention
            )
        )
    except Exception as e:
        await message.reply_text(
            "<emoji id=6298671811345254603>❌</emoji> Gagal mengirim hadiah: `{e}`".format(
                e=e
            )
        )


@command(lambda ctx: filters.command("listgift") & filters.user(ctx.owner_id))
async def list_gift_handler(client, message):
    status_msg = await message.reply_text(
        "<emoji id=5264727218734524899>🔄</emoji> Mengambil daftar hadiah..."
    )
    try:
        gifts = await client.get_available_gifts()
        if not gifts:
            return await status_msg.edit(
                "<emoji id=5258503720928288433>ℹ️</emoji> Tidak ada hadiah yang tersedia saat ini."
            )
        for gift in gifts:
            if not gift.is_sold_out:
                price = gift.star_count
                emoji = "❓️"
                if hasattr(gift, "sticker") and hasattr(gift.sticker, "emoji"):
                    emoji = f"{gift.sticker.emoji} "
                caption = "<b><emoji id=6283073379184415506>🎁</emoji> Info Hadiah</b>\n\n<b><emoji id=6269253325477123346>🆔</emoji> ID:</b> <code>{id}</code>\n<b><emoji id=5375296873982604963>💰</emoji> Harga:</b> <code>{price} Stars</code>\n<b><emoji id=5359441070201513074>🎭</emoji> Emoji:</b> {emoji}\n".format(
                    id=gift.id, price=price, emoji=emoji
                )
                buttons = [
                    [
                        {
                            "text": "🎁 Kirim ke Teman",
                            "callback_data": f"gift_send_ask_{gift.id}",
                        }
                    ],
                    [
                        {
                            "text": "👤 Klaim Sendiri",
                            "callback_data": f"gift_claim_self_{gift.id}",
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
                            message.chat.id, text=caption, reply_markup=markup
                        )
                    finally:
                        if file_path and os.path.exists(file_path):
                            os.remove(file_path)
                else:
                    await client.send_message(
                        message.chat.id, text=caption, reply_markup=markup
                    )
                await asyncio.sleep(1.5)
            await status_msg.delete()
    except Exception as e:
        await status_msg.edit(
            "<emoji id=6298671811345254603>❌</emoji> Gagal mengirim hadiah: `{e}`".format(
                e=e
            )
        )


@command(lambda ctx: filters.regex("^gift_claim_self_(\\d+)"), handler_type="callback")
async def claim_self_gift_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True
        )
    gift_id = int(callback_query.data.split("_")[3])
    user_id = callback_query.from_user.id
    try:
        await callback_query.edit_message_reply_markup(None)
        await send_star_gift_raw(client, user_id, gift_id)
        await callback_query.edit_message_caption(
            "<emoji id=6296367896398399651>✅</emoji> Berhasil mengklaim hadiah (ID: {id}) untuk diri sendiri!".format(
                id=gift_id
            )
        )
    except Exception as e:
        await callback_query.answer(
            "<emoji id=6298671811345254603>❌</emoji> Gagal klaim: {e}".format(e=e),
            show_alert=True,
        )


@command(lambda ctx: filters.regex("^gift_send_ask_(\\d+)"), handler_type="callback")
async def ask_send_gift_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True
        )
    gift_id = int(callback_query.data.split("_")[3])
    chat_id = callback_query.message.chat.id
    try:
        await callback_query.edit_message_reply_markup(None)
        prompt = f'''{"""<emoji id=5373012449597335010>👤</emoji> **Kirim Hadiah**

Silakan kirim **User ID** atau **Username** (@username) tujuan penerima hadiah."""}{"""

Ketik `/batal` untuk membatalkan."""}'''
        ask_msg = await client.ask(chat_id, prompt, timeout=60)
        if ask_msg.text.lower() == "/batal":
            return await client.send_message(
                chat_id,
                "<emoji id=6298671811345254603>🚫</emoji> Pengiriman dibatalkan.",
            )
        target_input = ask_msg.text
        processing_msg = await client.send_message(
            chat_id,
            "<emoji id=5264727218734524899>🔄</emoji> Mencari pengguna `{input}`...".format(
                input=target_input
            ),
        )
        try:
            target_user = await client.get_users(target_input)
        except Exception:
            return await processing_msg.edit(
                "<emoji id=6298671811345254603>❌</emoji> Pengguna tidak ditemukan. Pastikan username/ID benar."
            )
        await processing_msg.edit(
            "<emoji id=6283073379184415506>🎁</emoji> Mengirim hadiah **Star** (ID: `{id}`) ke **{mention}**...".format(
                id=gift_id, mention=target_user.first_name
            )
        )
        await send_star_gift_raw(client, target_user.id, gift_id)
        await processing_msg.edit(
            "<emoji id=6296367896398399651>✅</emoji> Berhasil mengirim hadiah ke **{mention}**!".format(
                mention=target_user.first_name
            )
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            "<emoji id=5413704112220949842>⏰</emoji> Waktu habis. Silakan ulangi proses.",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>❌</emoji> Gagal mengirim hadiah: `{e}`".format(
                e=e
            ),
        )
