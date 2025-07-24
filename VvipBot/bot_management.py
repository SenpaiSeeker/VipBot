from . import *


@command(lambda ctx: filters.regex("^create_bot$"), handler_type="callback")
async def create_bot_callback(client, callback_query):
    user_id = callback_query.from_user.id
    lang = callback_query.lang
    access_list = ctx.db.getListVars(ctx.owner_id, "create_bot_access") or []

    if user_id != ctx.owner_id and user_id not in access_list:
        owner_user = await client.get_users(ctx.owner_id)
        btn, txt = client.ns.button.create_keyboard(
            f"{lang.get('bot_management.create.no_access', mention=owner_user.mention)}\n\n| {lang.get('general.back')} - start |"
        )
        return await callback_query.edit_message_caption(txt, reply_markup=btn)

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    try:
        ask = lambda text: client.ask(chat_id, f"{text}", timeout=600)
        api_id_msg = await ask(lang.get("bot_management.create.step1_api_id"))
        if api_id_msg.text.lower() == "/batal":
            raise nsdev.UserCancelled
        api_id = api_id_msg.text

        api_hash_msg = await ask(lang.get("bot_management.create.step2_api_hash"))
        if api_hash_msg.text.lower() == "/batal":
            raise nsdev.UserCancelled
        api_hash = api_hash_msg.text

        token_msg = await ask(lang.get("bot_management.create.step3_bot_token"))
        if token_msg.text.lower() == "/batal":
            raise nsdev.UserCancelled
        token = token_msg.text

        msg = await client.send_message(
            chat_id, lang.get("bot_management.create.verifying")
        )
        new_bot_name = client.ns.arg.getNamebot(token)
        if "invalid" in new_bot_name.lower():
            raise ValueError(lang.get("bot_management.create.invalid_token"))

        new_bot_id = int(token.split(":", 1)[0])
        ctx.db.saveBot(new_bot_id, api_id, api_hash, token, is_token=True)
        expiry_date = datetime.now(timezone.utc) + timedelta(days=30)
        ctx.db.setVars(new_bot_id, "bot_expiration_date", expiry_date.isoformat())
        ctx.db.setVars(new_bot_id, "owner_id", user_id)

        if user_id != ctx.owner_id:
            ctx.db.removeListVars(ctx.owner_id, "create_bot_access", user_id)

        await msg.edit(lang.get("bot_management.create.saving", name=new_bot_name))
        bot_data = {
            "name": str(new_bot_id),
            "api_id": api_id,
            "api_hash": api_hash,
            "bot_token": token,
        }
        await ctx.manager.start_bot(bot_data)
        await msg.edit(lang.get("bot_management.create.success", name=new_bot_name))

    except nsdev.UserCancelled:
        await client.send_message(chat_id, lang.get("general.cancelled"))
    except asyncio.TimeoutError:
        await client.send_message(chat_id, lang.get("general.timeout"))
    except Exception as e:
        await client.send_message(chat_id, lang.get("bot_management.create.fail", e=e))


@command(lambda ctx: filters.regex(r"^list_my_bots(_\d+)?$"), handler_type="callback")
async def list_my_bots_callback(client, callback_query):
    user_id = callback_query.from_user.id
    lang = callback_query.lang
    my_bots = [
        b
        for b in ctx.db.getBots(is_token=True)
        if (ctx.db.getVars(int(b["name"]), "owner_id") or 0) == user_id
    ]
    if not my_bots:
        return await callback_query.answer(
            lang.get("bot_management.my_bots.empty"), show_alert=True
        )

    parts = callback_query.data.split("_")
    page = int(parts[-1]) if len(parts) > 2 and parts[-1].isdigit() else 0
    total_pages = len(my_bots)
    page = (page + total_pages) % total_pages
    bot_data = my_bots[page]
    bot_id = int(bot_data["name"])

    bot_name = f"ID {bot_id} ({lang.get('admin.allbots.offline')})"
    bot_username = None
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username
    except Exception:
        bot_name = f"ID {bot_id} ({lang.get('admin.allbots.error')})"

    exp_date_str = ctx.db.getVars(bot_id, "bot_expiration_date")
    days_left = (
        (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days
        if exp_date_str
        else "N/A"
    )

    text = f"**{lang.get('bot_management.my_bots.title', page=page + 1, total=total_pages)}**\n\n"
    text += f"• **{lang.get('admin.allbots.bot_name')}:** {bot_name}\n"
    text += f"• **{lang.get('admin.allbots.bot_id')}:** `{bot_id}`\n"
    text += f"• **{lang.get('admin.allbots.bot_username')}:** @{bot_username}\n"
    text += f"• **{lang.get('admin.allbots.expires_in')}:** `{days_left}` {lang.get('admin.allbots.days')}"

    btn_text = f"| {lang.get('bot_management.my_bots.manage_button', name=bot_name)} - manage_bot {bot_id} |\n"
    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages
        btn_text += f"| {lang.get('admin.allbots.prev_button')} - list_my_bots_{prev_page} | | {lang.get('admin.allbots.next_button')} - list_my_bots_{next_page};same |\n"

    btn_text += f"| {lang.get('general.back')} - start |"
    btn, _ = client.ns.button.create_keyboard(btn_text)
    await callback_query.edit_message_caption(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^manage_bot\s(\d+)"), handler_type="callback")
async def manage_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    lang = callback_query.lang
    owner_of_target_bot = ctx.db.getVars(bot_id_to_manage, "owner_id") or 0

    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await callback_query.answer(
            lang.get("general.not_your_bot"), show_alert=True
        )

    bot_name = f"ID {bot_id_to_manage}"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    exp_date_str = ctx.db.getVars(bot_id_to_manage, "bot_expiration_date")
    days_left_text = lang.get("bot_management.manage.not_set")
    if exp_date_str:
        days_left_text = f"{(datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days} {lang.get('admin.allbots.days')}"

    btn_text = (
        f"| {lang.get('bot_management.manage.extend_button')} - request_extend_duration {bot_id_to_manage} |\n"
        f"| {lang.get('bot_management.manage.delete_button')} - confirm_delete_bot {bot_id_to_manage} |\n"
        f"| {lang.get('general.back_to_bot_list')} - list_my_bots_0 |"
    )
    text = (
        f"**{lang.get('bot_management.manage.title', name=bot_name)}**\n\n"
        f"**{lang.get('admin.allbots.bot_id')}:** `{bot_id_to_manage}`\n"
        f"**{lang.get('bot_management.manage.expires_in')}:** `{days_left_text}`\n\n"
        f"{lang.get('bot_management.manage.prompt')}"
    )
    btn, txt = client.ns.button.create_keyboard(f"{text}\n\n{btn_text}")
    await callback_query.edit_message_caption(txt, reply_markup=btn)


@command(
    lambda ctx: filters.regex(r"^request_extend_duration\s(\d+)"),
    handler_type="callback",
)
async def request_extend_duration_callback(client, callback_query):
    bot_id_to_request = int(callback_query.data.split(" ", 1)[1])
    requester = callback_query.from_user
    lang = callback_query.lang
    bot_name = f"ID {bot_id_to_request}"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_request)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    try:
        main_bot_client = ctx.manager.main_bot_client
        if not main_bot_client or not main_bot_client.is_connected:
            raise ConnectionError("Bot utama tidak aktif.")

        txt_owner = (
            f"**{lang.get('bot_management.extend.request_title')}**\n\n"
            f"**{lang.get('general.user')}:** {main_bot_client.ns.arg.getMention(requester)} (`{requester.id}`)\n"
            f"**{lang.get('general.bot')}:** **{bot_name}** (`{bot_id_to_request}`)\n\n"
            f"{lang.get('bot_management.extend.request_prompt')}"
        )
        btn_owner_text = (
            f"| {lang.get('bot_management.extend.approve_button')} - approve_extension {bot_id_to_request} {requester.id} |\n"
            f"| {lang.get('bot_management.extend.reject_button')} - close_req {bot_id_to_request} {requester.id} |"
        )

        btn_owner, _ = main_bot_client.ns.button.create_keyboard(
            f"{txt_owner}\n{btn_owner_text}"
        )
        await main_bot_client.send_message(
            ctx.owner_id, txt_owner, reply_markup=btn_owner
        )
        await callback_query.answer(
            lang.get("bot_management.extend.sent_alert"), show_alert=True
        )

    except Exception as e:
        await callback_query.answer(
            lang.get("bot_management.extend.fail_alert", e=e), show_alert=True
        )


@command(
    lambda ctx: filters.regex(r"^approve_extension\s(\d+)\s(\d+)"),
    handler_type="callback",
)
async def owner_approve_extension_callback(client, callback_query):
    lang = callback_query.lang
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            lang.get("bot_management.extend.approve_denied"), show_alert=True
        )
    try:
        _, bot_id_str, requester_id_str = callback_query.data.split()
        bot_id_to_extend, requester_id, days_to_add = (
            int(bot_id_str),
            int(requester_id_str),
            30,
        )

        exp_date_str = ctx.db.getVars(bot_id_to_extend, "bot_expiration_date")
        current_exp_date = (
            datetime.fromisoformat(exp_date_str)
            if exp_date_str
            else datetime.now(timezone.utc)
        )
        new_exp_date = current_exp_date + timedelta(days=days_to_add)
        ctx.db.setVars(
            bot_id_to_extend, "bot_expiration_date", new_exp_date.isoformat()
        )

        await callback_query.edit_message_text(
            lang.get(
                "bot_management.extend.approve_success_log",
                bot_id=bot_id_to_extend,
                days=days_to_add,
            )
        )

        try:
            bot_instance = ctx.manager.running_bots.get(bot_id_to_extend)
            bot_name = (
                bot_instance.me.first_name
                if bot_instance and bot_instance.is_connected
                else f"ID {bot_id_to_extend}"
            )
            await client.send_message(
                requester_id,
                lang.get(
                    "bot_management.extend.approve_success_notif", bot_name=bot_name
                ),
            )
        except Exception as e:
            ctx.log.print(
                f"{ctx.log.YELLOW}Gagal kirim notif persetujuan ke {requester_id}: {e}"
            )

    except Exception as e:
        await callback_query.edit_message_text(
            lang.get("bot_management.extend.approve_fail", e=e)
        )


@command(
    lambda ctx: filters.regex(r"^close_req\s(\d+)\s(\d+)"), handler_type="callback"
)
async def owner_close_request_callback(client, callback_query):
    lang = callback_query.lang
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            lang.get("bot_management.extend.reject_denied"), show_alert=True
        )
    try:
        await callback_query.edit_message_text(
            lang.get("bot_management.extend.rejected_log")
        )
    except Exception:
        pass


@command(
    lambda ctx: filters.regex(r"^confirm_delete_bot\s(\d+)"), handler_type="callback"
)
async def confirm_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    lang = callback_query.lang
    bot_name = f"ID {bot_id_to_manage}"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    text = lang.get(
        "bot_management.delete.confirm_prompt", name=bot_name, id=bot_id_to_manage
    )
    btn_text = (
        f"| {lang.get('bot_management.delete.confirm_yes')} - do_delete_bot {bot_id_to_manage} |\n"
        f"| {lang.get('bot_management.delete.confirm_no')} - manage_bot {bot_id_to_manage} |"
    )
    btn, txt = client.ns.button.create_keyboard(
        f"**{lang.get('general.confirm_title')}**\n\n{text}\n\n{btn_text}"
    )
    await callback_query.edit_message_caption(txt, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^do_delete_bot\s(\d+)"), handler_type="callback")
async def do_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    lang = callback_query.lang
    owner_of_target_bot = ctx.db.getVars(bot_id_to_manage, "owner_id") or 0

    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await callback_query.answer(
            lang.get("bot_management.delete.no_permission"), show_alert=True
        )

    await callback_query.edit_message_caption(
        lang.get("bot_management.delete.processing", bot_id=bot_id_to_manage)
    )

    try:
        await ctx.manager.stop_bot(bot_id_to_manage)
        ctx.db.removeBot(bot_id_to_manage)
        ctx.db.removeAllVars(bot_id_to_manage)
        ctx.log.print(
            f"{ctx.log.ORANGE}Bot {bot_id_to_manage} telah dihapus oleh owner-nya ({user_id})."
        )

        btn_text = f"| {lang.get('general.back_to_bot_list')} - list_my_bots_0 |"
        await callback_query.edit_message_caption(
            lang.get("bot_management.delete.success", id=bot_id_to_manage),
            reply_markup=client.ns.button.create_keyboard(btn_text)[0],
        )
    except Exception as e:
        await callback_query.edit_message_caption(
            lang.get("bot_management.delete.fail", e=e)
        )
