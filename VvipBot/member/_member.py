from .. import *


async def _owner_only(callback_query):
    if not await is_bot_owner(callback_query._client, callback_query.from_user.id):
        return True
    return False


def _back_to_settings(client):
    return {
        "text": "• Kembali ke Pengaturan •",
        "callback_data": "settings",
        "style": "blue",
        "emoji": client.ns.emoji.id("toolbox"),
    }


def _back_to_group_selection(client):
    return {
        "text": "• Kembali ke Pemilihan Grup •",
        "callback_data": "check_active_menu_init",
        "style": "blue",
        "emoji": client.ns.emoji.id("back_arrow"),
    }


async def _reply(client, callback_query, text, btn):
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^list_members_(\\-?\\d+)$"),
    handler_type="callback",
)
async def list_members_callback(client, callback_query):
    if await _owner_only(callback_query):
        return

    members_list = await ctx.db.getListVars(client.me.id, "vvip_members") or []
    back_row = [_back_to_settings(client)]

    if not members_list:
        text = f"{client.ns.emoji.white_check_mark} Tidak ada member VVIP yang tercatat di database."
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await _reply(client, callback_query, text, btn)

    total_pages = len(members_list)
    try:
        page = int(callback_query.data.split("_")[-1])
        page = (page + total_pages) % total_pages
    except (ValueError, IndexError):
        page = 0

    member_data = members_list[page]
    try:
        user_id = member_data["user_id"]
        vvip_name = member_data["vvip_name"]
        join_date_iso = member_data["join_date"]
        pay_type = member_data["payment_type"]
        user = await client.get_users(user_id)
    except (KeyError, pyrogram.errors.UserNotParticipant) as e:
        text_error = (
            f"Data member ini tampaknya rusak atau pengguna tidak dapat diakses lagi.\n"
            f"`Error: {e}`\n\n"
            "Entri ini telah dihapus dari daftar untuk menjaga kebersihan data."
        )
        btn_back = client.ns.telegram.button.build_button_grid(back_row)
        await _reply(client, callback_query, text_error, btn_back)
        await ctx.db.removeListVars(client.me.id, "vvip_members", member_data)
        return

    expiry_date_str = "Permanen"
    expiry_raw = member_data.get("expiry_date")
    if expiry_raw:
        expiry_date_str = datetime.fromisoformat(expiry_raw).strftime(
            "%d %b %Y, %H:%M %Z"
        )

    mention_str = client.ns.telegram.arg.getMention(user)
    join_str = datetime.fromisoformat(join_date_iso).strftime("%d %b %Y, %H:%M %Z")
    text = (
        f"**{client.ns.emoji.busts_in_silhouette} Daftar Member VVIP ({page + 1}/{total_pages})**\n\n"
        f"**Nama:** {mention_str}\n"
        f"**ID:** `{user.id}`\n"
        f"**Kategori:** `{vvip_name}` ({pay_type.title()})\n"
        f"**Bergabung:** `{join_str}`\n"
        f"**Kedaluwarsa:** `{expiry_date_str}`"
    )
    button_name = (user.first_name or str(user.id))[:15]

    layout = []
    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages
        layout.append(
            [
                {
                    "text": "« Sebelumnya",
                    "callback_data": f"list_members_{prev_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                },
                {
                    "text": "Selanjutnya »",
                    "callback_data": f"list_members_{next_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("right_pointing"),
                },
            ]
        )

    layout.append(
        [
            {
                "text": f"🚨 Tendang {button_name}",
                "callback_data": f"kick_{user.id}_{vvip_name}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ]
    )
    layout.append(back_row)
    btn = client.ns.telegram.button.build_button_grid(layout)
    await _reply(client, callback_query, text, btn)


@command(
    lambda ctx: filters.regex("^kick_(\\d+)_(.+)"),
    handler_type="callback",
)
async def confirm_kick_member_callback(client, callback_query):
    if await _owner_only(callback_query):
        return
    match = callback_query.matches[0]
    user_id_str = match.group(1)
    vvip_name = match.group(2)
    user = await client.get_users(int(user_id_str))
    mention_str = client.ns.telegram.arg.getMention(user)

    text = (
        f"**{client.ns.emoji.exclamation} Konfirmasi Penendangan**\n\n"
        f"Anda yakin ingin menendang **{mention_str}** dari grup VVIP **{vvip_name}**?\n\n"
        "Pengguna akan dikeluarkan dari grup dan data keanggotaannya akan dihapus."
    )
    layout = [
        [
            {
                "text": "✅ Ya, Tendang",
                "callback_data": f"do_kick_{user_id_str}_{vvip_name}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": "❌ Tidak",
                "callback_data": "list_members_0",
                "style": "green",
                "emoji": client.ns.emoji.id("white_check_mark"),
            },
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)
    await _reply(client, callback_query, text, btn)


@command(
    lambda ctx: filters.regex("^do_kick_(\\d+)_(.+)"),
    handler_type="callback",
)
async def do_kick_member_callback(client, callback_query):
    if await _owner_only(callback_query):
        return
    match = callback_query.matches[0]
    user_id = int(match.group(1))
    vvip_name = match.group(2)

    members_list = await ctx.db.getListVars(client.me.id, "vvip_members") or []
    record = next(
        (
            r
            for r in members_list
            if r.get("user_id") == user_id and r.get("vvip_name") == vvip_name
        ),
        None,
    )
    if not record:
        return await callback_query.edit_message_caption(
            f"{client.ns.emoji.cross_mark} **Gagal:** Record keanggotaan tidak ditemukan di database."
        )

    chat_id_kick = record.get("chat_id_kick")
    if not chat_id_kick:
        return await callback_query.edit_message_caption(
            f"{client.ns.emoji.cross_mark} **Gagal:** Chat ID untuk menendang member tidak valid atau belum diatur di paket VVIP."
        )

    await callback_query.edit_message_caption(
        f"{client.ns.emoji.hourglass} `Memproses penendangan member dari grup...`"
    )
    try:
        await client.ban_chat_member(chat_id_kick, user_id)
        await asyncio.sleep(1)
        await client.unban_chat_member(chat_id_kick, user_id)
        await ctx.db.removeListVars(client.me.id, "vvip_members", record)

        user_to_kick = await client.get_users(user_id)
        mention_str = client.ns.telegram.arg.getMention(user_to_kick)
        layout = [[_back_to_settings(client)]]
        btn_back = client.ns.telegram.button.build_button_grid(layout)
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.white_check_mark} **Sukses!**\n"
            f"Pengguna {mention_str} telah ditendang dari **{vvip_name}** dan dihapus dari daftar.",
            reply_markup=btn_back,
        )
    except Exception as e:
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.cross_mark} **Gagal Menendang:** `{e}`"
        )


@command(
    lambda ctx: filters.regex("^check_active_menu"),
    handler_type="callback",
)
async def check_active_menu_callback(client, callback_query):
    if await _owner_only(callback_query):
        return

    if "init" in callback_query.data:
        ctx.ACTIVE_MEMBERS_CACHE = {}

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    layout = []
    button_row = []
    for item in vvip_list:
        name = item.get("name")
        chat_id_norm = item.get("chat_id_normal")
        chat_id_promo = item.get("chat_id_promo")
        if name and chat_id_norm:
            button_row.append(
                {
                    "text": f"👥 Cek '{name}' Normal",
                    "callback_data": f"list_active_{chat_id_norm}_0",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("busts_in_silhouette"),
                }
            )
        if name and chat_id_promo:
            button_row.append(
                {
                    "text": f"👥 Cek '{name}' Promo",
                    "callback_data": f"list_active_{chat_id_promo}_0",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("busts_in_silhouette"),
                }
            )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []
    if button_row:
        layout.append(button_row)

    back_row = [_back_to_settings(client)]
    if not layout:
        text = "Tidak ada VVIP dengan Chat ID valid yang terkonfigurasi. Silakan atur terlebih dahulu."
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await _reply(client, callback_query, text, btn)

    layout.append(back_row)
    text = (
        f"**{client.ns.emoji.mag} Cek Member Aktif Real-time**\n\n"
        "Pilih grup yang ingin Anda periksa untuk melihat daftar anggotanya saat ini."
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    await _reply(client, callback_query, text, btn)


@command(
    lambda ctx: filters.regex("^list_active_(\\-?\\d+)_(\\-?\\d+)"),
    handler_type="callback",
)
async def list_active_members_callback(client, callback_query):
    if await _owner_only(callback_query):
        return

    try:
        _, _, chat_id_str, page_str = callback_query.data.split("_", 3)
        chat_id = int(chat_id_str)
        page = int(page_str)
    except Exception:
        return await callback_query.answer("Data callback tidak valid.")

    if chat_id not in ctx.ACTIVE_MEMBERS_CACHE:
        try:
            await callback_query.answer(
                "<emoji id=5451732530048802485>⏳</emoji> "
                "Mengambil data member dari server Telegram, mohon tunggu...",
                show_alert=False,
            )
            members = [
                m async for m in client.get_chat_members(chat_id) if not m.user.is_bot
            ]
            random.shuffle(members)
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = members
        except Exception as e:
            await callback_query.edit_message_caption(
                f"{client.ns.emoji.cross_mark} **Gagal Mengambil Daftar Member:**\n`{e}`"
            )
            return

    all_members = ctx.ACTIVE_MEMBERS_CACHE.get(chat_id, [])
    if not all_members:
        return await callback_query.edit_message_caption(
            "Tidak ada anggota (non-bot) yang ditemukan di dalam grup ini."
        )

    total = len(all_members)
    page = (page + total) % total
    member = all_members[page]
    user = member.user

    mention_str = client.ns.telegram.arg.getMention(user)
    text = (
        f"**{client.ns.emoji.mag} Member Aktif ({page + 1}/{total})**\n\n"
        f"**Nama:** {mention_str}\n"
        f"**ID:** `{user.id}`\n"
        f"**Status:** `{member.status.name.title()}`"
    )
    button_name = (user.first_name or str(user.id))[:15]

    layout = []
    if total > 1:
        prev_p = (page - 1 + total) % total
        next_p = (page + 1) % total
        layout.append(
            [
                {
                    "text": "«",
                    "callback_data": f"list_active_{chat_id}_{prev_p}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                },
                {
                    "text": "»",
                    "callback_data": f"list_active_{chat_id}_{next_p}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("right_pointing"),
                },
            ]
        )

    layout.extend(
        [
            [
                {
                    "text": f"🚨 Tendang {button_name}",
                    "callback_data": f"kick_active_{chat_id}_{user.id}_{page}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ],
            [_back_to_group_selection(client)],
        ]
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    await _reply(client, callback_query, text, btn)


@command(
    lambda ctx: filters.regex("^kick_active_(\\-?\\d+)_(\\d+)_(\\-?\\d+)"),
    handler_type="callback",
)
async def confirm_kick_active_callback(client, callback_query):
    if await _owner_only(callback_query):
        return

    _, _, chat_id_str, user_id_str, page_str = callback_query.data.split("_", 4)
    user = await client.get_users(int(user_id_str))
    mention_str = client.ns.telegram.arg.getMention(user)

    text = (
        f"**{client.ns.emoji.exclamation} Konfirmasi**\n\n"
        f"Anda yakin ingin menendang **{mention_str}** dari grup?"
    )
    layout = [
        [
            {
                "text": "✅ Ya, Tendang",
                "callback_data": f"do_kick_active_{chat_id_str}_{user_id_str}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": "❌ Tidak, Batalkan",
                "callback_data": f"list_active_{chat_id_str}_{page_str}",
                "style": "green",
                "emoji": client.ns.emoji.id("white_check_mark"),
            },
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)
    await _reply(client, callback_query, text, btn)


@command(
    lambda ctx: filters.regex("^do_kick_active_(\\-?\\d+)_(\\d+)"),
    handler_type="callback",
)
async def do_kick_active_callback(client, callback_query):
    if await _owner_only(callback_query):
        return

    _, _, _, chat_id_str, user_id_str = callback_query.data.split("_", 4)
    chat_id = int(chat_id_str)
    user_id = int(user_id_str)

    try:
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.hourglass} `Memproses penendangan pengguna...`"
        )
        await client.ban_chat_member(chat_id, user_id)
        await client.unban_chat_member(chat_id, user_id)

        members_list = await ctx.db.getListVars(client.me.id, "vvip_members") or []
        record = next(
            (
                r
                for r in members_list
                if r.get("user_id") == user_id and r.get("chat_id_kick") == chat_id
            ),
            None,
        )
        if record:
            await ctx.db.removeListVars(client.me.id, "vvip_members", record)

        if chat_id in ctx.ACTIVE_MEMBERS_CACHE:
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = [
                m for m in ctx.ACTIVE_MEMBERS_CACHE[chat_id] if m.user.id != user_id
            ]

        user = await client.get_users(user_id)
        mention_str = client.ns.telegram.arg.getMention(user)
        text = (
            f"{client.ns.emoji.white_check_mark} **Sukses!**\n"
            f"Pengguna **{mention_str}** telah ditendang dari grup."
        )
        layout = [[_back_to_group_selection(client)]]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await _reply(client, callback_query, text, btn)
    except Exception as e:
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.cross_mark} **Gagal Menendang:** `{e}`"
        )