import asyncio

import pyrogram
from pyrogram import filters

from .. import command, ctx, is_bot_owner, listen


@command(
    lambda ctx: filters.regex("^set_broadcast_price$"),
    handler_type="callback",
)
async def set_broadcast_price_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        prompt = (
            f"{client.ns.emoji.md('glowing_star')} **Atur Harga Broadcast Paid**\n\n"
            f"Masukkan jumlah Bintang (Stars) yang harus dibayar pengguna.\n\n"
            f"Ketik `0` atau `/empty` untuk menonaktifkan.\n\n"
            f"Ketik `/batal` untuk membatalkan."
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=300)

        if ask_msg.text:
            if ask_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if ask_msg.text.lower() in ["/empty", "0"]:
                await ctx.db.removeVars(client.me.id, "broadcast_price")

                return await client.send_rich_message(
                    chat_id,
                    pyrogram.types.InputRichMessage(
                        markdown=(
                            f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n\n"
                            f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Fitur Paid Broadcast dinonaktifkan']])}"
                        )
                    ),
                    reply_markup=back_btn,
                )

        if not ask_msg.text.isdigit():
            raise ValueError("**Format Salah**")

        stars_amount = int(ask_msg.text)
        await ctx.db.setVars(client.me.id, "broadcast_price", stars_amount)

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Harga broadcast diperbarui'], ['Harga', f'`{stars_amount}` Stars']])}"
                )
            ),
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError, ValueError) as e:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Proses Dibatalkan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Dibatalkan'], ['Keterangan', f'{e}']])}"
                )
            ),
            reply_markup=back_btn,
        )


async def _send_broadcast_message(
    client, target_user_id, source_message, broadcast_price=0
):
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

    if not hasattr(ctx, "broadcast_stop"):
        ctx.broadcast_stop = {}
    ctx.broadcast_stop[bot_id] = False

    try:
        await callback_query.message.delete()
        prompt = (
            f"{client.ns.emoji.md('loudspeaker')} **Kirim Pesan Broadcast**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Instruksi', 'Teruskan (forward) atau kirim pesan yang ingin disiarkan'], ['Batal', 'Ketik `/batal` untuk membatalkan']])}"
        )
        ask_message = await client.ask(chat_id, text=prompt, timeout=600)

        if ask_message.text and ask_message.text.lower() == "/batal":
            raise listen.UserCancelled

        broadcast_price = await ctx.db.getVars(bot_id, "broadcast_price") or 0
        broadcast_price = int(broadcast_price)

        if broadcast_price > 0 and (not (ask_message.photo or ask_message.video)):
            raise ValueError(
                f"{client.ns.emoji.md('cross_mark')} **Gagal:** Paid Broadcast memerlukan media foto/video!"
            )

        user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
        if not user_ids:
            empty_rows = [
                ["Jumlah Pengguna", "`0`"],
                ["Status", "Tidak ada pengguna terdaftar"],
                ["Saran", "Tambahkan pengguna terlebih dahulu"],
            ]
            return await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Siaran Gagal**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], empty_rows)}"
                    )
                ),
            )

        progress_msg = await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Memulai Siaran**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Siaran dimulai'], ['Jumlah', f'`{len(user_ids)}` pengguna'], ['Berhenti', 'Tekan tombol dibawah untuk berhenti']])}"
                )
            ),
            reply_markup=client.ns.telegram.button.build_button_grid(
                [
                    [
                        {
                            "text": "BATALKAN",
                            "callback_data": f"broadcast_cancel_{bot_id}",
                            "style": "red",
                        }
                    ]
                ]
            ),
        )
        success_count, fail_count = 0, 0
        should_stop = False

        async def send_to_user(target_user_id):
            nonlocal success_count, fail_count
            from .. import ctx

            if getattr(ctx, "broadcast_stop", {}).get(client.me.id):
                nonlocal should_stop
                should_stop = True
                return
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
            if should_stop:
                break
            if user_id != ctx.owner_id:
                await send_to_user(user_id)

        await progress_msg.delete()

        status_title = (
            f"{client.ns.emoji.md('cross_mark')} **Siaran Dibatalkan!**"
            if should_stop
            else f"{client.ns.emoji.md('loudspeaker')} **Siaran Selesai!**"
        )
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{status_title}\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Dibatalkan' if should_stop else 'Selesai'], ['Terkirim', f'`{success_count}`'], ['Gagal', f'`{fail_count}`']])}"
            ),
        )

    except (listen.UserCancelled, asyncio.TimeoutError, ValueError) as e:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal/Batal**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal/Batal'], ['Keterangan', f'{e}']])}"
                )
            ),
        )


@command(
    lambda ctx: filters.regex("^broadcast_cancel_"),
    handler_type="callback",
)
async def broadcast_cancel_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer("🚫 Akses ditolak", show_alert=True)

    await callback_query.answer(
        "Siaran akan dihentikan setelah pengiriman saat ini...", show_alert=False
    )
    from .. import ctx

    if not hasattr(ctx, "broadcast_stop"):
        ctx.broadcast_stop = {}
    ctx.broadcast_stop[client.me.id] = True
