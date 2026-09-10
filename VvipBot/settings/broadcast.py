import asyncio

import pyrogram
from pyrogram import filters

from .. import command, ctx, is_bot_owner, listen


def _back_to_settings_layout(client):
    return [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]


@command(
    lambda ctx: filters.regex("^set_broadcast_price$"),
    handler_type="callback",
)
async def set_broadcast_price_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()
    back_btn = client.ns.telegram.button.build_button_grid(
        _back_to_settings_layout(client)
    )

    try:
        prompt = (
            f"**{client.ns.emoji.glowing_star} Atur Harga Broadcast Paid**\n\n"
            "Masukkan jumlah Bintang (Stars) yang harus dibayar pengguna.\n\n"
            "Ketik `0` atau `/empty` untuk menonaktifkan.\n\n"
            "Ketik `/batal` untuk membatalkan."
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=300)

        if ask_msg.text:
            if ask_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if ask_msg.text.lower() in ["/empty", "0"]:
                await ctx.db.removeVars(client.me.id, "broadcast_price")
                return await client.send_message(
                    chat_id,
                    f"{client.ns.emoji.white_check_mark} **Sukses!** Fitur Paid Broadcast dinonaktifkan.",
                    reply_markup=back_btn,
                )

        if not ask_msg.text.isdigit():
            raise ValueError("**Format Salah**")

        stars_amount = int(ask_msg.text)
        await ctx.db.setVars(client.me.id, "broadcast_price", stars_amount)
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} **Sukses!** Harga broadcast telah diatur menjadi `{stars_amount}` Stars.",
            reply_markup=back_btn,
        )
    except (listen.UserCancelled, asyncio.TimeoutError, ValueError) as e:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**\n{e}",
            reply_markup=back_btn,
        )


async def _send_broadcast_message(client, target_user_id, source_message, broadcast_price=0):
    caption_or_text = source_message.caption or source_message.text
    text_to_parse = caption_or_text.markdown if caption_or_text else ""
    reply_markup, cleaned_text = client.ns.telegram.button.create_inline_keyboard(
        text_to_parse
    )
    final_markup = (
        reply_markup
        if reply_markup.inline_keyboard
        else (source_message.reply_markup if source_message.reply_markup else None)
    )

    if broadcast_price > 0 and (source_message.photo or source_message.video):
        media_list = []
        if source_message.photo:
            media_list.append(
                pyrogram.types.InputPaidMediaPhoto(
                    source_message.photo.sizes[-1].file_id
                )
            )
        elif source_message.video:
            media_list.append(
                pyrogram.types.InputPaidMediaVideo(source_message.video.file_id)
            )
        await client.send_paid_media(
            chat_id=target_user_id,
            star_count=broadcast_price,
            media=media_list,
            caption=cleaned_text,
            reply_markup=final_markup,
        )
        return

    if source_message.photo:
        await client.send_photo(
            chat_id=target_user_id,
            photo=source_message.photo.sizes[-1].file_id,
            caption=cleaned_text,
            reply_markup=final_markup,
        )
    elif source_message.text:
        await client.send_message(
            chat_id=target_user_id,
            text=cleaned_text,
            reply_markup=final_markup,
        )
    else:
        await source_message.copy(
            chat_id=target_user_id,
            caption=cleaned_text,
            reply_markup=final_markup,
        )


@command(
    lambda ctx: filters.regex("^broadcast$"),
    handler_type="callback",
)
async def broadcast_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    chat_id = callback_query.message.chat.id
    bot_id = client.me.id

    try:
        await callback_query.message.delete()
        prompt = (
            f"**{client.ns.emoji.loudspeaker} Kirim Pesan Broadcast**\n\n"
            "Silakan teruskan (forward) atau kirim pesan yang ingin disiarkan.\n\n"
            "Ketik `/batal` untuk membatalkan."
        )
        ask_message = await client.ask(chat_id, text=prompt, timeout=600)
        if ask_message.text and ask_message.text.lower() == "/batal":
            raise listen.UserCancelled

        broadcast_price = await ctx.db.getVars(bot_id, "broadcast_price") or 0
        broadcast_price = int(broadcast_price)

        if broadcast_price > 0 and (not (ask_message.photo or ask_message.video)):
            raise ValueError(
                f"{client.ns.emoji.cross_mark} **Gagal:** Paid Broadcast memerlukan media foto/video!"
            )

        user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
        if not user_ids:
            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.cross_mark} **Gagal:** Tidak ada pengguna.",
            )

        progress_msg = await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} Memulai siaran ke `{len(user_ids)}` pengguna...",
        )
        success_count, fail_count = 0, 0

        async def send_to_user(target_user_id):
            nonlocal success_count, fail_count
            try:
                await _send_broadcast_message(
                    client,
                    target_user_id,
                    ask_message,
                    broadcast_price,
                )
                success_count += 1
            except pyrogram.errors.FloodWait as e:
                await asyncio.sleep(e.value + 1)
                await send_to_user(target_user_id)
            except Exception:
                await ctx.db.removeListVars(client.me.id, "user_ids", target_user_id)
                fail_count += 1
            await asyncio.sleep(0.1)

        for user_id in user_ids:
            if user_id != ctx.owner_id:
                await send_to_user(user_id)

        await progress_msg.delete()
        await client.send_message(
            chat_id,
            f"**{client.ns.emoji.loudspeaker} Siaran Selesai!**\n"
            f"{client.ns.emoji.white_check_mark} **Terkirim:** `{success_count}`\n"
            f"{client.ns.emoji.cross_mark} **Gagal:** `{fail_count}`",
        )
    except (listen.UserCancelled, asyncio.TimeoutError, ValueError) as e:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Gagal/Batal**\n{e}",
        )