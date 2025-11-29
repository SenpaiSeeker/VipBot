from . import *


async def get_start_keyboard_and_content(client, user, lang):
    is_owner = await is_bot_owner(client, user.id)
    is_main_bot = client.me.id == ctx.manager.main_bot_id

    main_text_template = await ctx.db.getVars(client.me.id, "start_text_template")
    photo_id = await ctx.db.getVars(client.me.id, "start_photo_id") or "https://files.catbox.moe/ozzvtz.jpg"

    if not main_text_template:
        key = "start.welcome_main_bot" if is_main_bot else "start.welcome_clone_bot"
        main_text_template = lang.get(key)

    welcome_text = main_text_template.format(mention=client.ns.telegram.arg.getMention(user))

    layout = []

    if is_main_bot:
        layout.append(
            [
                {"text": lang.get("start.create_bot"), "callback_data": "create_bot"},
                {"text": lang.get("start.my_bots"), "callback_data": "list_my_bots_0"},
            ]
        )
    if is_owner:
        layout.append([{"text": lang.get("start.settings_panel"), "callback_data": "settings"}])

    layout.extend(
        [
            [
                {"text": lang.get("start.list_vvip"), "callback_data": "list_vvip"},
                {"text": lang.get("start.donate"), "callback_data": "donate_stars"},
            ],
            [
                {"text": lang.get("start.about_bot"), "callback_data": "about_bot"},
                {"text": lang.get("start.ai_feature"), "callback_data": "gemini_ai"},
            ],
            [{"text": lang.get("start.language"), "callback_data": "set_lang"}],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)
    return btn, welcome_text, photo_id


@command(lambda ctx: filters.command("start") & filters.private)
async def start_bot(client, message):
    await check_new_user(client, message)
    btn, txt, photo_id = await get_start_keyboard_and_content(client, message.from_user, message.lang)
    await message.reply_photo(photo=photo_id, caption=txt, reply_markup=btn)


@command(lambda ctx: filters.regex("^start$"), handler_type="callback")
async def start_callback(client, callback_query):
    btn, txt, photo_id = await get_start_keyboard_and_content(client, callback_query.from_user, callback_query.lang)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.message.delete()
        await client.send_photo(
            callback_query.from_user.id,
            photo=photo_id,
            caption=txt,
            reply_markup=btn,
        )


@command(lambda ctx: filters.regex("^about_bot$"), handler_type="callback")
async def about_bot_callback(client, callback_query):
    lang = callback_query.lang
    text = lang.get("about.panel")
    layout = [[{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}]]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^set_lang$"), handler_type="callback")
async def set_lang_callback(client, callback_query):
    lang = callback_query.lang
    text = lang.get("lang.select")

    layout = [
        [
            {"text": lang.get("lang.button_id"), "callback_data": "chg_lang_id"},
            {"text": lang.get("lang.button_en"), "callback_data": "chg_lang_en"},
        ],
        [{"text": lang.get("lang.button_ja"), "callback_data": "chg_lang_ja"}],
        [{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^chg_lang_(id|en|ja)$"), handler_type="callback")
async def change_lang_callback(client, callback_query):
    lang_code = callback_query.data.split("_")[-1]
    await ctx.db.setVars(callback_query.from_user.id, "language", lang_code, var_key="user_info")
    lang = ctx.L(ctx.db, callback_query.from_user.id, lang_code)
    await callback_query.answer(lang.get("lang.selected"), show_alert=True)
    callback_query.lang = lang
    await start_callback(client, callback_query)


@command(lambda ctx: filters.regex("^close_panel$"), handler_type="callback")
async def close_panel_callback(client, callback_query):
    try:
        await callback_query.message.delete()
    except Exception:
        await callback_query.answer("Done.")


@command(lambda ctx: filters.regex("^list_vvip$"), handler_type="callback")
async def list_vvip_bot(client, callback_query):
    lang = callback_query.lang
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

    layout = []

    if not vvip_list:
        text = lang.get("vvip_list.empty")
        layout.append([{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}])
        btn = client.ns.telegram.button.build_button_grid(layout)
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)

    for index, item in enumerate(vvip_list):
        name = item.get("name", "N/A")
        promo_price = item.get("promo_price", 0)

        button_row = [{"text": lang.get("vvip_list.button_package", name=name), "callback_data": f"notes_{index}"}]

        if promo_price > 0:
            button_row.append(
                {"text": lang.get("vvip_list.button_promo", name=name), "callback_data": f"promo_detail_{index}"}
            )

        layout.append(button_row)

    layout.append([{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}])

    btn = client.ns.telegram.button.build_button_grid(layout)
    text = lang.get("vvip_list.panel", mention=client.me.mention)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^(gemini_ai|khodam|chatbot)"), handler_type="callback")
async def gemini_bot_ai(client, callback_query):
    lang = callback_query.lang
    gemini_service = getattr(client, "services", None) and client.services.gemini

    if not gemini_service:
        if await is_bot_owner(client, callback_query.from_user.id):
            text = lang.get("ai.disabled")
            layout = [
                [
                    {"text": lang.get("ai.setup_button"), "callback_data": "api_settings"},
                    {"text": lang.get("general.back_to_main_menu"), "callback_data": "start"},
                ]
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            if callback_query.message.photo:
                return await callback_query.edit_message_caption(text, reply_markup=btn)
            return await callback_query.edit_message_text(text, reply_markup=btn)
        return await callback_query.answer(lang.get("ai.unavailable"), show_alert=True)

    data = callback_query.data.split()
    chat_id = callback_query.from_user.id

    if data[0] == "gemini_ai":
        text = lang.get("ai.panel")
        layout = [
            [
                {"text": lang.get("ai.khodam_button"), "callback_data": "khodam"},
                {"text": lang.get("ai.chatbot_button"), "callback_data": "chatbot"},
            ],
            [{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}],
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        if callback_query.message.photo:
            await callback_query.edit_message_caption(text, reply_markup=btn)
        else:
            await callback_query.edit_message_text(text, reply_markup=btn)

    elif data[0] in ("khodam", "chatbot"):
        await callback_query.edit_message_reply_markup(None)
        mode = data[0]
        try:
            if mode == "khodam":
                prompt = f"{lang.get('ai.khodam_prompt')}{lang.get('prompts.cancel_footer')}"
                ask_msg = await client.ask(chat_id, prompt, timeout=300)
                if ask_msg.text.lower() == "/batal":
                    raise listen.UserCancelled

                msg = await client.send_message(chat_id, lang.get("ai.khodam_analyzing", name=ask_msg.text))
                response_text = await gemini_service.send_khodam_message(ask_msg.text, chat_id)

                layout = [
                    [
                        {"text": lang.get("ai.khodam_try_again_button"), "callback_data": "khodam"},
                        {"text": lang.get("ai.back_to_ai_menu_button"), "callback_data": "gemini_ai"},
                    ]
                ]
                btn = client.ns.telegram.button.build_button_grid(layout)
                await msg.edit(
                    lang.get("ai.khodam_result_title", name=ask_msg.text, result=response_text), reply_markup=btn
                )

            elif mode == "chatbot":
                vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
                vvip_info_text = ""
                if vvip_list:
                    vvip_info_text = "\n".join(
                        [f"- {item.get('name', 'N/A')}: IDR {item.get('price', 0):,}" for item in vvip_list]
                    )
                else:
                    vvip_info_text = "No VVIP packages available."

                about_bot_text = lang.get("about.description")

                system_instruction = lang.get(
                    "ai.chatbot_system_instruction",
                    bot_name=client.me.first_name,
                    about_bot=about_bot_text,
                    vvip_info=vvip_info_text,
                )
                gemini_service.set_chatbot_instruction(system_instruction)

                await client.send_message(chat_id, lang.get("ai.chatbot_intro", bot_name=client.me.first_name))

                while True:
                    user_msg = await client.listen(chat_id, timeout=600)
                    if not user_msg.text:
                        continue
                    if user_msg.text.lower() == "/stop":
                        raise listen.UserCancelled

                    await client.send_chat_action(chat_id, pyrogram.enums.ChatAction.TYPING)
                    response_text = await gemini_service.send_chat_message(
                        user_msg.text, user_id=chat_id, bot_name=client.me.first_name
                    )
                    await client.send_message(chat_id, response_text)

        except listen.UserCancelled:
            layout = [[{"text": lang.get("ai.back_to_ai_menu_button"), "callback_data": "gemini_ai"}]]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(chat_id, lang.get("ai.session_stopped"), reply_markup=btn)
        except asyncio.TimeoutError:
            layout = [[{"text": lang.get("ai.back_to_ai_menu_button"), "callback_data": "gemini_ai"}]]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(chat_id, lang.get("ai.session_expired"), reply_markup=btn)
        except Exception as e:
            ctx.log.print(f"{ctx.log.RED}Error on AI Chatbot session: {e}")
            await client.send_message(chat_id, lang.get("ai.error", e=e))
        finally:
            gemini_service.reset_chatbot_instruction()


@command(lambda ctx: filters.regex("^donate_stars$"), handler_type="callback")
async def donate_callback(client, callback_query):
    lang = callback_query.lang
    photo_url = "https://files.catbox.moe/1f9j10.jpg"
    text = lang.get("donation.panel")
    layout = [
        [{"text": "25 ⭐", "callback_data": "donate_pay_26"}, {"text": "50 ⭐", "callback_data": "donate_pay_50"}],
        [{"text": "75 ⭐", "callback_data": "donate_pay_75"}, {"text": "100 ⭐", "callback_data": "donate_pay_100"}],
        [{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        if callback_query.message.photo:
            await callback_query.edit_message_caption(caption=text, reply_markup=btn)
        else:
            await callback_query.message.delete()
            await client.send_photo(callback_query.from_user.id, photo=photo_url, caption=text, reply_markup=btn)
    except Exception:
        await callback_query.message.delete()
        await client.send_photo(callback_query.from_user.id, photo=photo_url, caption=text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^donate_pay_(\d+)$"), handler_type="callback")
async def process_donation_callback(client, callback_query):
    lang = callback_query.lang
    try:
        star_amount = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        return await callback_query.answer(lang.get("payment.donation.invalid_amount"), show_alert=True)

    await callback_query.answer(lang.get("payment.donation.preparing"))

    invoice = {
        "title": lang.get("payment.donation.invoice_title"),
        "description": lang.get("payment.donation.invoice_desc", stars=star_amount),
        "payload": f"donation_{star_amount}_{callback_query.from_user.id}_{int(time())}",
        "currency": "XTR",
        "prices": [pyrogram.types.LabeledPrice(f"Donasi {star_amount} Stars", star_amount)],
    }

    try:
        await client.send_invoice(callback_query.from_user.id, **invoice)
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal mengirim invoice Stars: {e}")
        await callback_query.answer(lang.get("payment.donation.invoice_fail"), show_alert=True)
