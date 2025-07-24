from . import *

@command(lambda ctx: filters.regex(r"^list_members_(\-?\d+)$"), handler_type="callback")
async def list_members_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    members_list = ctx.db.getListVars(client.me.id, "vvip_members") or []

    back_btn_text = f"| {lang.get('general.back_to_settings')} - settings |"

    if not members_list:
        btn, txt = client.ns.button.create_keyboard(
            f"{lang.get('member.list.empty')}\n\n{back_btn_text}"
        )
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(txt, reply_markup=btn)
        return await callback_query.edit_message_text(txt, reply_markup=btn)


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
        await callback_query.edit_message_caption(
            lang.get("member.list.data_error", e=e),
            reply_markup=client.ns.button.create_keyboard(back_btn_text)[0],
        )
        ctx.db.removeListVars(client.me.id, "vvip_members", member_data)
        return

    join_dt_utc = datetime.fromisoformat(join_date_iso)
    duration_days = (datetime.now(timezone.utc) - join_dt_utc).days

    text = f"**{lang.get('member.list.title', page=page + 1, total=total_pages)}**\n\n"
    text += (
        f"**{lang.get('general.name')}:** {client.ns.arg.getMention(user)}\n"
        f"**{lang.get('general.id')}:** `{user.id}`\n"
        f"**{lang.get('member.list.category')}:** `{vvip_name}` ({pay_type.title()})\n"
        f"**{lang.get('member.list.joined')}:** `{join_dt_utc.strftime('%d %b %Y, %H:%M UTC')}`\n"
        f"**{lang.get('member.list.duration')}:** `{duration_days}` {lang.get('admin.allbots.days')}"
    )

    btn_text = f"| {lang.get('member.list.kick_button', name=user.first_name or user.id)} - kick_{user.id}_{vvip_name} |\n"
    if total_pages > 1:
        prev_page, next_page = (
            (page - 1 + total_pages) % total_pages,
            (page + 1) % total_pages,
        )
        btn_text += f"| {lang.get('admin.allbots.prev_button')} - list_members_{prev_page} | | {lang.get('admin.allbots.next_button')} - list_members_{next_page};same |\n"
    btn_text += back_btn_text

    btn, _ = client.ns.button.create_keyboard(btn_text)
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

    prompt = lang.get(
        "member.kick.confirm_prompt",
        mention=client.ns.arg.getMention(user),
        name=vvip_name,
    )
    btn_text = f"| {lang.get('member.kick.confirm_yes_button')} - do_kick_{user_id_str}_{vvip_name} | | {lang.get('member.kick.confirm_no_button')} - list_members_0 |"

    btn, txt = client.ns.button.create_keyboard(
        f"**{lang.get('member.kick.confirm_title')}**\n\n{prompt}\n\n{btn_text}"
    )
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)

@command(lambda ctx: filters.regex(r"^do_kick_(\d+)_(.+)"), handler_type="callback")
async def do_kick_member_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    lang = callback_query.lang
    _, _, user_id_str, vvip_name = callback_query.data.split("_", 3)
    user_id = int(user_id_str)
    members_list = ctx.db.getListVars(client.me.id, "vvip_members") or []
    record_to_remove = next(
        (
            r
            for r in members_list
            if r.get("user_id") == user_id and r.get("vvip_name") == vvip_name
        ),
        None,
    )

    if not record_to_remove:
        return await callback_query.edit_message_caption(
            lang.get("member.kick.record_not_found")
        )

    chat_id_kick = record_to_remove.get("chat_id_kick")
    if not chat_id_kick:
        return await callback_query.edit_message_caption(
            lang.get("member.kick.invalid_chat_id")
        )

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
                mention=client.ns.arg.getMention(user_to_kick),
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
    btn_text = ""
    for item in vvip_list:
        name, chat_id_norm, chat_id_promo = (
            item.get("name"),
            item.get("chat_id_normal"),
            item.get("chat_id_promo"),
        )
        if name and chat_id_norm:
            btn_text += f"| {lang.get('member.active_list.button_normal', name=name)} - list_active_{chat_id_norm}_0 |\n"
        if name and chat_id_promo:
            btn_text += f"| {lang.get('member.active_list.button_promo', name=name)} - list_active_{chat_id_promo}_0;same |\n"

    back_btn_text = f"| {lang.get('general.back_to_settings')} - settings |"
    if not btn_text:
        btn, txt = client.ns.button.create_keyboard(
            f"{lang.get('member.active_list.no_valid_chat_id')}\n\n{back_btn_text}"
        )
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(txt, reply_markup=btn)
        return await callback_query.edit_message_text(txt, reply_markup=btn)


    btn_text += back_btn_text
    text = f"**{lang.get('member.active_list.title')}**\n\n{lang.get('member.active_list.prompt')}"
    btn, _ = client.ns.button.create_keyboard(f"{text}\n\n{btn_text}")
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


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
            await callback_query.answer(
                lang.get("member.active_list.fetching"), show_alert=False
            )
            members = [
                m async for m in client.get_chat_members(chat_id) if not m.user.is_bot
            ]
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = members
        except Exception as e:
            return await callback_query.edit_message_caption(
                lang.get("member.active_list.fetch_fail", e=e)
            )

    all_members = ctx.ACTIVE_MEMBERS_CACHE.get(chat_id, [])
    if not all_members:
        return await callback_query.edit_message_caption(
            lang.get("member.active_list.empty")
        )

    total_members = len(all_members)
    page = (page + total_members) % total_members
    member, user = all_members[page], all_members[page].user

    text = f"**{lang.get('member.active_list.active_title', page=page + 1, total=total_members)}**\n\n"
    text += f"**{lang.get('general.name')}:** {client.ns.arg.getMention(user)}\n"
    text += f"**{lang.get('general.id')}:** `{user.id}`\n"
    text += f"**{lang.get('general.status')}:** `{member.status.name.title()}`"
    
    kick_button_name = user.first_name or user.id
    btn_text = f"| 🚨 {kick_button_name} - kick_active_{chat_id}_{user.id}_{page} |\n"
    if total_members > 1:
        prev_p, next_p = (
            (page - 1 + total_members) % total_members,
            (page + 1) % total_members,
        )
        btn_text += f"| « - list_active_{chat_id}_{prev_p} | | » - list_active_{chat_id}_{next_p};same |\n"
    
    btn_text += (
        f"| {lang.get('general.back_to_group_selection')} - check_active_menu_init |"
    )
    btn, _ = client.ns.button.create_keyboard(text + "\n\n" + btn_text)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)

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

    text = f"**{lang.get('member.active_list.kick_confirm_title')}**\n{lang.get('member.active_list.kick_confirm_prompt', mention=client.ns.arg.getMention(user))}"
    btn_text = f"| {lang.get('member.active_list.kick_confirm_yes_button')} - do_kick_active_{chat_id_str}_{user_id_str} | | {lang.get('member.active_list.kick_confirm_no_button')} - list_active_{chat_id_str}_{page_str} |"

    btn, _ = client.ns.button.create_keyboard(f"{text}\n\n{btn_text}")
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


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
        await callback_query.edit_message_caption(
            lang.get("member.active_list.kick_processing")
        )
        await client.ban_chat_member(chat_id, user_id)
        await client.unban_chat_member(chat_id, user_id)

        members_list = ctx.db.getListVars(client.me.id, "vvip_members") or []
        record_to_remove = next(
            (
                r
                for r in members_list
                if r.get("user_id") == user_id and r.get("chat_id_kick") == chat_id
            ),
            None,
        )
        if record_to_remove:
            ctx.db.removeListVars(client.me.id, "vvip_members", record_to_remove)

        if chat_id in ctx.ACTIVE_MEMBERS_CACHE:
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = [
                m for m in ctx.ACTIVE_MEMBERS_CACHE[chat_id] if m.user.id != user_id
            ]

        user = await client.get_users(user_id)
        text = f"{lang.get('member.active_list.kick_success', mention=client.ns.arg.getMention(user))}"
        btn_text = f"| {lang.get('general.back_to_group_selection')} - check_active_menu_init |"
        btn, _ = client.ns.button.create_keyboard(f"{text}\n\n{btn_text}")
        if callback_query.message.photo:
            await callback_query.edit_message_caption(txt, reply_markup=btn)
        else:
            await callback_query.edit_message_text(txt, reply_markup=btn)


    except Exception as e:
        await callback_query.edit_message_caption(lang.get("member.kick.fail", e=e))
