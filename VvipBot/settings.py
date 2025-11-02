from . import *


@command(lambda ctx: filters.regex("^settings$"), handler_type="callback")
async def settings(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(callback_query.lang.get("general.no_access"), show_alert=True)

    lang = callback_query.lang

    layout = [
        [
            {"text": lang.get("settings.set_start_photo"), "callback_data": "set_start_photo"},
            {"text": lang.get("settings.set_start_text"), "callback_data": "set_start_text"},
        ],
        [
            {"text": lang.get("settings.add_vvip"), "callback_data": "setup_listvvip"},
            {"text": lang.get("settings.del_vvip"), "callback_data": "delete_listvvip"},
        ],
        [
            {"text": lang.get("settings.list_all_users"), "callback_data": "list_all_users_0"},
            {"text": lang.get("settings.check_members"), "callback_data": "list_members_0"},
        ],
        [
            {"text": lang.get("settings.check_active_members"), "callback_data": "check_active_menu_init"},
            {"text": lang.get("settings.broadcast"), "callback_data": "broadcast"},
        ],
        [
            {"text": lang.get("settings.api_keys"), "callback_data": "api_settings"},
            {"text": lang.get("settings.coupons"), "callback_data": "manage_coupons"},
        ],
        [
            {"text": lang.get("settings.stats_button"), "callback_data": "stats_0"},
            {"text": lang.get("general.back_to_main_menu"), "callback_data": "start"},
        ],
    ]

    txt_content = lang.get("settings.panel")
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt_content, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt_content, reply_markup=btn)


@command(lambda ctx: filters.regex("^set_start_photo$"), handler_type="callback")
async def set_start_photo_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    lang = callback_query.lang
    await callback_query.message.delete()

    layout = [[{"text": lang.get("general.back_to_settings"), "callback_data": "settings"}]]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        prompt = f"{lang.get('settings.set_photo_prompt')}{lang.get('prompts.cancel_footer')}"
        ask_photo_msg = await client.ask(chat_id, prompt, timeout=300)

        if ask_photo_msg.text:
            if ask_photo_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if ask_photo_msg.text.lower() == "/empty":
                await ctx.db.removeVars(client.me.id, "start_photo_id")
                return await client.send_message(chat_id, lang.get("settings.photo_emptied"), reply_markup=back_btn)

        if not ask_photo_msg.photo:
            return await client.send_message(chat_id, lang.get("settings.set_photo_fail"), reply_markup=back_btn)

        photo_id = ask_photo_msg.photo.sizes[-1].file_id
        await ctx.db.setVars(client.me.id, "start_photo_id", photo_id)
        await client.send_message(chat_id, lang.get("settings.set_photo_success"), reply_markup=back_btn)

    except listen.UserCancelled:
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

    layout = [[{"text": lang.get("general.back_to_settings"), "callback_data": "settings"}]]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        prompt = f"{lang.get('settings.set_text_prompt')}{lang.get('prompts.cancel_footer')}"
        ask_text_msg = await client.ask(chat_id, prompt, timeout=600)

        if not ask_text_msg.text:
            return await client.send_message(chat_id, lang.get("settings.set_text_fail"), reply_markup=back_btn)

        if ask_text_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        if ask_text_msg.text.lower() == "/empty":
            await ctx.db.removeVars(client.me.id, "start_text_template")
            return await client.send_message(chat_id, lang.get("settings.text_emptied"), reply_markup=back_btn)

        await ctx.db.setVars(client.me.id, "start_text_template", ask_text_msg.text.html)
        await client.send_message(chat_id, lang.get("settings.set_text_success"), reply_markup=back_btn)

    except listen.UserCancelled:
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
            raise listen.UserCancelled

        user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
        if not user_ids:
            return await client.send_message(chat_id, lang.get("settings.broadcast_no_users"))

        progress_msg = await client.send_message(chat_id, lang.get("settings.broadcast_start", count=len(user_ids)))

        success_count, fail_count = 0, 0

        text_to_parse = ask_message.text or ask_message.caption or ""
        reply_markup, cleaned_text = client.ns.telegram.button.create_inline_keyboard(text_to_parse)

        async def send_to_user(target_user_id):
            if reply_markup and reply_markup.inline_keyboard:
                if ask_message.media:
                    await ask_message.copy(chat_id=target_user_id, reply_markup=reply_markup)
                else:
                    await client.send_message(chat_id=target_user_id, text=cleaned_text, reply_markup=reply_markup)
            else:
                await ask_message.copy(chat_id=target_user_id)

        for user_id in user_ids:
            try:
                await send_to_user(user_id)
                success_count += 1
            except pyrogram.errors.FloodWait as e:
                await asyncio.sleep(e.value + 1)
                await send_to_user(user_id)
                success_count += 1
            except Exception:
                await ctx.db.removeListVars(client.me.id, "user_ids", user_id)
                fail_count += 1
            await asyncio.sleep(0.1)

        await progress_msg.edit(lang.get("settings.broadcast_done", success=success_count, fail=fail_count))

    except listen.UserCancelled:
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
                raise listen.UserCancelled
            if not check_func(msg.text):
                raise ValueError(lang.get(err_msg_key))
            return msg.text

        def is_digit(t):
            return t.isdigit()

        def is_chatid(t):
            return t.lstrip("-").isdigit()

        vvip_data = {}
        vvip_data["name"] = validate(await ask(lang.get("settings.setup_vvip.step1_name")), lambda t: True, "")
        vvip_data["price"] = int(
            validate(
                await ask(lang.get("settings.setup_vvip.step2_price")),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )
        vvip_data["duration"] = int(
            validate(
                await ask(lang.get("settings.setup_vvip.step3_duration")),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
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
            vvip_data["chat_id_promo"] = int(
                validate(
                    await ask(lang.get("settings.setup_vvip.step6_promo_chat_id")),
                    is_chatid,
                    "settings.setup_vvip.err_must_be_chat_id",
                )
            )
            prompt_promo = f"{lang.get('settings.setup_vvip.step7_promo_text')}{lang.get('prompts.skip_footer')}{lang.get('prompts.cancel_footer')}"
            promo_text_msg = await client.ask(chat_id, prompt_promo, timeout=600)
            if promo_text_msg.text and promo_text_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            vvip_data["promo_text"] = "" if promo_text_msg.text.lower() == "/skip" else promo_text_msg.text
        else:
            vvip_data["chat_id_promo"], vvip_data["promo_text"] = 0, ""

        prompt_normal = f"{lang.get('settings.setup_vvip.step8_normal_text')}{lang.get('prompts.skip_footer')}{lang.get('prompts.cancel_footer')}"
        normal_text_msg = await client.ask(chat_id, prompt_normal, timeout=600)
        if normal_text_msg.text and normal_text_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        vvip_data["normal_text"] = "" if normal_text_msg.text.lower() == "/skip" else normal_text_msg.text

        await ctx.db.setListVars(client.me.id, "list_vvip", vvip_data)
        await client.send_message(chat_id, lang.get("settings.setup_vvip.success", name=vvip_data["name"]))

    except listen.UserCancelled:
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
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

    back_row = [{"text": lang.get("general.back_to_settings"), "callback_data": "settings"}]

    if not vvip_list:
        text = lang.get("settings.delete_vvip_empty")
        btn = client.ns.telegram.button.build_button_grid([back_row])
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)

    layout = []
    button_row = []
    for item in vvip_list:
        name = item.get("name", "Tanpa Nama")
        button_row.append(
            {"text": lang.get("settings.delete_vvip_button", name=name), "callback_data": f"delete_vvip {name}"}
        )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []
    if button_row:
        layout.append(button_row)

    layout.append(back_row)
    text = lang.get("settings.delete_vvip_panel")
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^delete_vvip\s(.+)"), handler_type="callback")
async def confirm_delete_vvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    _, name = callback_query.data.split(" ", 1)

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    item_to_remove = next((item for item in vvip_list if item.get("name") == name), None)

    back_row = [{"text": lang.get("general.back_to_settings"), "callback_data": "delete_listvvip"}]

    if item_to_remove:
        await ctx.db.removeListVars(client.me.id, "list_vvip", item_to_remove)
        ctx.log.print(f"{ctx.log.ORANGE}Owner bot {client.me.id} menghapus VVIP: {name}")
        message = lang.get("settings.delete_vvip_success", name=name)
    else:
        message = lang.get("settings.delete_vvip_fail", name=name)

    btn = client.ns.telegram.button.build_button_grid([back_row])

    if callback_query.message.photo:
        await callback_query.edit_message_caption(message, reply_markup=btn)
    else:
        await callback_query.edit_message_text(message, reply_markup=btn)


@command(lambda ctx: filters.regex("^api_settings$"), handler_type="callback")
async def api_settings_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang

    saweria_username = await ctx.db.getVars(client.me.id, "SAWERIA_USERNAME")
    if saweria_username:
        saweria_status = lang.get("settings.api_status_saweria_active", username=saweria_username)
    else:
        saweria_status = lang.get("settings.api_status_inactive")

    gemini_status = (
        lang.get("settings.api_status_active")
        if await ctx.db.getVars(client.me.id, "GEMINI_API_KEY")
        else lang.get("settings.api_status_inactive")
    )

    layout = [
        [
            {"text": lang.get("settings.api_set_saweria"), "callback_data": "set_api SAWERIA"},
            {"text": lang.get("settings.api_set_gemini"), "callback_data": "set_api GEMINI_API_KEY"},
        ],
        [{"text": lang.get("settings.api_del_all"), "callback_data": "del_api_confirm"}],
        [{"text": lang.get("general.back_to_settings"), "callback_data": "settings"}],
    ]

    text = lang.get(
        "settings.api_panel", mention=client.me.mention, saweria_status=saweria_status, gemini_status=gemini_status
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^set_api\s(.+)"), handler_type="callback")
async def set_api_key_prompt(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    lang = callback_query.lang
    _, key_name = callback_query.data.split(" ", 1)
    await callback_query.message.delete()

    layout = [[{"text": lang.get("general.back_to_settings_api"), "callback_data": "api_settings"}]]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:

        def ask(p):
            return client.ask(chat_id, f"{p}{lang.get('prompts.cancel_footer')}", timeout=600)

        if key_name == "SAWERIA":
            api_key_msg = await ask(lang.get("settings.api_set_saweria_1"))
            if api_key_msg.text and api_key_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            username_msg = await ask(lang.get("settings.api_set_saweria_2"))
            if username_msg.text and username_msg.text.lower() == "/batal":
                raise listen.UserCancelled

            processing_msg = await client.send_message(chat_id, lang.get("general.processing"))
            try:
                saweria_temp = client.ns.payment.Saweria(api_key=api_key_msg.text)
                user_data = await saweria_temp.get_user_id(username=username_msg.text)

                if user_data.status != "Success":
                    raise Exception(user_data.result.msg if hasattr(user_data, "result") else "Unknown Error")

                saweria_user_id = user_data.result.userId

                await ctx.db.setVars(client.me.id, "SAWERIA_API_KEY", api_key_msg.text)
                await ctx.db.setVars(client.me.id, "SAWERIA_USERNAME", username_msg.text)
                await ctx.db.setVars(client.me.id, "SAWERIA_USER_ID", saweria_user_id)
                await processing_msg.delete()
                await client.send_message(chat_id, lang.get("settings.api_set_success_saweria"), reply_markup=back_btn)
                key_name = "Saweria"

            except Exception as e:
                await processing_msg.edit_text(lang.get("settings.api_set_fail_saweria", e=e), reply_markup=back_btn)
                return
        else:
            prompt = lang.get("settings.api_set_gemini_prompt", key_name=key_name)
            key_value_msg = await ask(prompt)
            if key_value_msg.text and key_value_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            await ctx.db.setVars(client.me.id, key_name, key_value_msg.text)
            await client.send_message(
                chat_id, lang.get("settings.api_set_success", key_name=key_name), reply_markup=back_btn
            )

        from services import initialize_bot_services

        await initialize_bot_services(client, ctx.db)

    except listen.UserCancelled:
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

    text = lang.get("settings.api_del_confirm_panel")
    layout = [
        [
            {"text": lang.get("settings.api_del_confirm_yes_button"), "callback_data": "do_del_api"},
            {"text": lang.get("settings.api_del_confirm_no_button"), "callback_data": "api_settings"},
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^do_del_api$"), handler_type="callback")
async def do_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    await ctx.db.removeVars(client.me.id, "SAWERIA_API_KEY")
    await ctx.db.removeVars(client.me.id, "SAWERIA_USERNAME")
    await ctx.db.removeVars(client.me.id, "SAWERIA_USER_ID")
    await ctx.db.removeVars(client.me.id, "GEMINI_API_KEY")

    from services import initialize_bot_services

    initialize_bot_services(client, ctx.db)

    await callback_query.answer(lang.get("settings.api_del_success"), show_alert=True)
    await api_settings_callback(client, callback_query)


@command(lambda ctx: filters.regex(r"^manage_coupons"), handler_type="callback")
async def manage_coupons_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    lang = callback_query.lang
    text = lang.get("coupons.panel")
    layout = [
        [{"text": lang.get("coupons.add_button"), "callback_data": "add_coupon"}],
        [{"text": lang.get("coupons.list_button"), "callback_data": "list_coupons_0"}],
        [{"text": lang.get("general.back_to_settings"), "callback_data": "settings"}],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^add_coupon"), handler_type="callback")
async def add_coupon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    try:

        def ask(text):
            return client.ask(chat_id, f"{text}{lang.get('prompts.cancel_footer')}", timeout=600)

        code = (await ask(lang.get("coupons.ask_code"))).text.upper()
        type_msg = await ask(lang.get("coupons.ask_type"))
        discount_type = "percentage" if "1" in type_msg.text else "fixed"

        value_prompt = (
            lang.get("coupons.ask_value_percent")
            if discount_type == "percentage"
            else lang.get("coupons.ask_value_fixed")
        )
        discount_value = int((await ask(value_prompt)).text)

        uses_left = int((await ask(lang.get("coupons.ask_uses"))).text)

        expiry_days_msg = await ask(lang.get("coupons.ask_expiry"))
        expiry_days = int(expiry_days_msg.text)
        expiry_date = (
            (datetime.now(timezone.utc) + timedelta(days=expiry_days)).isoformat() if expiry_days > 0 else None
        )

        coupon_data = {
            "code": code,
            "discount_type": discount_type,
            "discount_value": discount_value,
            "uses_left": uses_left,
            "expiry_date": expiry_date,
        }

        await ctx.db.setListVars(client.me.id, "coupons", coupon_data)
        await client.send_message(chat_id, lang.get("coupons.add_success", code=code))

    except (listen.UserCancelled, asyncio.TimeoutError, ValueError) as e:
        await client.send_message(chat_id, lang.get("general.cancelled"))
    except Exception as e:
        await client.send_message(chat_id, lang.get("general.error", e=e))


@command(lambda ctx: filters.regex(r"^list_coupons_(\d+)"), handler_type="callback")
async def list_coupons_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    page = int(callback_query.data.split("_")[2])

    coupons = await ctx.db.getListVars(client.me.id, "coupons") or []

    back_row = [{"text": lang.get("general.back"), "callback_data": "manage_coupons"}]

    if not coupons:
        text = lang.get("coupons.list_empty")
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await callback_query.edit_message_caption(text, reply_markup=btn)

    total_pages = len(coupons)
    page = max(0, min(page, total_pages - 1))
    coupon = coupons[page]

    expiry_text = "Permanent"
    if coupon.get("expiry_date"):
        expiry_text = datetime.fromisoformat(coupon["expiry_date"]).strftime("%d %b %Y")

    text = lang.get(
        "coupons.list_panel",
        page=page + 1,
        total=total_pages,
        code=coupon["code"],
        type=coupon["discount_type"],
        value=coupon["discount_value"],
        uses=coupon["uses_left"],
        expiry=expiry_text,
    )

    layout = []
    pagination_row = []
    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages if page + 1 < total_pages else page
        pagination_row.extend(
            [
                {"text": "«", "callback_data": f"list_coupons_{prev_page}"},
                {"text": "»", "callback_data": f"list_coupons_{next_page}"},
            ]
        )

    layout.append(
        [{"text": lang.get("coupons.delete_button"), "callback_data": f"delete_coupon {coupon['code']} {page}"}]
    )
    if pagination_row:
        layout.append(pagination_row)
    layout.append(back_row)

    btn = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_caption(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^delete_coupon\s(.+)\s(\d+)"), handler_type="callback")
async def delete_coupon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    _, code, page_str = callback_query.data.split()

    coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
    coupon_to_remove = next((c for c in coupons if c.get("code") == code), None)

    if coupon_to_remove:
        await ctx.db.removeListVars(client.me.id, "coupons", coupon_to_remove)
        await callback_query.answer(lang.get("coupons.delete_success"), show_alert=True)

    new_page = int(page_str)
    remaining_coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
    if new_page >= len(remaining_coupons) and len(remaining_coupons) > 0:
        new_page = len(remaining_coupons) - 1

    callback_query.data = f"list_coupons_{new_page}"
    await list_coupons_callback(client, callback_query)
