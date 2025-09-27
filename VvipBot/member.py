from . import *


async def _send_my_access_panel(client, update):
    lang = update.lang
    user_id = update.from_user.id
    all_members = ctx.db.getListVars(client.me.id, "vvip_members") or []
    user_memberships = [m for m in all_members if m.get("user_id") == user_id]

    back_btn_text = f"| {lang.get('general.back_to_main_menu')} - start |"

    if not user_memberships:
        text = lang.get("member_portal.no_access")
        btn, final_text = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{back_btn_text}")
    else:
        text = lang.get("member_portal.panel_title")
        btn_list = []
        
        for membership in user_memberships:
            name = membership.get("vvip_name", "N/A")
            join_date_obj = datetime.fromisoformat(membership.get("join_date"))
            join_date_str = join_date_obj.strftime("%d %b %Y")
            
            expiry_date_str = lang.get("member_portal.permanent")
            expiry_date_obj_str = membership.get("expiry_date")
            if expiry_date_obj_str:
                expiry_date_obj = datetime.fromisoformat(expiry_date_obj_str)
                expiry_date_str = expiry_date_obj.strftime("%d %b %Y")

            text += lang.get("member_portal.membership_entry",
                             name=name,
                             join_date=join_date_str,
                             expiry_date=expiry_date_str)
            
            btn_list.append(f"| {lang.get('member_portal.resend_link_button', name=name)} - resend_link {name} |")

        btn_list.append(back_btn_text)
        btn, final_text = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n" + "\n".join(btn_list))

    if isinstance(update, pyrogram.types.Message):
        await update.reply_text(final_text, reply_markup=btn)
    elif isinstance(update, pyrogram.types.CallbackQuery):
        if update.message.photo:
            await update.edit_message_caption(final_text, reply_markup=btn)
        else:
            await update.edit_message_text(final_text, reply_markup=btn)


@command(lambda ctx: filters.command("myaccess") & filters.private)
async def my_access_command(client, message):
    await _send_my_access_panel(client, message)


@command(lambda ctx: filters.regex("^my_access$"), handler_type="callback")
async def my_access_callback(client, callback_query):
    await _send_my_access_panel(client, callback_query)


@command(lambda ctx: filters.regex(r"^resend_link\s(.+)"), handler_type="callback")
async def resend_link_callback(client, callback_query):
    lang = callback_query.lang
    user_id = callback_query.from_user.id
    vvip_name = callback_query.data.split(" ", 1)[1]

    all_members = ctx.db.getListVars(client.me.id, "vvip_members") or []
    membership = next((m for m in all_members if m.get("user_id") == user_id and m.get("vvip_name") == vvip_name), None)

    if not membership:
        return await callback_query.answer(lang.get("member_portal.not_found"), show_alert=True)
    
    chat_id = membership.get("chat_id_kick")
    if not chat_id:
        return await callback_query.answer(lang.get("member_portal.chat_id_missing"), show_alert=True)
        
    try:
        expire_date_link = datetime.now() + timedelta(hours=2)
        invite_link_obj = await client.create_chat_invite_link(
            chat_id=chat_id,
            member_limit=1,
            expire_date=expire_date_link
        )
        link = invite_link_obj.invite_link
        await client.send_message(user_id, lang.get("member_portal.link_resent", name=vvip_name, link=link), protect_content=True)
        await callback_query.answer(lang.get("member_portal.link_sent_alert"), show_alert=True)
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal kirim ulang link untuk {user_id}: {e}")
        await callback_query.answer(lang.get("general.error", e=e), show_alert=True)


@command(lambda ctx: filters.regex(r"^list_members_(\-?\d+)$"), handler_type="callback")
async def list_members_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    members_list = ctx.db.getListVars(client.me.id, "vvip_members") or []

    back_btn_text = f"| {lang.get('general.back_to_settings')} - settings |"

    if not members_list:
        text = lang.get("member.list.empty")
        btn, _ = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{back_btn_text}")
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)

    total_pages = len(members_list)
    try:
        page = int(callback_query.data.split("_")[-1])
        page = (page + total_pages) % total_pages
    except (ValueError, IndexError):
        page = 0

    member_data = members_list[page]
    try:
        user_id, vvip_name = member_data["user_id"], member_data["vvip_name"]
        join_date_iso, pay_type = member_data["join_date"], member_data["payment_type"]
        user = await client.get_users(user_id)
    except (KeyError, pyrogram.errors.UserNotParticipant) as e:
        text_error = lang.get("member.list.data_error", e=e)
        await callback_query.edit_message_caption(
            text_error,
            reply_markup=client.ns.telegram.button.create_inline_keyboard(back_btn_text)[0],
        )
        ctx.db.removeListVars(client.me.id, "vvip_members", member_data)
        return

    join_dt_utc = datetime.fromisoformat(join_date_iso)
    
    expiry_date_str = lang.get("member_portal.permanent")
    expiry_date_obj_str = member_data.get("expiry_date")
    if expiry_date_obj_str:
        expiry_date_obj = datetime.fromisoformat(expiry_date_obj_str)
        expiry_date_str = expiry_date_obj.strftime("%d %b %Y, %H:%M %Z")

    text = lang.get(
        "member.list.panel",
        page=page + 1,
        total=total_pages,
        mention=client.ns.telegram.arg.getMention(user),
        id=user.id,
        category=vvip_name,
        type=pay_type.title(),
        date=join_dt_utc.strftime("%d %b %Y, %H:%M %Z"),
        expiry=expiry_date_str,
    )

    btn_text_list = [
        f"| {lang.get('member.list.kick_button', name=client.ns.telegram.arg.getMention(user, no_tag=True) if user.first_name else user.id)} - kick_{user.id}_{vvip_name} |"
    ]
    if total_pages > 1:
        prev_page, next_page = (
            (page - 1 + total_pages) % total_pages,
            (page + 1) % total_pages,
        )
        btn_text_list.append(
            f"| {lang.get('admin.allbots.prev_button')} - list_members_{prev_page} | | {lang.get('admin.allbots.next_button')} - list_members_{next_page};same |"
        )
    btn_text_list.append(back_btn_text)

    btn, _ = client.ns.telegram.button.create_inline_keyboard("\n".join(btn_text_list))
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^kick_(\d+)_(.+)"), handler_type="callback")
async def confirm_kick_member_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    _, user_id_str, vvip_name = callback_query.data.split("_", 2)
    user = await client.get_users(int(user_id_str))

    text = lang.get(
        "member.kick.confirm_panel",
        mention=client.ns.telegram.arg.getMention(user),
        name=vvip_name,
    )
    btn_text = f"| {lang.get('member.kick.confirm_yes_button')} - do_kick_{user_id_str}_{vvip_name} | | {lang.get('member.kick.confirm_no_button')} - list_members_0 |"

    btn, _ = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^do_kick_(\d+)_(.+)"), handler_type="callback")
async def do_kick_member_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    _, user_id_str, vvip_name = callback_query.data.split("_", 2)
    user_id = int(user_id_str)
    members_list = ctx.db.getListVars(client.me.id, "vvip_members") or []
    record_to_remove = next(
        (r for r in members_list if r.get("user_id") == user_id and r.get("vvip_name") == vvip_name),
        None,
    )

    if not record_to_remove:
        return await callback_query.edit_message_caption(lang.get("member.kick.record_not_found"))

    chat_id_kick = record_to_remove.get("chat_id_kick")
    if not chat_id_kick:
        return await callback_query.edit_message_caption(lang.get("member.kick.invalid_chat_id"))

    await callback_query.edit_message_caption(lang.get("member.kick.processing"))
    try:
        await client.ban_chat_member(chat_id_kick, user_id)
        await asyncio.sleep(1)
        await client.unban_chat_member(chat_id_kick, user_id)
        ctx.db.removeListVars(client.me.id, "vvip_members", record_to_remove)
        user_to_kick = await client.get_users(user_id)
        await callback_query.edit_message_caption(
            lang.get(
                "member.kick.success",
                mention=client.ns.telegram.arg.getMention(user_to_kick),
                name=vvip_name,
            )
        )
    except Exception as e:
        await callback_query.edit_message_caption(lang.get("member.kick.fail", e=e))


@command(lambda ctx: filters.regex("^check_active_menu"), handler_type="callback")
async def check_active_menu_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    if "init" in callback_query.data:
        ctx.ACTIVE_MEMBERS_CACHE = {}

    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
    btn_text_list = []
    for item in vvip_list:
        name, chat_id_norm, chat_id_promo = (
            item.get("name"),
            item.get("chat_id_normal"),
            item.get("chat_id_promo"),
        )
        if name and chat_id_norm:
            btn_text_list.append(
                f"| {lang.get('member.active_list.button_normal', name=name)} - list_active_{chat_id_norm}_0 |"
            )
        if name and chat_id_promo:
            btn_text_list.append(
                f"| {lang.get('member.active_list.button_promo', name=name)} - list_active_{chat_id_promo}_0;same |"
            )

    back_btn_text = f"| {lang.get('general.back_to_settings')} - settings |"

    if not btn_text_list:
        text = lang.get("member.active_list.no_valid_chat_id")
        btn, _ = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{back_btn_text}")
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)

    btn_text = "\n".join(btn_text_list)
    btn_text += f"\n{back_btn_text}"
    text = lang.get("member.active_list.panel")
    btn, _ = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex(r"^list_active_(\-?\d+)_(\-?\d+)"),
    handler_type="callback",
)
async def list_active_members_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    try:
        _, _, chat_id_str, page_str = callback_query.data.split("_", 3)
        chat_id, page = int(chat_id_str), int(page_str)
    except Exception:
        return await callback_query.answer(lang.get("general.invalid_callback"))

    if chat_id not in ctx.ACTIVE_MEMBERS_CACHE:
        try:
            await callback_query.answer(lang.get("member.active_list.fetching"), show_alert=False)
            members = [m async for m in client.get_chat_members(chat_id) if not m.user.is_bot]
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = members
        except Exception as e:
            return await callback_query.edit_message_caption(lang.get("member.active_list.fetch_fail", e=e))

    all_members = ctx.ACTIVE_MEMBERS_CACHE.get(chat_id, [])
    if not all_members:
        return await callback_query.edit_message_caption(lang.get("member.active_list.empty"))

    total_members = len(all_members)
    page = (page + total_members) % total_members
    member, user = all_members[page], all_members[page].user

    text = lang.get(
        "member.active_list.member_panel",
        page=page + 1,
        total=total_members,
        mention=client.ns.telegram.arg.getMention(user),
        id=user.id,
        status=member.status.name.title(),
    )

    btn_text_list = [f"| {lang.get('member.list.kick_button', name=client.ns.telegram.arg.getMention(user, no_tag=True) if user.first_name else user.id)} - kick_active_{chat_id}_{user.id}_{page} |"]
    if total_members > 1:
        prev_p, next_p = (
            (page - 1 + total_members) % total_members,
            (page + 1) % total_members,
        )
        btn_text_list.append(f"| « - list_active_{chat_id}_{prev_p} | | » - list_active_{chat_id}_{next_p};same |")

    btn_text_list.append(f"| {lang.get('general.back_to_group_selection')} - check_active_menu_init |")

    btn, _ = client.ns.telegram.button.create_inline_keyboard("\n".join(btn_text_list))
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex(r"^kick_active_(\-?\d+)_(\d+)_(\-?\d+)"),
    handler_type="callback",
)
async def confirm_kick_active_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    _, _, chat_id_str, user_id_str, page_str = callback_query.data.split("_", 4)
    user = await client.get_users(int(user_id_str))

    text = lang.get("member.active_list.kick_confirm_panel", mention=client.ns.telegram.arg.getMention(user))
    btn_text = f"| {lang.get('member.active_list.kick_confirm_yes_button')} - do_kick_active_{chat_id_str}_{user_id_str} | | {lang.get('member.active_list.kick_confirm_no_button')} - list_active_{chat_id_str}_{page_str} |"

    btn, _ = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex(r"^do_kick_active_(\-?\d+)_(\d+)"),
    handler_type="callback",
)
async def do_kick_active_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    _, _, _, chat_id_str, user_id_str = callback_query.data.split("_", 4)
    chat_id, user_id = int(chat_id_str), int(user_id_str)

    try:
        await callback_query.edit_message_caption(lang.get("member.active_list.kick_processing"))
        await client.ban_chat_member(chat_id, user_id)
        await client.unban_chat_member(chat_id, user_id)

        members_list = ctx.db.getListVars(client.me.id, "vvip_members") or []
        record_to_remove = next(
            (r for r in members_list if r.get("user_id") == user_id and r.get("chat_id_kick") == chat_id),
            None,
        )
        if record_to_remove:
            ctx.db.removeListVars(client.me.id, "vvip_members", record_to_remove)

        if chat_id in ctx.ACTIVE_MEMBERS_CACHE:
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = [m for m in ctx.ACTIVE_MEMBERS_CACHE[chat_id] if m.user.id != user_id]

        user = await client.get_users(user_id)
        text = lang.get("member.active_list.kick_success", mention=client.ns.telegram.arg.getMention(user))
        btn_text = f"| {lang.get('general.back_to_group_selection')} - check_active_menu_init |"
        btn, _ = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")
        if callback_query.message.photo:
            await callback_query.edit_message_caption(text, reply_markup=btn)
        else:
            await callback_query.edit_message_text(text, reply_markup=btn)

    except Exception as e:
        await callback_query.edit_message_caption(lang.get("member.kick.fail", e=e))
