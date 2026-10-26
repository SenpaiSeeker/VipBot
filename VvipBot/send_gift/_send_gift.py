import asyncio

import aiofiles.os
import pyrogram
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
            return await message.reply_rich(
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Target Tidak Ditemukan**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Target tidak ditemukan'], ['Cara', 'Balas pesan pengguna atau gunakan format'], ['Format', '`/gift [username] [gift_id]`']])}"
                    )
                )
            )
        if not gift_id_arg or not gift_id_arg.isdigit():
            return await message.reply_rich(
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **ID Hadiah Tidak Valid**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'ID hadiah tidak valid'], ['Saran', 'Gunakan `/listgift` untuk melihat ID']])}"
                    )
                )
            )
        gift_id = int(gift_id_arg)
        status_msg = await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('repeat')} **Memproses Pengiriman**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Memproses pengiriman hadiah']])}"
                )
            )
        )
        available_gifts = await client.get_available_gifts()
        target_gift = next(
            (g for g in available_gifts if g.id == gift_id),
            None,
        )
        if not target_gift:
            return await status_msg.edit(
                rich_message=pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Hadiah Tidak Ditemukan**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Gift ID', f'`{gift_id}`'], ['Status', 'Tidak ditemukan atau tidak tersedia']])}"
                    )
                )
            )
        target_user = await client.get_users(user_id_target)
        mention = client.ns.telegram.arg.getMention(target_user, md=True)
        await status_msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('gift')} **Mengirim Hadiah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Hadiah', f'Hadiah **Star** (ID: `{gift_id}`)'], ['Tujuan', f'**{mention}**'], ['Status', 'Mengirim']])}"
                )
            )
        )
        await send_star_gift_raw(client, target_user.id, gift_id)
        await status_msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Berhasil!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Berhasil mengirim hadiah'], ['Penerima', f'**{mention}**']])}"
                )
            )
        )
    except Exception as e:
        await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal Mengirim**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal mengirim hadiah'], ['Error', f'`{e}`']])}"
                )
            )
        )


@command(lambda ctx: filters.command("listgift") & filters.private)
async def list_gift_handler(client, message):
    if not await is_bot_owner(client, message.from_user.id):
        return
    status_msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=f"{client.ns.emoji.md('repeat')} Mengambil daftar hadiah..."
        )
    )
    try:
        gifts = await client.get_available_gifts()
        if not gifts:
            empty_rows = [
                ["Jumlah Hadiah", "`0`"],
                ["Status", "Tidak ada hadiah tersedia"],
            ]
            return await status_msg.edit(
                rich_message=pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('gift')} **Daftar Hadiah**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], empty_rows)}"
                    )
                )
            )
        for gift in gifts:
            if not gift.is_sold_out:
                price = gift.star_count
                emoji = "❓️"
                if hasattr(gift, "sticker") and hasattr(gift.sticker, "emoji"):
                    emoji = f"{gift.sticker.emoji} "

                gift_rows = [
                    [f"{client.ns.emoji.md('id_card')} ID", f"{gift.id}"],
                    [f"{client.ns.emoji.md('money_bag')} Harga", f"{price} Stars"],
                    [f"{client.ns.emoji.md('performing_arts')} Emoji", emoji],
                ]

                rich_text = (
                    f"{client.ns.emoji.md('gift')} **Info Hadiah**\n\n"
                    f"{client.ns.table.md(['Label', 'Isi'], gift_rows)}"
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
                sticker = getattr(gift, "sticker", None)
                thumbs = getattr(sticker, "thumbs", None)
                if thumbs:
                    thumb = thumbs[-1]
                    file_path = None
                    try:
                        file_path = await client.download_media(thumb.file_id)
                        await client.send_rich_message(
                            message.chat.id,
                            client.ns.table.rich_photo(
                                photo=file_path,
                                markdown=rich_text,
                                alias=f"gift_{gift.id}",
                            ),
                            reply_markup=markup,
                        )
                    except Exception:
                        await client.send_rich_message(
                            message.chat.id,
                            pyrogram.types.InputRichMessage(markdown=rich_text),
                            reply_markup=markup,
                        )
                    finally:
                        if file_path and await aiofiles.os.path.exists(file_path):
                            await aiofiles.os.remove(file_path)
                else:
                    await client.send_rich_message(
                        message.chat.id,
                        pyrogram.types.InputRichMessage(markdown=rich_text),
                        reply_markup=markup,
                    )
                await asyncio.sleep(1.5)
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} Gagal mengirim hadiah: `{e}`"
            )
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
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Hadiah Berhasil Diklaim**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Gift ID', f'`{gift_id}`'], ['Penerima', 'Diri sendiri']])}"
                )
            )
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
            f"**{client.ns.emoji.md('bust_in_silhouette')} Kirim Hadiah**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Instruksi', 'Silakan kirim **User ID** atau **Username** (@username) tujuan penerima hadiah'], ['Batal', 'Ketik `/batal` untuk membatalkan']])}"
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=60)
        if not ask_msg.text:
            raise ValueError("Input harus berupa User ID atau username.")
        if ask_msg.text.lower() == "/batal":
            await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Dibatalkan**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Pengiriman dibatalkan']])}"
                    )
                ),
            )
            return
        target_input = ask_msg.text
        processing_msg = await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('repeat')} **Mencari Pengguna**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', f'Mencari pengguna `{target_input}`']])}"
                )
            ),
        )
        try:
            target_user = await client.get_users(target_input)
        except Exception:
            await processing_msg.edit(
                rich_message=pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Pengguna Tidak Ditemukan**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Masukan', f'`{target_input}`'], ['Status', 'Pengguna tidak ditemukan'], ['Saran', 'Pastikan username/ID benar']])}"
                    )
                )
            )
            return
        await processing_msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('gift')} **Mengirim Hadiah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Hadiah', f'Hadiah **Star** (ID: `{gift_id}`)'], ['Tujuan', f'**{target_user.first_name}**'], ['Status', 'Mengirim']])}"
                )
            )
        )
        await send_star_gift_raw(client, target_user.id, gift_id)
        await processing_msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Berhasil!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Berhasil mengirim hadiah'], ['Penerima', f'**{target_user.first_name}**']])}"
                )
            )
        )
    except asyncio.TimeoutError:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('alarm_clock')} **Waktu Habis**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Waktu habis'], ['Aksi', 'Silakan ulangi proses']])}"
                )
            ),
        )
    except Exception as e:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal Mengirim**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal mengirim hadiah'], ['Error', f'`{e}`']])}"
                )
            ),
        )
