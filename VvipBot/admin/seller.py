from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from telethon import events

from .. import command, ctx, seller_only


@command(lambda ctx: events.NewMessage(incoming=True, pattern=r"^/akses(\s|$)"))
@seller_only
async def access_command_handler(client, event):
    user_id_target, _ = await client.ns.telegram.arg.getReasonAndId(event)
    em = client.ns.emoji

    if not user_id_target:
        return await event.respond(
            f"{em.cross_mark} <b>Format Salah.</b>\nGunakan: <code>/akses &lt;user_id atau @username&gt;</code>",
            parse_mode="html",
        )

    try:
        target_user = await client.get_entity(user_id_target)
        has_access = False
        user_expiry_str = await ctx.db.getVars(target_user.id, "user_expiry_date")

        if user_expiry_str:
            expiry_date = datetime.fromisoformat(user_expiry_str)
            if expiry_date > datetime.now(timezone.utc):
                has_access = True

        status_text = (
            f"{em.white_check_mark} Memiliki Akses"
            if has_access
            else f"{em.cross_mark} Tidak Memiliki Akses"
        )

        text = (
            f"{em.key} <b>Kelola Akses Pembuatan Bot</b>\n\n"
            f"<b>Pengguna:</b> {client.ns.telegram.arg.getMention(target_user)}\n"
            f"<b>ID:</b> <code>{target_user.id}</code>\n"
            f"<b>Status:</b> <code>{status_text}</code>\n\n"
            f"Pilih tindakan untuk pengguna ini:"
        )

        layout = [
            [
                {
                    "text": "✅ Beri Akses",
                    "callback_data": f"give_access_{target_user.id}",
                    "style": "success",
                    "emoji": 5427009714745517609,
                },
                {
                    "text": "❌ Cabut Akses",
                    "callback_data": f"revoke_access_{target_user.id}",
                    "style": "danger",
                    "emoji": 5465665476971471368,
                },
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await event.respond(text, buttons=btn, parse_mode="html")

    except Exception as e:
        await event.respond(
            f"Gagal memproses. Error: <code>{e}</code>",
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^give_access_"))
@seller_only
async def give_access_callback(client, event):
    payload = event.data.decode("utf-8")
    target_id = int(payload.split("_")[-1])

    layout = [
        [
            {"text": f"📅 {m} Bulan", "callback_data": f"do_give_{target_id}_{m}", "style": "primary", "emoji": 5431897022456145283}
            for m in [1, 3, 6, 12]
        ],
        [{"text": "◀️ Kembali", "callback_data": "close_panel", "style": "primary", "emoji": 5373098009640836781}],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit("Pilih durasi akses yang ingin diberikan:", buttons=btn)


@command(lambda ctx: events.CallbackQuery(pattern=b"^do_give_"))
@seller_only
async def do_give_access_callback(client, event):
    payload = event.data.decode("utf-8")
    _, _, target_id_str, months_str = payload.split("_")
    target_id = int(target_id_str)
    months_to_add = int(months_str)
    em = client.ns.emoji

    try:
        target_user = await client.get_entity(target_id)
        current_expiry_str = await ctx.db.getVars(target_id, "user_expiry_date")
        start_date = datetime.now(timezone.utc)

        if current_expiry_str:
            current_expiry = datetime.fromisoformat(current_expiry_str)
            if current_expiry > start_date:
                start_date = current_expiry

        new_expiry_date = start_date + timedelta(days=30 * months_to_add)
        await ctx.db.setVars(target_id, "user_expiry_date", new_expiry_date.isoformat())

        expiry_in_jakarta = new_expiry_date.astimezone(ZoneInfo("Asia/Jakarta"))

        await event.edit(
            f"{em.white_check_mark} <b>Akses Diberikan!</b>\n\n"
            f"Pengguna {client.ns.telegram.arg.getMention(target_user)} sekarang memiliki akses untuk membuat bot selama "
            f"<b>{months_to_add} bulan</b>.\n\n"
            f"Masa aktif akses hingga: <code>{expiry_in_jakarta.strftime('%d %B %Y, %H:%M %Z')}</code>",
            parse_mode="html",
        )
        await event.answer(
            f"✅ Akses berhasil diberikan kepada {target_id}"
        )

    except Exception as e:
        await event.answer(f"Gagal memproses. Error: {e}", alert=True)


@command(lambda ctx: events.CallbackQuery(pattern=b"^revoke_access_"))
@seller_only
async def revoke_access_callback(client, event):
    payload = event.data.decode("utf-8")
    target_id = int(payload.split("_")[-1])
    em = client.ns.emoji

    try:
        target_user = await client.get_entity(target_id)
        mention = client.ns.telegram.arg.getMention(target_user)

        await ctx.db.removeVars(target_id, "user_expiry_date")
        await event.answer(f"❌ Akses berhasil dicabut dari {target_id}")
        await event.edit(
            f"{em.cross_mark} <b>Akses Dicabut!</b>\n\n"
            f"Pengguna {mention} tidak lagi memiliki hak untuk membuat bot.",
            parse_mode="html",
        )

    except Exception as e:
        await event.answer(f"Gagal memproses. Error: {e}", alert=True)


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/addseller(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def add_seller_handler(client, event):
    user_id_target, _ = await client.ns.telegram.arg.getReasonAndId(event)
    em = client.ns.emoji

    if not user_id_target:
        return await event.respond(
            f"{em.cross_mark} Pengguna tidak ditemukan. Pastikan ID/Username benar atau balas pesan pengguna.",
            parse_mode="html",
        )

    try:
        target_user = await client.get_entity(user_id_target)
        seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []

        if target_user.id in seller_list:
            return await event.respond(
                f"{em.cross_mark} User <code>{target_user.id}</code> sudah terdaftar sebagai seller.",
                parse_mode="html",
            )

        await ctx.db.setListVars(ctx.owner_id, "seller_id_list", target_user.id)
        await event.respond(
            f"{em.white_check_mark} Berhasil menambahkan {client.ns.telegram.arg.getMention(target_user)} sebagai seller.",
            parse_mode="html",
        )

    except Exception as e:
        await event.respond(
            f"{em.cross_mark} <b>Terjadi Kesalahan</b>\n<pre>{e}</pre>",
            parse_mode="html",
        )


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/listseller(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def list_seller_handler(client, event):
    seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
    em = client.ns.emoji

    if not seller_list:
        return await event.respond("Belum ada seller yang terdaftar.")

    text = f"{em.bust_in_silhouette} <b>Daftar Seller Aktif</b>\n\n"
    keyboard = []

    for index, user_id in enumerate(seller_list, 1):
        try:
            user_obj = await client.get_entity(user_id)
            mention = client.ns.telegram.arg.getMention(user_obj)
        except Exception:
            mention = f"ID: <code>{user_id}</code>"

        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"🗑️ Hapus Seller ({user_id})",
                    "callback_data": f"del_sell_{user_id}",
                    "style": "danger",
                    "emoji": 5229113891081956317,
                }
            ]
        )

    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await event.respond(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^del_sell_"))
async def delete_seller_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if sender.id != ctx.owner_id:
        return

    payload = event.data.decode("utf-8")
    target_id = int(payload.split("_")[-1])

    await ctx.db.removeListVars(ctx.owner_id, "seller_id_list", target_id)
    await event.answer(f"Seller {target_id} berhasil dihapus.", alert=True)

    seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []

    if not seller_list:
        return await event.edit("Belum ada seller yang terdaftar.")

    text = f"{em.bust_in_silhouette} <b>Daftar Seller Aktif</b>\n\n"
    keyboard = []

    for index, user_id in enumerate(seller_list, 1):
        try:
            user_obj = await client.get_entity(user_id)
            mention = client.ns.telegram.arg.getMention(user_obj)
        except Exception:
            mention = f"ID: <code>{user_id}</code>"

        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"🗑️ Hapus Seller ({user_id})",
                    "callback_data": f"del_sell_{user_id}",
                    "style": "danger",
                    "emoji": 5229113891081956317,
                }
            ]
        )

    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/listakses(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def list_akses_handler(client, event):
    user_ids = await ctx.db.getListVars(client.uid, "user_ids") or []
    em = client.ns.emoji
    access_users = []

    for uid in user_ids:
        if await ctx.db.getVars(uid, "user_expiry_date"):
            access_users.append(uid)

    if not access_users:
        return await event.respond(
            "Tidak ada pengguna yang memiliki akses aktif saat ini."
        )

    text = f"{em.key} <b>Daftar Pengguna Berakses</b>\n\n"
    keyboard = []

    for index, uid in enumerate(access_users, 1):
        try:
            user_obj = await client.get_entity(uid)
            mention = client.ns.telegram.arg.getMention(user_obj)
        except Exception:
            mention = f"ID: <code>{uid}</code>"

        text += f"{index}. {mention}\n"
        keyboard.append(
            [{"text": f"❌ Cabut Akses ({uid})", "callback_data": f"del_acc_{uid}", "style": "danger", "emoji": 5465665476971471368}]
        )

    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await event.respond(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^del_acc_"))
async def delete_access_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if sender.id != ctx.owner_id:
        return

    payload = event.data.decode("utf-8")
    target_id = int(payload.split("_")[-1])

    await ctx.db.removeVars(target_id, "user_expiry_date")
    await event.answer(f"Akses untuk {target_id} telah dicabut.", alert=True)

    user_ids = await ctx.db.getListVars(client.uid, "user_ids") or []
    access_users = [
        uid for uid in user_ids if await ctx.db.getVars(uid, "user_expiry_date")
    ]

    if not access_users:
        return await event.edit(
            "Tidak ada pengguna yang memiliki akses aktif saat ini."
        )

    text = f"{em.key} <b>Daftar Pengguna Berakses</b>\n\n"
    keyboard = []

    for index, uid in enumerate(access_users, 1):
        try:
            user_obj = await client.get_entity(uid)
            mention = client.ns.telegram.arg.getMention(user_obj)
        except Exception:
            mention = f"ID: <code>{uid}</code>"

        text += f"{index}. {mention}\n"
        keyboard.append(
            [{"text": f"❌ Cabut Akses ({uid})", "callback_data": f"del_acc_{uid}", "style": "danger", "emoji": 5465665476971471368}]
        )

    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await event.edit(text, buttons=btn, parse_mode="html")
