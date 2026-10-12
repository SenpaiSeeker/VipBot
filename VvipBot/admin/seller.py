import pyrogram

from helpers import parse_dt

from .. import *


@command(lambda ctx: filters.command("akses"))
@seller_only
async def access_command_handler(client, message):
    user_id_target, _ = await client.ns.telegram.arg.getReasonAndId(message)
    if not user_id_target:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Gunakan', '`/akses <user_id atau @username>`']])}"
                )
            )
        )
    try:
        target_user = await client.get_users(user_id_target)
        has_access = False
        expiry = parse_dt(await ctx.db.getVars(target_user.id, "user_expiry_date"))
        if expiry and expiry > datetime.now(timezone.utc):
            has_access = True
        status_text = (
            f"{client.ns.emoji.md('white_check_mark')} Memiliki Akses"
            if has_access
            else f"{client.ns.emoji.md('cross_mark')} Tidak Memiliki Akses"
        )
        text = (
            f"{client.ns.emoji.md('key')} **Kelola Akses Pembuatan Bot**\n\n"
            f"| Info | Detail |\n"
            f"| :--- | :--- |\n"
            f"| Pengguna | {client.ns.telegram.arg.getMention(target_user, md=True)} |\n"
            f"| ID | `{target_user.id}` |\n"
            f"| Status | {status_text} |\n\n"
            f"Pilih tindakan untuk pengguna ini:"
        )
        layout = [
            [
                {
                    "text": "✅ Beri Akses",
                    "callback_data": f"give_access_{target_user.id}",
                    "style": "green",
                    "emoji": client.ns.emoji.id("white_check_mark"),
                },
                {
                    "text": "❌ Cabut Akses",
                    "callback_data": f"revoke_access_{target_user.id}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("cross_mark"),
                },
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await message.reply_rich(
            pyrogram.types.InputRichMessage(markdown=text), reply_markup=btn
        )
    except Exception as e:
        await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal Memproses**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal'], ['Error', f'`{e}`']])}"
                )
            )
        )


@command(lambda ctx: filters.regex("^give_access_(\\d+)"), handler_type="callback")
@seller_only
async def give_access_callback(client, callback_query):
    target_id = int(callback_query.data.split("_")[-1])
    layout = [
        [
            {
                "text": f"{m} Bulan",
                "callback_data": f"do_give_{target_id}_{m}",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            }
            for m in [1, 3, 6, 12]
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": "close_panel",
                "style": "red",
                "emoji": client.ns.emoji.id("cross_mark"),
            }
        ],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('hourglass')} **Pilih Durasi Akses**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Tujuan', 'Berikan akses premium ke pengguna'], ['Opsi', 'Pilih salah satu durasi di bawah ini']])}"
            )
        ),
        reply_markup=btn,
    )


@command(lambda ctx: filters.regex("^do_give_(\\d+)_(\\d+)"), handler_type="callback")
@seller_only
async def do_give_access_callback(client, callback_query):
    _, _, target_id_str, months_str = callback_query.data.split("_")
    target_id = int(target_id_str)
    months_to_add = int(months_str)
    try:
        target_user = await client.get_users(target_id)
        current_expiry = parse_dt(
            await ctx.db.getVars(target_id, "user_expiry_date")
        ) or datetime.now(timezone.utc)
        start_date = max(current_expiry, datetime.now(timezone.utc))
        new_expiry_date = start_date + timedelta(days=30 * months_to_add)
        await ctx.db.setVars(target_id, "user_expiry_date", new_expiry_date.isoformat())
        expiry_in_jakarta = new_expiry_date.astimezone(ZoneInfo("Asia/Jakarta"))

        mention_str = client.ns.telegram.arg.getMention(target_user, md=True)
        formatted_jakarta_date = expiry_in_jakarta.strftime("%d %B %Y, %H:%M %Z")
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('white_check_mark')} **Akses Diberikan!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Pengguna', f'{mention_str}'], ['Akses', f'Membuat bot selama **{months_to_add} bulan**'], ['Berlaku hingga', f'`{formatted_jakarta_date}`']])}"
            )
        )
        await callback_query.answer(
            "<emoji id=6296367896398399651>✅</emoji> Akses berhasil diberikan kepada {target_id}".format(
                target_id=target_id
            )
        )
    except Exception as e:
        await callback_query.answer(f"Gagal memproses. Error: `{e}`", show_alert=True)


@command(lambda ctx: filters.regex("^revoke_access_(\\d+)"), handler_type="callback")
@seller_only
async def revoke_access_callback(client, callback_query):
    target_id = int(callback_query.data.split("_")[-1])
    try:
        target_user = await client.get_users(target_id)
        mention = client.ns.telegram.arg.getMention(target_user, md=True)
        await ctx.db.removeVars(target_id, "user_expiry_date")
        await callback_query.answer(
            "<emoji id=6298671811345254603>❌</emoji> Akses berhasil dicabut dari {target_id}".format(
                target_id=target_id
            )
        )
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Akses Dicabut!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Pengguna', f'{mention}'], ['Status', 'Tidak lagi memiliki hak untuk membuat bot']])}"
            )
        )
    except Exception as e:
        await callback_query.answer(f"Gagal memproses. Error: `{e}`", show_alert=True)


@command(lambda ctx: filters.command("addseller") & filters.user(ctx.owner_id))
async def add_seller_handler(client, message):
    user_id_target, _ = await client.ns.telegram.arg.getReasonAndId(message)
    if not user_id_target:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Pengguna Tidak Ditemukan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Pengguna tidak ditemukan'], ['Saran', 'Pastikan ID/Username benar atau balas pesan pengguna']])}"
                )
            )
        )
    try:
        target_user = await client.get_users(user_id_target)
        seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
        if target_user.id in seller_list:
            return await message.reply_rich(
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Sudah Terdaftar**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['User', f'`{target_user.id}`'], ['Status', 'Sudah terdaftar sebagai seller']])}"
                    )
                )
            )
        await ctx.db.setListVars(ctx.owner_id, "seller_id_list", target_user.id)
        user_mention = client.ns.telegram.arg.getMention(target_user, md=True)
        await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Seller Ditambahkan!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Seller', f'{user_mention}'], ['Status', 'Berhasil ditambahkan sebagai seller']])}"
                )
            )
        )
    except Exception as e:
        await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal'], ['Error', f'`{e}`']])}"
                )
            )
        )


@command(lambda ctx: filters.command("listseller") & filters.user(ctx.owner_id))
async def list_seller_handler(client, message):
    seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
    if not seller_list:
        empty_rows = [
            ["Jumlah Seller", "`0`"],
            ["Status", "Belum ada seller terdaftar"],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('bust_in_silhouette')} **Daftar Seller Aktif**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], empty_rows)}"
                )
            )
        )
    text = (
        f"**{client.ns.emoji.md('bust_in_silhouette')} Daftar Seller Aktif**\n\n"
        f"| No | Seller |\n"
        f"| :---: | :--- |\n"
    )
    keyboard = []
    for index, user_id in enumerate(seller_list, 1):
        try:
            user_obj = await client.get_users(user_id)
            mention = client.ns.telegram.arg.getMention(user_obj, md=True)
        except Exception:
            mention = f"ID: `{user_id}`"
        text += f"| {index} | {mention} |\n"
        keyboard.append(
            [
                {
                    "text": f"Hapus Seller 🗑️ ({user_id})",
                    "callback_data": f"del_sell_{user_id}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await message.reply_rich(
        pyrogram.types.InputRichMessage(markdown=text), reply_markup=btn
    )


@command(lambda ctx: filters.regex("^del_sell_(\\d+)"), handler_type="callback")
async def delete_seller_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    target_id = int(callback_query.matches[0].group(1))
    await ctx.db.removeListVars(ctx.owner_id, "seller_id_list", target_id)
    await callback_query.answer(
        "Seller `{user_id}` berhasil dihapus.".format(user_id=target_id),
        show_alert=True,
    )
    seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
    if not seller_list:
        empty_rows = [
            ["Jumlah Seller", "`0`"],
            ["Status", "Belum ada seller terdaftar"],
        ]
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('bust_in_silhouette')} **Daftar Seller Aktif**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], empty_rows)}"
                )
            )
        )
        return
    text = (
        f"**{client.ns.emoji.md('bust_in_silhouette')} Daftar Seller Aktif**\n\n"
        f"| No | Seller |\n"
        f"| :---: | :--- |\n"
    )
    keyboard = []
    for index, user_id in enumerate(seller_list, 1):
        try:
            user_obj = await client.get_users(user_id)
            mention = client.ns.telegram.arg.getMention(user_obj, md=True)
        except Exception:
            mention = f"ID: `{user_id}`"
        text += f"| {index} | {mention} |\n"
        keyboard.append(
            [
                {
                    "text": f"Hapus Seller 🗑️ ({user_id})",
                    "callback_data": f"del_sell_{user_id}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text), reply_markup=btn
    )


@command(lambda ctx: filters.command("listakses") & filters.user(ctx.owner_id))
async def list_akses_handler(client, message):
    user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
    now = datetime.now(timezone.utc)
    access_users = []
    for uid in user_ids:
        expiry = parse_dt(await ctx.db.getVars(uid, "user_expiry_date"))
        if expiry and expiry > now:
            access_users.append(uid)
    if not access_users:
        empty_rows = [
            ["Jumlah Pengguna", "`0`"],
            ["Status", "Tidak ada pengguna dengan akses aktif"],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('key')} **Daftar Pengguna Berakses**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], empty_rows)}"
                )
            )
        )
    text = (
        f"**{client.ns.emoji.md('key')} Daftar Pengguna Berakses**\n\n"
        f"| No | Pengguna |\n"
        f"| :---: | :--- |\n"
    )
    keyboard = []
    for index, uid in enumerate(access_users, 1):
        try:
            user_obj = await client.get_users(uid)
            mention = client.ns.telegram.arg.getMention(user_obj, md=True)
        except Exception:
            mention = f"ID: `{uid}`"
        text += f"| {index} | {mention} |\n"
        keyboard.append(
            [
                {
                    "text": f"Cabut Akses 🚫 ({uid})",
                    "callback_data": f"del_acc_{uid}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await message.reply_rich(
        pyrogram.types.InputRichMessage(markdown=text), reply_markup=btn
    )


@command(lambda ctx: filters.regex("^del_acc_(\\d+)"), handler_type="callback")
async def delete_access_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    target_id = int(callback_query.matches[0].group(1))
    await ctx.db.removeVars(target_id, "user_expiry_date")
    await callback_query.answer(
        "Akses untuk `{user_id}` telah dicabut.".format(user_id=target_id),
        show_alert=True,
    )
    user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
    now = datetime.now(timezone.utc)
    access_users = []
    for uid in user_ids:
        expiry = parse_dt(await ctx.db.getVars(uid, "user_expiry_date"))
        if expiry and expiry > now:
            access_users.append(uid)
    if not access_users:
        empty_rows = [
            ["Jumlah Pengguna", "`0`"],
            ["Status", "Tidak ada pengguna dengan akses aktif"],
        ]
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('key')} **Daftar Pengguna Berakses**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], empty_rows)}"
                )
            )
        )
        return
    text = (
        f"**{client.ns.emoji.md('key')} Daftar Pengguna Berakses**\n\n"
        f"| No | Pengguna |\n"
        f"| :---: | :--- |\n"
    )
    keyboard = []
    for index, uid in enumerate(access_users, 1):
        try:
            user_obj = await client.get_users(uid)
            mention = client.ns.telegram.arg.getMention(user_obj, md=True)
        except Exception:
            mention = f"ID: `{uid}`"
        text += f"| {index} | {mention} |\n"
        keyboard.append(
            [
                {
                    "text": f"Cabut Akses 🚫 ({uid})",
                    "callback_data": f"del_acc_{uid}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text), reply_markup=btn
    )
