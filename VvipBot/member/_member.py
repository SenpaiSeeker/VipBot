import pyrogram

from .. import *


@command(
    lambda ctx: filters.regex("^list_members_(\\-?\\d+)$"),
    handler_type="callback",
)
async def list_members_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    members_list = await ctx.db.getListVars(client.me.id, "vvip_members") or []
    back_row = [
        {
            "text": "• Kembali ke Pengaturan •",
            "callback_data": "settings",
            "style": "blue",
            "emoji": client.ns.emoji.id("toolbox"),
        }
    ]
    if not members_list:
        table = client.ns.table
        empty_rows = [
            ["Total Member", "`0`"],
            ["Status", "Belum ada member VVIP tercatat"],
        ]
        text = (
            f"{client.ns.emoji.html('busts_in_silhouette')} <b>Daftar Member VVIP</b>\n\n"
            f"{table.caption(['Info', 'Nilai'], empty_rows)}"
        )
        rich_text = (
            f"{client.ns.emoji.md('busts_in_silhouette')} **Daftar Member VVIP**\n\n"
            f"{table.md(['Info', 'Nilai'], empty_rows)}"
        )
        btn = client.ns.telegram.button.build_button_grid([back_row])
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=rich_text),
            reply_markup=btn,
        )
    total_pages = len(members_list)
    try:
        page = int(callback_query.data.split("_")[-1])
        page = (page + total_pages) % total_pages
    except (ValueError, IndexError):
        page = 0
    member_data = members_list[page]
    try:
        user_id, vvip_name = (
            member_data["user_id"],
            member_data["vvip_name"],
        )
        join_date_iso, pay_type = (
            member_data["join_date"],
            member_data["payment_type"],
        )
        user = await client.get_users(user_id)
    except (
        KeyError,
        pyrogram.errors.UserNotParticipant,
    ) as e:
        text_error = (
            f"<b>Data Member Bermasalah</b>\n\n"
            f"{client.ns.table.caption(['Info', 'Isi'], [['Status', 'Pengguna tidak dapat diakses'], ['Error', f'{e}'], ['Tindakan', 'Entri dihapus dari daftar']])}"
        )
        btn_back = client.ns.telegram.button.build_button_grid([back_row])
        await callback_query.edit_message_caption(text_error, reply_markup=btn_back)
        await ctx.db.removeListVars(client.me.id, "vvip_members", member_data)
        return
    join_dt_utc = datetime.fromisoformat(join_date_iso)
    expiry_date_str = "Permanen"
    expiry_date_obj_str = member_data.get("expiry_date")
    if expiry_date_obj_str:
        expiry_date_obj = datetime.fromisoformat(expiry_date_obj_str)
        expiry_date_str = expiry_date_obj.strftime("%d %b %Y, %H:%M %Z")

    mention_str = client.ns.telegram.arg.getMention(user)
    formatted_join_date = join_dt_utc.strftime("%d %b %Y, %H:%M %Z")
    rows = [
        ["Nama", mention_str],
        ["ID", f"`{user.id}`"],
        ["Kategori", f"`{vvip_name}` ({pay_type.title()})"],
        ["Bergabung", f"`{formatted_join_date}`"],
        ["Kedaluwarsa", f"`{expiry_date_str}`"],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.html('busts_in_silhouette')} <b>Daftar Member VVIP ({page + 1}/{total_pages})</b>\n\n"
        f"{table.caption(['Label', 'Isi'], rows)}"
    )
    rich_text = (
        f"{client.ns.emoji.md('busts_in_silhouette')} **Daftar Member VVIP ({page + 1}/{total_pages})**\n\n"
        f"{table.md(['Label', 'Isi'], rows)}"
    )
    button_name = (user.first_name or str(user.id))[:15]
    layout = []
    pagination_row = []
    if total_pages > 1:
        prev_page, next_page = (
            (page - 1 + total_pages) % total_pages,
            (page + 1) % total_pages,
        )
        pagination_row.extend(
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
    if pagination_row:
        layout.append(pagination_row)
    layout.append(
        [
            {
                "text": f"🚨 Tendang {button_name}",
                "callback_data": f"kick_{user.id}_{vvip_name}",
                "style": "red",
                "emoji": client.ns.emoji.id("cross_mark"),
            }
        ]
    )
    layout.append(back_row)
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=rich_text),
            reply_markup=btn,
        )


@command(
    lambda ctx: filters.regex("^kick_(\\d+)_(.+)"),
    handler_type="callback",
)
async def confirm_kick_member_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    match = callback_query.matches[0]
    user_id_str = match.group(1)
    vvip_name = match.group(2)
    user = await client.get_users(int(user_id_str))

    mention_str = client.ns.telegram.arg.getMention(user)
    text = (
        f"**{client.ns.emoji.exclamation} Konfirmasi Penendangan**\n\n"
        f"Anda yakin ingin menendang **{mention_str}** dari grup VVIP **{vvip_name}**?\n\n"
        f"Pengguna akan dikeluarkan dari grup dan data keanggotaannya akan dihapus."
    )
    rich_text = (
        f"{client.ns.emoji.md('exclamation')} **Konfirmasi Penendangan**\n\n"
        f"Anda yakin ingin menendang **{mention_str}** dari grup VVIP **{vvip_name}**?\n\n"
        f"Pengguna akan dikeluarkan dari grup dan data keanggotaannya akan dihapus."
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
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=rich_text),
            reply_markup=btn,
        )


@command(
    lambda ctx: filters.regex("^do_kick_(\\d+)_(.+)"),
    handler_type="callback",
)
async def do_kick_member_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    match = callback_query.matches[0]
    user_id = int(match.group(1))
    vvip_name = match.group(2)
    members_list = await ctx.db.getListVars(client.me.id, "vvip_members") or []
    record_to_remove = next(
        (
            r
            for r in members_list
            if r.get("user_id") == user_id and r.get("vvip_name") == vvip_name
        ),
        None,
    )
    if not record_to_remove:
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.cross_mark} **Gagal:** Record keanggotaan tidak ditemukan di database."
        )
        return
    chat_id_kick = record_to_remove.get("chat_id_kick")
    if not chat_id_kick:
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.cross_mark} **Gagal:** Chat ID untuk menendang member tidak valid atau belum diatur di paket VVIP."
        )
        return
    await callback_query.edit_message_caption(
        f"{client.ns.emoji.hourglass} `Memproses penendangan member dari grup...`"
    )
    try:
        await client.ban_chat_member(chat_id_kick, user_id)
        await asyncio.sleep(1)
        await client.unban_chat_member(chat_id_kick, user_id)
        await ctx.db.removeListVars(client.me.id, "vvip_members", record_to_remove)
        user_to_kick = await client.get_users(user_id)
        layout = [
            [
                {
                    "text": "• Kembali •",
                    "callback_data": "list_members_0",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ]
        ]
        btn_back = client.ns.telegram.button.build_button_grid(layout)

        mention_str = client.ns.telegram.arg.getMention(user_to_kick)
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
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    if "init" in callback_query.data:
        ctx.ACTIVE_MEMBERS_CACHE = {}
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    layout = []
    button_row = []
    for item in vvip_list:
        name, chat_id_norm, chat_id_promo = (
            item.get("name"),
            item.get("chat_id_normal"),
            item.get("chat_id_promo"),
        )
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
    back_row = [
        {
            "text": "• Kembali ke Pengaturan •",
            "callback_data": "settings",
            "style": "blue",
            "emoji": client.ns.emoji.id("toolbox"),
        }
    ]
    if not layout:
        table = client.ns.table
        empty_rows = [
            ["Jumlah VVIP", "`0`"],
            ["Status", "Tidak ada Chat ID valid"],
            ["Saran", "Atur Chat ID terlebih dahulu"],
        ]
        text = (
            f"{client.ns.emoji.html('busts_in_silhouette')} <b>Daftar Member VVIP</b>\n\n"
            f"{table.caption(['Info', 'Nilai'], empty_rows)}"
        )
        rich_text = (
            f"{client.ns.emoji.md('busts_in_silhouette')} **Daftar Member VVIP**\n\n"
            f"{table.md(['Info', 'Nilai'], empty_rows)}"
        )
        btn = client.ns.telegram.button.build_button_grid([back_row])
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=rich_text),
            reply_markup=btn,
        )
    layout.append(back_row)

    text = (
        f"**{client.ns.emoji.mag} Cek Member Aktif Real-time**\n\n"
        f"Pilih grup yang ingin Anda periksa untuk melihat daftar anggotanya saat ini."
    )
    rich_text = (
        f"{client.ns.emoji.md('mag')} **Cek Member Aktif Real-time**\n\n"
        f"Pilih grup yang ingin Anda periksa untuk melihat daftar anggotanya saat ini."
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=rich_text),
            reply_markup=btn,
        )


@command(
    lambda ctx: filters.regex("^list_active_(\\-?\\d+)_(\\-?\\d+)"),
    handler_type="callback",
)
async def list_active_members_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    try:
        _, _, chat_id_str, page_str = callback_query.data.split("_", 3)
        chat_id, page = (int(chat_id_str), int(page_str))
    except Exception:
        return await callback_query.answer("Data callback tidak valid.")
    if chat_id not in ctx.ACTIVE_MEMBERS_CACHE:
        try:
            await callback_query.answer(
                "<emoji id=5451732530048802485>⏳</emoji> Mengambil data member dari server Telegram, mohon tunggu...",
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
        empty_rows = [
            ["Jumlah Anggota", "`0`"],
            ["Status", "Tidak ada anggota non-bot di grup ini"],
        ]
        await callback_query.edit_message_caption(
            f"<b>Daftar Member Grup</b>\n\n"
            f"{client.ns.table.caption(['Info', 'Nilai'], empty_rows)}"
        )
        return
    total_members = len(all_members)
    page = (page + total_members) % total_members
    member, user = (
        all_members[page],
        all_members[page].user,
    )

    mention_str = client.ns.telegram.arg.getMention(user)
    text = (
        f"**{client.ns.emoji.mag} Member Aktif ({page + 1}/{total_members})**\n\n"
        f"**Nama:** {mention_str}\n"
        f"**ID:** `{user.id}`\n"
        f"**Status:** `{member.status.name.title()}`"
    )
    rich_text = (
        f"{client.ns.emoji.md('mag')} **Member Aktif ({page + 1}/{total_members})**\n\n"
        f"| Label | Isi |\n"
        f"| :--- | :--- |\n"
        f"| Nama | {mention_str} |\n"
        f"| ID | `{user.id}` |\n"
        f"| Status | `{member.status.name.title()}` |"
    )
    button_name = (user.first_name or str(user.id))[:15]
    layout = []
    pagination_row = []
    if total_members > 1:
        prev_p, next_p = (
            (page - 1 + total_members) % total_members,
            (page + 1) % total_members,
        )
        pagination_row.extend(
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
    if pagination_row:
        layout.append(pagination_row)
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
            [
                {
                    "text": "• Kembali ke Pemilihan Grup •",
                    "callback_data": "check_active_menu_init",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ],
        ]
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=rich_text),
            reply_markup=btn,
        )


@command(
    lambda ctx: filters.regex("^kick_active_(\\-?\\d+)_(\\d+)_(\\-?\\d+)"),
    handler_type="callback",
)
async def confirm_kick_active_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    _, _, chat_id_str, user_id_str, page_str = callback_query.data.split("_", 4)
    user = await client.get_users(int(user_id_str))

    mention_str = client.ns.telegram.arg.getMention(user)
    text = (
        f"**{client.ns.emoji.exclamation} Konfirmasi**\n\n"
        f"Anda yakin ingin menendang **{mention_str}** dari grup?"
    )
    rich_text = (
        f"{client.ns.emoji.md('exclamation')} **Konfirmasi**\n\n"
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
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=rich_text),
            reply_markup=btn,
        )


@command(
    lambda ctx: filters.regex("^do_kick_active_(\\-?\\d+)_(\\d+)"),
    handler_type="callback",
)
async def do_kick_active_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    _, _, _, chat_id_str, user_id_str = callback_query.data.split("_", 4)
    chat_id, user_id = (
        int(chat_id_str),
        int(user_id_str),
    )
    try:
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.hourglass} `Memproses penendangan pengguna...`"
        )
        await client.ban_chat_member(chat_id, user_id)
        await client.unban_chat_member(chat_id, user_id)
        members_list = await ctx.db.getListVars(client.me.id, "vvip_members") or []
        record_to_remove = next(
            (
                r
                for r in members_list
                if r.get("user_id") == user_id and r.get("chat_id_kick") == chat_id
            ),
            None,
        )
        if record_to_remove:
            await ctx.db.removeListVars(
                client.me.id,
                "vvip_members",
                record_to_remove,
            )
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
        rich_text = (
            f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n"
            f"Pengguna **{mention_str}** telah ditendang dari grup."
        )
        layout = [
            [
                {
                    "text": "• Kembali ke Pemilihan Grup •",
                    "callback_data": "check_active_menu_init",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        if callback_query.message.photo:
            await callback_query.edit_message_caption(text, reply_markup=btn)
        else:
            await callback_query.edit_message_text(
                rich_message=pyrogram.types.InputRichMessage(markdown=rich_text),
                reply_markup=btn,
            )
    except Exception as e:
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.cross_mark} **Gagal Menendang:** `{e}`"
        )
