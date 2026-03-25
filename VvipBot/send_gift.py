import asyncio
import os

from pyrogram import filters
from pyrogram.raw import functions, types

from . import command, ctx


async def send_star_gift_raw(client, user_id: int, gift_id: int):
    peer = await client.resolve_peer(user_id)

    invoice = types.InputInvoiceStarGift(peer=peer, gift_id=int(gift_id))

    payment_form = await client.invoke(functions.payments.GetPaymentForm(invoice=invoice))

    form_id = payment_form.form_id

    result = await client.invoke(functions.payments.SendStarsForm(form_id=form_id, invoice=invoice))

    return result


@command(lambda ctx: filters.command("gift") & filters.user(ctx.owner_id))
async def send_gift_handler(client, message):
    lang = message.texts
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
            return await message.reply_text(lang.get("gift.usage_error"))

        if not gift_id_arg or not gift_id_arg.isdigit():
            return await message.reply_text(lang.get("gift.invalid_id"))

        gift_id = int(gift_id_arg)

        status_msg = await message.reply_text(lang.get("gift.processing"))

        available_gifts = await client.get_available_gifts()
        target_gift = next((g for g in available_gifts if g.id == gift_id), None)

        if not target_gift:
            return await status_msg.edit(lang.get("gift.not_found", id=gift_id))

        target_user = await client.get_users(user_id_target)
        mention = client.ns.telegram.arg.getMention(target_user)

        await status_msg.edit(lang.get("gift.sending", id=gift_id, mention=mention))

        await send_star_gift_raw(client, target_user.id, gift_id)

        await status_msg.edit(lang.get("gift.success", mention=mention))

    except Exception as e:
        await message.reply_text(lang.get("gift.fail", e=e))


@command(lambda ctx: filters.command("listgift") & filters.user(ctx.owner_id))
async def list_gift_handler(client, message):
    lang = message.texts
    status_msg = await message.reply_text(lang.get("gift.list_processing"))

    try:
        gifts = await client.get_available_gifts()

        if not gifts:
            return await status_msg.edit(lang.get("gift.list_empty"))

        for gift in gifts:
            if not gift.is_sold_out:
                price = gift.star_count
                emoji = "❓️"
                if hasattr(gift, "sticker") and hasattr(gift.sticker, "emoji"):
                    emoji = f"{gift.sticker.emoji} "

                caption = lang.get("gift.info_caption", id=gift.id, price=price, emoji=emoji)

                buttons = [
                    [{"text": lang.get("gift.btn_send"), "callback_data": f"gift_send_ask_{gift.id}"}],
                    [{"text": lang.get("gift.btn_claim"), "callback_data": f"gift_claim_self_{gift.id}"}],
                ]
                markup = client.ns.telegram.button.build_button_grid(buttons)

                if hasattr(gift, "sticker") and gift.sticker.thumbs:
                    thumb = gift.sticker.thumbs[-1]
                    file_path = None
                    try:
                        file_path = await client.download_media(thumb.file_id)
                        await client.send_photo(message.chat.id, photo=file_path, caption=caption, reply_markup=markup)
                    except Exception:
                        await client.send_message(message.chat.id, text=caption, reply_markup=markup)
                    finally:
                        if file_path and os.path.exists(file_path):
                            os.remove(file_path)
                else:
                    await client.send_message(message.chat.id, text=caption, reply_markup=markup)

                await asyncio.sleep(1.5)

            await status_msg.delete()

    except Exception as e:
        await status_msg.edit(lang.get("gift.fail", e=e))


@command(lambda ctx: filters.regex(r"^gift_claim_self_(\d+)"), handler_type="callback")
async def claim_self_gift_callback(client, callback_query):
    lang = callback_query.texts
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(lang.get("general.no_access"), show_alert=True)

    gift_id = int(callback_query.data.split("_")[3])
    user_id = callback_query.from_user.id

    try:
        await callback_query.edit_message_reply_markup(None)
        await send_star_gift_raw(client, user_id, gift_id)
        await callback_query.edit_message_caption(lang.get("gift.claim_self_success", id=gift_id))
    except Exception as e:
        await callback_query.answer(lang.get("gift.claim_fail", e=e), show_alert=True)


@command(lambda ctx: filters.regex(r"^gift_send_ask_(\d+)"), handler_type="callback")
async def ask_send_gift_callback(client, callback_query):
    lang = callback_query.texts
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(lang.get("general.no_access"), show_alert=True)

    gift_id = int(callback_query.data.split("_")[3])
    chat_id = callback_query.message.chat.id

    try:
        await callback_query.edit_message_reply_markup(None)

        prompt = f"{lang.get('gift.ask_target')}{lang.get('prompts.cancel_footer')}"
        ask_msg = await client.ask(chat_id, prompt, timeout=60)

        if ask_msg.text.lower() == "/batal":
            return await client.send_message(chat_id, lang.get("gift.cancel_text"))

        target_input = ask_msg.text
        processing_msg = await client.send_message(chat_id, lang.get("gift.finding_user", input=target_input))

        try:
            target_user = await client.get_users(target_input)
        except Exception:
            return await processing_msg.edit(lang.get("gift.user_not_found"))

        await processing_msg.edit(lang.get("gift.sending", id=gift_id, mention=target_user.first_name))

        await send_star_gift_raw(client, target_user.id, gift_id)

        await processing_msg.edit(lang.get("gift.success", mention=target_user.first_name))

    except asyncio.TimeoutError:
        await client.send_message(chat_id, lang.get("gift.timeout"))
    except Exception as e:
        await client.send_message(chat_id, lang.get("gift.fail", e=e))
