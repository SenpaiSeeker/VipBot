import random
from datetime import datetime

from telethon import events

from .. import command, ctx, is_bot_owner


@command(lambda ctx: events.CallbackQuery(pattern=b"^list_members_"))
async def list_members_callback(client, event):
    sender = await event.get_sender()

    if not await is_bot_owner(client, sender.id):
        return

    em = client.ns.emoji
    members_list = await ctx.db.getListVars(client.uid, "vvip_members") or []
    back_row = [{"text": "◀️ Kembali ke Pengaturan", "callback_data": "settings", "style": "primary", "emoji": 5373098009640836781}]

    if not members_list:
        text = f"{em.white_check_mark} Tidak ada member VVIP yang tercatat di database."
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await event.edit(text, buttons=btn, parse_mode="html")

    total_pages = len(members_list)
    payload = event.data.decode("utf-8")

    try:
        page = int(payload.split("_")[-1])
        page = (page + total_pages) % total_pages
    except (ValueError, IndexError):
        page = 0

    member_data = members_list[page]

    try:
        user_id = member_data["user_id"]
        vvip_name = member_data["vvip_name"]
        join_date_iso = member_data["join_date"]
        pay_type = member_data["payment_type"]
        user = await client.get_entity(user_id)
    except Exception as e:
        text_error = (
            f"Data member ini tampaknya rusak atau tidak dapat diakses lagi.\n"
            f"<code>Error: {e}</code>\n\nEntri ini telah dihapus."
        )
        btn_back = client.ns.telegram.button.build_button_grid([back_row])
        await event.edit(text_error, buttons=btn_back, parse_mode="html")
        await ctx.db.removeListVars(client.uid, "vvip_members", member_data)
        return

    join_dt_utc = datetime.fromisoformat(join_date_iso)
    expiry_date_str = "Permanen"
    expiry_date_obj_str = member_data.get("expiry_date")

    if expiry_date_obj_str:
        expiry_date_obj = datetime.fromisoformat(expiry_date_obj_str)
        expiry_date_str = expiry_date_obj.strftime("%d %b %Y, %H:%M %Z")

    text = (
        f"{em.busts_in_silhouette} <b>Daftar Member VVIP ({page + 1}/{total_pages})</b>\n\n"
        f"<b>Nama:</b> {client.ns.telegram.arg.getMention(user)}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"<b>Kategori:</b> <code>{vvip_name}</code> ({pay_type.title()})\n"
        f"<b>Bergabung:</b> <code>{join_dt_utc.strftime('%d %b %Y, %H:%M %Z')}</code>\n"
        f"<b>Kedaluwarsa:</b> <code>{expiry_date_str}</code>"
    )

    button_name = (user.first_name or str(user.id))[:15]
    layout = []
    pagination_row = []

    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages
        pagination_row.extend(
            [
                {"text": "« Sebelumnya", "callback_data": f"list_members_{prev_page}", "style": "primary", "emoji": 5373098009640836781},
                {"text": "Selanjutnya »", "callback_data": f"list_members_{next_page}", "style": "primary", "emoji": 5373098009640836781},
            ]
        )

    if pagination_row:
        layout.append(pagination_row)

    layout.append(
        [
            {
                "text": f"🦵 Tendang {button_name}",
                "callback_data": f"kick_{user.id}_{vvip_name}",
                "style": "danger",
                "emoji": 5465665476971471368,
            }
        ]
    )
    layout.append(back_row)

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^kick_"))
async def confirm_kick_member_callback(client, event):
    sender = await event.get_sender()

    if not await is_bot_owner(client, sender.id):
        return

    payload = event.data.decode("utf-8")
    parts = payload.split("_")
    user_id_str = parts[1]
    vvip_name = parts[2]
    em = client.ns.emoji

    user = await client.get_entity(int(user_id_str))
    text = (
        f"{em.anger} <b>Konfirmasi Penendangan</b>\n\n"
        f"Anda yakin ingin menendang <b>{client.ns.telegram.arg.getMention(user)}</b> "
        f"dari grup VVIP <b>{vvip_name}</b>?\n\n"
        f"Pengguna akan dikeluarkan dari grup dan data keanggotaannya akan dihapus."
    )

    layout = [
        [
            {
                "text": "✅ Ya, Tendang",
                "callback_data": f"do_kick_{user_id_str}_{vvip_name}",
                "style": "success",
                "emoji": 5427009714745517609,
            },
            {
                "text": "❌ Tidak",
                "callback_data": "list_members_0",
                "style": "danger",
                "emoji": 5465665476971471368,
            },
        ]
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^do_kick_"))
async def do_kick_member_callback(client, event):
    sender = await event.get_sender()

    if not await is_bot_owner(client, sender.id):
        return

    payload = event.data.decode("utf-8")
    parts = payload.split("_")
    user_id = int(parts[2])
    vvip_name = parts[3]
    em = client.ns.emoji

    members_list = await ctx.db.getListVars(client.uid, "vvip_members") or []
    record_to_remove = next(
        (
            r
            for r in members_list
            if r.get("user_id") == user_id and r.get("vvip_name") == vvip_name
        ),
        None,
    )

    if not record_to_remove:
        return await event.edit(
            f"{em.cross_mark} <b>Gagal:</b> Record keanggotaan tidak ditemukan di database.",
            parse_mode="html",
        )

    chat_id_kick = record_to_remove.get("chat_id_kick")
    if not chat_id_kick:
        return await event.edit(
            f"{em.cross_mark} <b>Gagal:</b> Chat ID untuk menendang member tidak valid.",
            parse_mode="html",
        )

    await event.edit(
        f"{em.hourglass} <code>Memproses penendangan member dari grup...</code>",
        parse_mode="html",
    )

    try:
        await client.kick_participant(chat_id_kick, user_id)
        await ctx.db.removeListVars(client.uid, "vvip_members", record_to_remove)
        user_to_kick = await client.get_entity(user_id)

        layout = [[{"text": "◀️ Kembali", "callback_data": "list_members_0", "style": "primary", "emoji": 5373098009640836781}]]
        btn_back = client.ns.telegram.button.build_button_grid(layout)

        await event.edit(
            f"{em.white_check_mark} <b>Sukses!</b>\n"
            f"Pengguna {client.ns.telegram.arg.getMention(user_to_kick)} telah ditendang dari "
            f"<b>{vvip_name}</b> dan dihapus dari daftar.",
            buttons=btn_back,
            parse_mode="html",
        )
    except Exception as e:
        await event.edit(
            f"{em.cross_mark} <b>Gagal Menendang:</b> <code>{e}</code>",
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^check_active_menu"))
async def check_active_menu_callback(client, event):
    sender = await event.get_sender()

    if not await is_bot_owner(client, sender.id):
        return

    if "init" in event.data.decode("utf-8"):
        ctx.ACTIVE_MEMBERS_CACHE = {}

    em = client.ns.emoji
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    layout = []
    button_row = []

    for item in vvip_list:
        name = item.get("name")
        chat_id_norm = item.get("chat_id_normal")
        chat_id_promo = item.get("chat_id_promo")

        if name and chat_id_norm:
            button_row.append(
                {
                    "text": f"👥 '{name}' Normal",
                    "callback_data": f"list_active_{chat_id_norm}_0",
                    "style": "primary",
                    "emoji": 5372926953978341366,
                }
            )
        if name and chat_id_promo:
            button_row.append(
                {
                    "text": f"🎉 '{name}' Promo",
                    "callback_data": f"list_active_{chat_id_promo}_0",
                    "style": "primary",
                    "emoji": 5372926953978341366,
                }
            )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []

    if button_row:
        layout.append(button_row)

    back_row = [{"text": "◀️ Kembali ke Pengaturan", "callback_data": "settings", "style": "primary", "emoji": 5373098009640836781}]

    if not layout:
        text = "Tidak ada VVIP dengan Chat ID valid yang terkonfigurasi."
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await event.edit(text, buttons=btn)

    layout.append(back_row)
    text = (
        f"{em.busts_in_silhouette} <b>Cek Member Aktif Real-time</b>\n\n"
        f"Pilih grup yang ingin Anda periksa untuk melihat daftar anggotanya saat ini."
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^list_active_"))
async def list_active_members_callback(client, event):
    sender = await event.get_sender()

    if not await is_bot_owner(client, sender.id):
        return

    try:
        payload = event.data.decode("utf-8")
        _, _, chat_id_str, page_str = payload.split("_", 3)
        chat_id = int(chat_id_str)
        page = int(page_str)
    except Exception:
        return await event.answer("Data callback tidak valid.", alert=True)

    em = client.ns.emoji

    if chat_id not in ctx.ACTIVE_MEMBERS_CACHE:
        try:
            await event.answer(
                "⏳ Mengambil data member dari server Telegram..."
            )
            members = await client.get_participants(chat_id)
            members = [m for m in members if not m.bot]
            random.shuffle(members)
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = members
        except Exception as e:
            return await event.edit(
                f"{em.cross_mark} <b>Gagal Mengambil Daftar Member:</b>\n<code>{e}</code>",
                parse_mode="html",
            )

    all_members = ctx.ACTIVE_MEMBERS_CACHE.get(chat_id, [])
    if not all_members:
        return await event.edit(
            "Tidak ada anggota (non-bot) yang ditemukan di dalam grup ini."
        )

    total_members = len(all_members)
    page = (page + total_members) % total_members
    user = all_members[page]

    text = (
        f"{em.busts_in_silhouette} <b>Member Aktif ({page + 1}/{total_members})</b>\n\n"
        f"<b>Nama:</b> {client.ns.telegram.arg.getMention(user)}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"<b>Status:</b> <code>Aktif</code>"
    )

    button_name = (user.first_name or str(user.id))[:15]
    layout = []
    pagination_row = []

    if total_members > 1:
        prev_p = (page - 1 + total_members) % total_members
        next_p = (page + 1) % total_members
        pagination_row.extend(
            [
                {"text": "«", "callback_data": f"list_active_{chat_id}_{prev_p}", "style": "primary", "emoji": 5373098009640836781},
                {"text": "»", "callback_data": f"list_active_{chat_id}_{next_p}", "style": "primary", "emoji": 5373098009640836781},
            ]
        )

    if pagination_row:
        layout.append(pagination_row)

    layout.extend(
        [
            [
                {
                    "text": f"🦵 Tendang {button_name}",
                    "callback_data": f"kick_active_{chat_id}_{user.id}_{page}",
                    "style": "danger",
                    "emoji": 5465665476971471368,
                }
            ],
            [
                {
                    "text": "◀️ Kembali ke Pemilihan Grup",
                    "callback_data": "check_active_menu_init",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^kick_active_"))
async def confirm_kick_active_callback(client, event):
    sender = await event.get_sender()

    if not await is_bot_owner(client, sender.id):
        return

    payload = event.data.decode("utf-8")
    _, _, chat_id_str, user_id_str, page_str = payload.split("_", 4)
    em = client.ns.emoji

    user = await client.get_entity(int(user_id_str))
    text = (
        f"{em.anger} <b>Konfirmasi</b>\n\n"
        f"Anda yakin ingin menendang <b>{client.ns.telegram.arg.getMention(user)}</b> dari grup?"
    )

    layout = [
        [
            {
                "text": "✅ Ya, Tendang",
                "callback_data": f"do_kick_active_{chat_id_str}_{user_id_str}",
                "style": "success",
                "emoji": 5427009714745517609,
            },
            {
                "text": "❌ Tidak, Batalkan",
                "callback_data": f"list_active_{chat_id_str}_{page_str}",
                "style": "danger",
                "emoji": 5465665476971471368,
            },
        ]
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^do_kick_active_"))
async def do_kick_active_callback(client, event):
    sender = await event.get_sender()

    if not await is_bot_owner(client, sender.id):
        return

    payload = event.data.decode("utf-8")
    _, _, _, chat_id_str, user_id_str = payload.split("_", 4)
    chat_id = int(chat_id_str)
    user_id = int(user_id_str)
    em = client.ns.emoji

    try:
        await event.edit(
            f"{em.hourglass} <code>Memproses penendangan pengguna...</code>",
            parse_mode="html",
        )
        await client.kick_participant(chat_id, user_id)

        members_list = await ctx.db.getListVars(client.uid, "vvip_members") or []
        record_to_remove = next(
            (
                r
                for r in members_list
                if r.get("user_id") == user_id and r.get("chat_id_kick") == chat_id
            ),
            None,
        )

        if record_to_remove:
            await ctx.db.removeListVars(client.uid, "vvip_members", record_to_remove)

        if chat_id in ctx.ACTIVE_MEMBERS_CACHE:
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = [
                m for m in ctx.ACTIVE_MEMBERS_CACHE[chat_id] if m.id != user_id
            ]

        user = await client.get_entity(user_id)
        text = (
            f"{em.white_check_mark} <b>Sukses!</b>\n"
            f"Pengguna <b>{client.ns.telegram.arg.getMention(user)}</b> telah ditendang dari grup."
        )

        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pemilihan Grup",
                    "callback_data": "check_active_menu_init",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await event.edit(text, buttons=btn, parse_mode="html")
    except Exception as e:
        await event.edit(
            f"{em.cross_mark} <b>Gagal Menendang:</b> <code>{e}</code>",
            parse_mode="html",
        )
