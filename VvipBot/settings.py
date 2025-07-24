from . import *


@command(lambda ctx: filters.regex("^settings$"), handler_type="callback")
async def settings(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(callback_query.lang.get("general.no_access"), show_alert=True)

    lang = callback_query.lang

    button_rows = [
        f"| {lang.get('settings.set_start_photo')} - set_start_photo | | {lang.get('settings.set_start_text')} - set_start_text;same |",
        f"| {lang.get('settings.add_vvip')} - setup_listvvip | | {lang.get('settings.del_vvip')} - delete_listvvip;same |",
        f"| {lang.get('settings.check_members')} - list_members_0 | | {lang.get('settings.check_active_members')} - check_active_menu_init;same |",
        f"| {lang.get('settings.api_keys')} - api_settings | | {lang.get('settings.broadcast')} - broadcast;same |",
        f"| {lang.get('settings.stats_button')} - stats_0 |",
        f"| {lang.get('general.back_to_main_menu')} - start |",
    ]
    btn_text = "\n".join(button_rows)

    txt_content = f"**{lang.get('settings.title')}**\n\n{lang.get('settings.description')}"
    btn, txt = client.ns.button.create_keyboard(f"{txt_content}\n\n{btn_text}")

    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


@command(lambda ctx: filters.regex("^set_start_photo$"), handler_type="callback")
async def set_start_photo_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    lang = callback_query.lang
    await callback_query.message.delete()

    back_btn_text = f"| {lang.get('general.back_to_settings')} - settings |"
    back_btn = client.ns.button.create_keyboard(back_btn_text)[0]

    try:
        prompt = f"{lang.get('settings.set_photo_prompt')}{lang.get('prompts.cancel_footer')}"
        ask_photo_msg = await client.ask(chat_id, prompt, timeout=300)

        if ask_photo_msg.text:
            if ask_photo_msg.text.lower() == "/batal":
                raise nsdev.UserCancelled
            if ask_photo_msg.text.lower() == "/empty":
                ctx.db.removeVars(client.me.id, "start_photo_id")
                return await client.send_message(chat_id, lang.get("settings.photo_emptied"), reply_markup=back_btn)

        if not ask_photo_msg.photo:
            return await client.send_message(chat_id, lang.get("settings.set_photo_fail"), reply_markup=back_btn)

        photo_id = ask_photo_msg.photo.sizes[-1].file_id
        ctx.db.setVars(client.me.id, "start_photo_id", photo_id)
        await client.send_message(chat_id, lang.get("settings.set_photo_success"), reply_markup=back_btn)

    except nsdev.UserCancelled:
        await client.send_message(chat_id, lang.get("general.cancelled"), reply_markup=back_btn)
    except asyncio.TimeoutError:
        await client.send_message(chat_id, lang.get("general.timeout"), reply_markup=back_btn)
    except Exception as e:
        await client.send_message(chat_id, lang.get("general.error", e=e), reply_markup=back_btn)


@command(lambda ctx: filters.regex("^set_start_text$"), handler_type="callback")
async def set_start_text_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    lang = callback_query.lang
    await callback_query.message.delete()

    back_btn_text = f"| {lang.get('general.back_to_settings')} - settings |"
    back_btn = client.ns.button.create_keyboard(back_btn_text)[0]

    try:
        prompt = f"{lang.get('settings.set_text_prompt')}{lang.get('prompts.cancel_footer')}"
        ask_text_msg = await client.ask(chat_id, prompt, timeout=600)

        if not ask_text_msg.text:
            return await client.send_message(chat_id, lang.get("settings.set_text_fail"), reply_markup=back_btn)

        if ask_text_msg.text.lower() == "/batal":
            raise nsdev.UserCancelled

        if ask_text_msg.text.lower() == "/empty":
            ctx.db.removeVars(client.me.id, "start_text_template")
            return await client.send_message(chat_id, lang.get("settings.text_emptied"), reply_markup=back_btn)

        ctx.db.setVars(client.me.id, "start_text_template", ask_text_msg.text)
        await client.send_message(chat_id, lang.get("settings.set_text_success"), reply_markup=back_btn)

    except nsdev.UserCancelled:
        await client.send_message(chat_id, lang.get("general.cancelled"), reply_markup=back_btn)
    except asyncio.TimeoutError:
        await client.send_message(chat_id, lang.get("general.timeout"), reply_markup=back_btn)
    except Exception as e:
        await client.send_message(chat_id, lang.get("general.error", e=e), reply_markup=back_btn)


@command(lambda ctx: filters.regex("^broadcast$"), handler_type="callback")
async def broadcast_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(callback_query.lang.get("general.no_access"), show_alert=True)

    chat_id = callback_query.message.chat.id
    lang = callback_query.lang

    try:
        await callback_query.message.delete()
        prompt = f"{lang.get('settings.broadcast_prompt')}{lang.get('prompts.cancel_footer')}"
        ask_message = await client.ask(chat_id, text=prompt, timeout=600)

        if ask_message.text and ask_message.text.lower() == "/batal":
            raise nsdev.UserCancelled

        user_ids = ctx.db.getListVars(client.me.id, "user_ids") or []
        if not user_ids:
            return await client.send_message(chat_id, lang.get("settings.broadcast_no_users"))

        progress_msg = await client.send_message(chat_id, lang.get("settings.broadcast_start", count=len(user_ids)))

        success_count, fail_count = 0, 0
        for user_id in user_ids:
            try:
                await ask_message.copy(chat_id=user_id)
                success_count += 1
            except pyrogram.errors.FloodWait as e:
                await asyncio.sleep(e.value + 1)
                await ask_message.copy(chat_id=user_id)
                success_count += 1
            except Exception:
                ctx.db.removeListVars(client.me.id, "user_ids", user_id)
                fail_count += 1
            await asyncio.sleep(0.1)

        await progress_msg.edit(lang.get("settings.broadcast_done", success=success_count, fail=fail_count))

    except nsdev.UserCancelled:
        await client.send_message(chat_id, lang.get("general.cancelled"))
    except asyncio.TimeoutError:
        await client.send_message(chat_id, lang.get("general.timeout"))
    except Exception as e:
        await client.send_message(chat_id, lang.get("general.error", e=e))


@command(lambda ctx: filters.regex("^setup_listvvip$"), handler_type="callback")
async def setup_listvvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    lang = callback_query.lang
    await callback_query.message.delete()

    try:

        def ask(text):
            return client.ask(chat_id, f"{text}{lang.get('prompts.cancel_footer')}", timeout=600)

        def validate(msg, check_func, err_msg_key):
            if msg.text and msg.text.lower() == "/batal":
                raise nsdev.UserCancelled
            if not check_func(msg.text):
                raise ValueError(lang.get(err_msg_key))
            return msg.text

        def is_digit(t):
            return t.isdigit()

        def is_chatid(t):
            return t.lstrip("-").isdigit()

        def is_link(t):
            return "https://" in t

        vvip_data = {}
        vvip_data["name"] = validate(await ask(lang.get("settings.setup_vvip.step1_name")), lambda t: True, "")
        vvip_data["price"] = int(
            validate(
                await ask(lang.get("settings.setup_vvip.step2_price")),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )
        vvip_data["group_link"] = validate(
            await ask(lang.get("settings.setup_vvip.step3_link")),
            is_link,
            "settings.setup_vvip.err_must_be_link",
        )
        vvip_data["chat_id_normal"] = int(
            validate(
                await ask(lang.get("settings.setup_vvip.step4_chat_id")),
                is_chatid,
                "settings.setup_vvip.err_must_be_chat_id",
            )
        )
        vvip_data["promo_price"] = int(
            validate(
                await ask(lang.get("settings.setup_vvip.step5_promo_price")),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )

        if vvip_data["promo_price"] > 0:
            vvip_data["promo_link"] = validate(
                await ask(lang.get("settings.setup_vvip.step6_promo_link")),
                is_link,
                "settings.setup_vvip.err_must_be_link",
            )
            vvip_data["chat_id_promo"] = int(
                validate(
                    await ask(lang.get("settings.setup_vvip.step7_promo_chat_id")),
                    is_chatid,
                    "settings.setup_vvip.err_must_be_chat_id",
                )
            )
            prompt_promo = f"{lang.get('settings.setup_vvip.step8_promo_text')}{lang.get('prompts.cancel_footer')}"
            promo_text_msg = await client.ask(chat_id, prompt_promo, timeout=600)
            if promo_text_msg.text and promo_text_msg.text.lower() == "/batal":
                raise nsdev.UserCancelled
            vvip_data["promo_text"] = "" if promo_text_msg.text.lower() == "/skip" else promo_text_msg.text
        else:
            (
                vvip_data["promo_link"],
                vvip_data["chat_id_promo"],
                vvip_data["promo_text"],
            ) = (
                "",
                0,
                "",
            )

        prompt_normal = f"{lang.get('settings.setup_vvip.step9_normal_text')}{lang.get('prompts.cancel_footer')}"
        normal_text_msg = await client.ask(chat_id, prompt_normal, timeout=600)
        if normal_text_msg.text and normal_text_msg.text.lower() == "/batal":
            raise nsdev.UserCancelled
        vvip_data["normal_text"] = "" if normal_text_msg.text.lower() == "/skip" else normal_text_msg.text

        ctx.db.setListVars(client.me.id, "list_vvip", vvip_data)
        await client.send_message(chat_id, lang.get("settings.setup_vvip.success", name=vvip_data["name"]))

    except nsdev.UserCancelled:
        await client.send_message(chat_id, lang.get("settings.setup_vvip.cancelled"))
    except (asyncio.TimeoutError, ValueError) as e:
        await client.send_message(chat_id, f"{lang.get('general.invalid_input_timeout')}\n`{e}`")
    except Exception as e:
        await client.send_message(chat_id, lang.get("general.error", e=e))


@command(lambda ctx: filters.regex("^delete_listvvip$"), handler_type="callback")
async def delete_listvvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []

    back_btn = f"| {lang.get('general.back_to_settings')} - settings |"

    if not vvip_list:
        btn, txt = client.ns.button.create_keyboard(f"{lang.get('settings.delete_vvip_empty')}\n\n{back_btn}")
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(txt, reply_markup=btn)
        return await callback_query.edit_message_text(txt, reply_markup=btn)

    btn_text = ""
    for i, item in enumerate(vvip_list):
        name = item.get("name", "Tanpa Nama")
        del_btn_text = lang.get("settings.delete_vvip_button", name=name)
        suffix = ";same" if i % 2 != 0 else ""
        btn_text += f"| {del_btn_text} - delete_vvip {name}{suffix} |\n"

    btn_text += back_btn
    title = lang.get("settings.delete_vvip_title")
    prompt = lang.get("settings.delete_vvip_prompt")

    btn, txt = client.ns.button.create_keyboard(f"**{title}**\n\n{prompt}\n\n{btn_text}")

    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^delete_vvip\s(.+)"), handler_type="callback")
async def confirm_delete_vvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    _, name = callback_query.data.split(" ", 1)

    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
    item_to_remove = next((item for item in vvip_list if item.get("name") == name), None)

    back_btn = f"| {lang.get('general.back_to_settings')} - delete_listvvip |"

    if item_to_remove:
        ctx.db.removeListVars(client.me.id, "list_vvip", item_to_remove)
        ctx.log.print(f"{ctx.log.ORANGE}Owner bot {client.me.id} menghapus VVIP: {name}")
        message = lang.get("settings.delete_vvip_success", name=name)
        btn, txt = client.ns.button.create_keyboard(f"{message}\n\n{back_btn}")
    else:
        message = lang.get("settings.delete_vvip_fail", name=name)
        btn, txt = client.ns.button.create_keyboard(f"{message}\n\n{back_btn}")

    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


@command(lambda ctx: filters.regex("^api_settings$"), handler_type="callback")
async def api_settings_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang

    active = lang.get("settings.api_status_active")
    inactive = lang.get("settings.api_status_inactive")

    violet_status = active if ctx.db.getVars(client.me.id, "VIOLET_API_KEY") else inactive
    gemini_status = active if ctx.db.getVars(client.me.id, "GEMINI_API_KEY") else inactive

    btn_text = (
        f"| {lang.get('settings.api_set_violet')} - set_api VIOLET |\n"
        f"| {lang.get('settings.api_set_gemini')} - set_api GEMINI_API_KEY;same |\n"
        f"| {lang.get('settings.api_del_all')} - del_api_confirm |\n"
        f"| {lang.get('general.back_to_settings')} - settings |"
    )

    text = (
        f"**{lang.get('settings.api_title', mention=client.me.mention)}**\n\n"
        f"{lang.get('settings.api_desc')}\n\n"
        f"**{lang.get('settings.api_status_title')}**\n"
        f"{lang.get('settings.api_status_violet', status=violet_status)}\n"
        f"{lang.get('settings.api_status_gemini', status=gemini_status)}\n\n"
        f"{lang.get('settings.api_prompt')}"
    )

    btn, txt = client.ns.button.create_keyboard(f"{text}\n{btn_text}")
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^set_api\s(.+)"), handler_type="callback")
async def set_api_key_prompt(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    lang = callback_query.lang
    _, key_name = callback_query.data.split(" ", 1)
    await callback_query.message.delete()

    back_btn_text = f"| {lang.get('general.back_to_settings_api')} - api_settings |"
    back_btn = client.ns.button.create_keyboard(back_btn_text)[0]

    try:

        def ask(p):
            return client.ask(chat_id, f"{p}{lang.get('prompts.cancel_footer')}")

        if key_name == "VIOLET":
            api_key_msg = await ask(lang.get("settings.api_set_violet_1"))
            if api_key_msg.text and api_key_msg.text.lower() == "/batal":
                raise nsdev.UserCancelled
            secret_key_msg = await ask(lang.get("settings.api_set_violet_2"))
            if secret_key_msg.text and secret_key_msg.text.lower() == "/batal":
                raise nsdev.UserCancelled

            ctx.db.setVars(client.me.id, "VIOLET_API_KEY", api_key_msg.text)
            ctx.db.setVars(client.me.id, "VIOLET_SECRET_KEY", secret_key_msg.text)
        else:
            prompt = lang.get("settings.api_set_gemini_prompt", key_name=key_name)
            key_value_msg = await ask(prompt)
            if key_value_msg.text and key_value_msg.text.lower() == "/batal":
                raise nsdev.UserCancelled
            ctx.db.setVars(client.me.id, key_name, key_value_msg.text)

        from services import initialize_bot_services

        initialize_bot_services(client, ctx.db)

        await client.send_message(
            chat_id,
            lang.get("settings.api_set_success", key_name=key_name),
            reply_markup=back_btn,
        )

    except nsdev.UserCancelled:
        await client.send_message(chat_id, lang.get("general.cancelled"), reply_markup=back_btn)
    except asyncio.TimeoutError:
        await client.send_message(chat_id, lang.get("general.timeout"), reply_markup=back_btn)
    except Exception as e:
        await client.send_message(chat_id, lang.get("general.error", e=e), reply_markup=back_btn)


@command(lambda ctx: filters.regex("^del_api_confirm$"), handler_type="callback")
async def confirm_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    btn, txt = client.ns.button.create_keyboard(
        f"**{lang.get('settings.api_del_confirm_title')}**\n{lang.get('settings.api_del_confirm_prompt')}\n\n"
        f"| {lang.get('settings.api_del_confirm_yes_button')} - do_del_api | | {lang.get('settings.api_del_confirm_no_button')} - api_settings |"
    )
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


@command(lambda ctx: filters.regex("^do_del_api$"), handler_type="callback")
async def do_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    ctx.db.removeVars(client.me.id, "VIOLET_API_KEY")
    ctx.db.removeVars(client.me.id, "VIOLET_SECRET_KEY")
    ctx.db.removeVars(client.me.id, "GEMINI_API_KEY")

    from services import initialize_bot_services

    initialize_bot_services(client, ctx.db)

    await callback_query.answer(lang.get("settings.api_del_success"), show_alert=True)
    await api_settings_callback(client, callback_query)
