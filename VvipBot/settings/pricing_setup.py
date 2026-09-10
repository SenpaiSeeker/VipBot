import asyncio
import uuid

from pyrogram import filters

from .. import command, ctx, is_bot_owner, listen

ERROR_MESSAGES = {
    "settings.setup_vvip.err_must_be_number": "**Input Tidak Valid!** Nilai harus berupa angka.",
    "settings.setup_vvip.err_must_be_chat_id": "**Input Tidak Valid!** Format Chat ID salah.",
}


def _back_layout(client):
    return [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]


async def _reply(client, callback_query, text, btn):
    if callback_query.message.photo:
        return await callback_query.edit_message_caption(text, reply_markup=btn)
    return await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^set_start_photo$"),
    handler_type="callback",
)
async def set_start_photo_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    back_btn = client.ns.telegram.button.build_button_grid(_back_layout(client))
    try:
        ask_msg = await client.ask(
            chat_id,
            "Kirim foto baru untuk menyambut user.\n\nKetik `/batal` untuk membatalkan.",
            timeout=120,
        )
        if ask_msg.text:
            if ask_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if ask_msg.text.lower() == "/empty":
                await ctx.db.removeVars(client.me.id, "start_photo_id")
                return await client.send_message(
                    chat_id,
                    f"{client.ns.emoji.white_check_mark} **Sukses!** Foto /start telah dihapus.",
                    reply_markup=back_btn,
                )
        if not ask_msg.photo:
            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.cross_mark} **Gagal:** Pesan bukan foto.",
                reply_markup=back_btn,
            )

        photo_id = ask_msg.photo.sizes[-1].file_id
        await ctx.db.setVars(client.me.id, "start_photo_id", photo_id)
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} **Sukses!** Foto /start berhasil diperbarui.",
            reply_markup=back_btn,
        )
    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
            reply_markup=back_btn,
        )


@command(
    lambda ctx: filters.regex("^set_start_text$"),
    handler_type="callback",
)
async def set_start_text_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    back_btn = client.ns.telegram.button.build_button_grid(_back_layout(client))
    try:
        prompt = (
            f"**{client.ns.emoji.writing_hand} Atur Teks Start**\n\n"
            "Silakan kirim teks baru untuk pesan /start. Anda dapat menggunakan variabel "
            "`{{mention}}` untuk menyapa pengguna.\n\n"
            "Ketik `/empty` untuk menghapus teks kustom dan kembali ke default.\n\n"
            "Ketik `/batal` untuk membatalkan."
        )
        ask_text_msg = await client.ask(chat_id, prompt, timeout=600)

        if not ask_text_msg.text:
            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.cross_mark} **Gagal:** Pesan bukan teks.",
                reply_markup=back_btn,
            )
        if ask_text_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        if ask_text_msg.text.lower() == "/empty":
            await ctx.db.removeVars(client.me.id, "start_text_template")
            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.white_check_mark} **Sukses!** Teks /start telah dihapus.",
                reply_markup=back_btn,
            )

        await ctx.db.setVars(
            client.me.id,
            "start_text_template",
            ask_text_msg.text.markdown,
        )
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} **Sukses!** Teks /start berhasil diperbarui.",
            reply_markup=back_btn,
        )
    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
            reply_markup=back_btn,
        )


@command(
    lambda ctx: filters.regex("^check_vvip_status$"),
    handler_type="callback",
)
async def check_vvip_status_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    chat_id = callback_query.message.chat.id
    await callback_query.message.delete()

    status_msg = await client.send_message(
        chat_id,
        f"{client.ns.emoji.hourglass} Sedang Memeriksa Status Grup...\nMohon tunggu, proses ini mungkin memakan waktu.",
    )
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    if not vvip_list:
        return await status_msg.edit(
            f"{client.ns.emoji.cross_mark} Belum ada data VVIP."
        )

    report_text = f"{client.ns.emoji.mag} Laporan Status Grup VVIP\n\n"
    for item in vvip_list:
        chat_id_target = item.get("chat_id_normal")
        name = item.get("name")
        try:
            chat = await client.get_chat(chat_id_target)
            if hasattr(chat, "restrictions") and chat.restrictions:
                restriction = chat.restrictions[0]
                reason_text = f"{restriction.reason}: {restriction.text}"
                report_text += (
                    f"{client.ns.emoji.folder} Nama: {name}\n"
                    f"{client.ns.emoji.bulb} Grup: {chat.title}\n"
                    f"{client.ns.emoji.cross_mark} STATUS: BANNED/DIBATASI\n"
                    f"{client.ns.emoji.pencil} Alasan: {reason_text}\n\n"
                )
            else:
                link = chat.invite_link or "N/A"
                report_text += (
                    f"{client.ns.emoji.folder} Nama: {name}\n"
                    f"{client.ns.emoji.bulb} Grup: {chat.title}\n"
                    f"{client.ns.emoji.link} Link: {link}\n"
                    f"{client.ns.emoji.white_check_mark} Status: Aman\n\n"
                )
        except Exception:
            report_text += (
                f"{client.ns.emoji.folder} Nama: {name}\n"
                f"{client.ns.emoji.cross_mark} Error: Tidak dapat mengakses grup (ID: {chat_id_target}). Pastikan bot adalah admin.\n\n"
            )

        if len(report_text) > 3500:
            await client.send_message(chat_id, report_text)
            report_text = ""

    if report_text:
        await client.send_message(chat_id, report_text)

    btn = client.ns.telegram.button.build_button_grid(_back_layout(client))
    await status_msg.delete()
    await client.send_message(
        chat_id,
        f"{client.ns.emoji.white_check_mark} Pemeriksaan Selesai.",
        reply_markup=btn,
    )


def _make_validator():
    def validate(msg, check_func, err_msg_key):
        if msg.text and msg.text.lower() == "/batal":
            raise listen.UserCancelled
        if not check_func(msg.text):
            raise ValueError(
                ERROR_MESSAGES.get(err_msg_key, "**Input tidak valid.**")
            )
        return msg.text

    return validate


def _is_digit(t):
    return t.isdigit()


def _is_chatid(t):
    return t.lstrip("-").isdigit()


@command(
    lambda ctx: filters.regex("^setup_listvvip$"),
    handler_type="callback",
)
async def setup_listvvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    try:
        def ask(text):
            return client.ask(
                chat_id,
                f"{text}\n\nKetik `/batal` untuk membatalkan.",
                timeout=600,
            )

        validate = _make_validator()

        vvip_data = {}
        vvip_data["name"] = validate(
            await ask(
                f"**{client.ns.emoji.pencil} Langkah 1/8: Nama Kategori**\nContoh: `VVIP Bulanan`"
            ),
            lambda t: True,
            "",
        )
        vvip_data["price"] = int(
            validate(
                await ask(
                    f"**{client.ns.emoji.money_bag} Langkah 2/8: Harga Normal**\nContoh: `50000`"
                ),
                _is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )
        vvip_data["duration"] = int(
            validate(
                await ask(
                    f"**{client.ns.emoji.hourglass} Langkah 3/8: Durasi Keanggotaan (Hari)**\nKirim `0` untuk akses permanen."
                ),
                _is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )
        vvip_data["chat_id_normal"] = int(
            validate(
                await ask(
                    f"**{client.ns.emoji.id_card} Langkah 4/8: Chat ID Grup Normal**\nContoh: `-100123456789`."
                ),
                _is_chatid,
                "settings.setup_vvip.err_must_be_chat_id",
            )
        )
        vvip_data["promo_price"] = int(
            validate(
                await ask(
                    f"**{client.ns.emoji.party_popper} Langkah 5/8: Harga Promo**\nKirim `0` jika tidak ada harga promo."
                ),
                _is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )

        if vvip_data["promo_price"] > 0:
            vvip_data["chat_id_promo"] = int(
                validate(
                    await ask(
                        f"**{client.ns.emoji.id_card} Langkah 6/8: Chat ID Grup Promo**\nDiisi jika Harga Promo > 0."
                    ),
                    _is_chatid,
                    "settings.setup_vvip.err_must_be_chat_id",
                )
            )
            promo_text_msg = await client.ask(
                chat_id,
                (
                    f"**{client.ns.emoji.pencil} Langkah 7/8: Teks Deskripsi Promo**\n"
                    "Gunakan `{{name}}` dan `{{promo_price}}`.\n\n"
                    "Ketik `/skip` untuk menggunakan teks default.\n\n"
                    "Ketik `/batal` untuk membatalkan."
                ),
                timeout=600,
            )
            if promo_text_msg.text and promo_text_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            vvip_data["promo_text"] = (
                "" if promo_text_msg.text.lower() == "/skip" else promo_text_msg.text
            )
        else:
            vvip_data["chat_id_promo"], vvip_data["promo_text"] = 0, ""

        normal_text_msg = await client.ask(
            chat_id,
            (
                f"**{client.ns.emoji.pencil} Langkah 8/8: Teks Deskripsi Normal**\n"
                "Gunakan `{{name}}` and `{{price}}`.\n\n"
                "Ketik `/skip` untuk menggunakan teks default.\n\n"
                "Ketik `/batal` untuk membatalkan."
            ),
            timeout=600,
        )
        if normal_text_msg.text and normal_text_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        vvip_data["normal_text"] = (
            "" if normal_text_msg.text.lower() == "/skip" else normal_text_msg.text
        )

        await ctx.db.setListVars(client.me.id, "list_vvip", vvip_data)
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} **Sukses!**\nPaket VVIP **{vvip_data['name']}** berhasil ditambahkan.",
        )
    except listen.UserCancelled:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} Setup paket VVIP dibatalkan.",
        )
    except (asyncio.TimeoutError, ValueError) as e:
        await client.send_message(
            chat_id,
            f"**Input Tidak Valid / Timeout**\nProses dibatalkan.\n`{e}`",
        )


async def _build_item_selector(
    client,
    callback_query,
    key_attr,
    action,
    callback_prefix,
    emoji_id,
    header_emoji,
    header_text,
    body_text,
    empty_text,
):
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    back_row = _back_layout(client)[0]

    if not vvip_list:
        text = empty_text
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await _reply(client, callback_query, text, btn)

    if not hasattr(ctx, key_attr):
        setattr(ctx, key_attr, {})

    layout = []
    button_row = []
    mapping = getattr(ctx, key_attr)
    for item in vvip_list:
        name = item.get("name", "Tanpa Nama")
        item_id = uuid.uuid4().hex[:8]
        mapping[item_id] = name
        button_row.append(
            {
                "text": f"{action} {name}",
                "callback_data": f"{callback_prefix} {item_id}",
                "style": "red" if action.startswith("🗑") else "blue",
                "emoji": client.ns.emoji.id(emoji_id),
            }
        )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []
    if button_row:
        layout.append(button_row)
    layout.append(back_row)

    text = f"**{header_emoji} {header_text}**\n\n{body_text}"
    btn = client.ns.telegram.button.build_button_grid(layout)
    await _reply(client, callback_query, text, btn)


@command(
    lambda ctx: filters.regex("^delete_listvvip$"),
    handler_type="callback",
)
async def delete_listvvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    await _build_item_selector(
        client,
        callback_query,
        "vip_list",
        "🗑️ Hapus",
        "delete_vvip",
        "minus",
        client.ns.emoji.minus,
        "Hapus Paket VVIP",
        "Pilih paket VVIP yang ingin Anda hapus.",
        f"{client.ns.emoji.white_check_mark} Tidak ada paket VVIP untuk dihapus.",
    )


@command(
    lambda ctx: filters.regex("^delete_vvip\\s(.+)"),
    handler_type="callback",
)
async def confirm_delete_vvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    _, item_id = callback_query.data.split(" ", 1)
    if not hasattr(ctx, "vip_list") or item_id not in ctx.vip_list:
        return await callback_query.answer(
            "Sesi tidak ditemukan atau kedaluwarsa.",
            show_alert=True,
        )

    name = ctx.vip_list[item_id]
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    item_to_remove = next(
        (item for item in vvip_list if item.get("name") == name),
        None,
    )
    if item_to_remove:
        await ctx.db.removeListVars(client.me.id, "list_vvip", item_to_remove)
        await callback_query.answer("Kategori berhasil dihapus.", show_alert=True)

    await delete_listvvip(client, callback_query)


@command(
    lambda ctx: filters.regex("^edit_price_listvvip$"),
    handler_type="callback",
)
async def edit_price_listvvip_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    await _build_item_selector(
        client,
        callback_query,
        "vip_list_edit",
        "✏️ Edit",
        "edit_vvip_price",
        "pencil",
        client.ns.emoji.pencil,
        "Edit Harga VVIP",
        "Pilih paket VVIP yang ingin Anda ubah harganya.",
        f"{client.ns.emoji.cross_mark} Belum ada paket VVIP.",
    )


@command(
    lambda ctx: filters.regex("^edit_vvip_price\\s(.+)"),
    handler_type="callback",
)
async def edit_vvip_price_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    _, item_id = callback_query.data.split(" ", 1)

    if not hasattr(ctx, "vip_list_edit") or item_id not in ctx.vip_list_edit:
        return await callback_query.answer(
            "Sesi tidak ditemukan atau kedaluwarsa.",
            show_alert=True,
        )

    name = ctx.vip_list_edit[item_id]
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    old_item = next(
        (item for item in vvip_list if item.get("name") == name),
        None,
    )
    if not old_item:
        return await callback_query.answer(
            "Paket VVIP tidak ditemukan.",
            show_alert=True,
        )

    await callback_query.message.delete()
    try:
        def ask(text):
            return client.ask(
                chat_id,
                f"{text}\n\nKetik `/batal` untuk membatalkan.",
                timeout=300,
            )

        new_price_msg = await ask(
            f"**{client.ns.emoji.money_bag} Masukkan Harga Normal Baru**\nContoh: `50000`\n\nHarga sebelumnya: `{old_item.get('price', 0)}`"
        )
        if new_price_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        if not new_price_msg.text.isdigit():
            raise ValueError
        new_price = int(new_price_msg.text)

        new_promo_msg = await ask(
            f"**{client.ns.emoji.party_popper} Masukkan Harga Promo Baru**\nContoh: `25000` atau `0`.\n\nHarga sebelumnya: `{old_item.get('promo_price', 0)}`"
        )
        if new_promo_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        if not new_promo_msg.text.isdigit():
            raise ValueError
        new_promo = int(new_promo_msg.text)

        await ctx.db.removeListVars(client.me.id, "list_vvip", old_item)
        old_item["price"] = new_price
        old_item["promo_price"] = new_promo
        await ctx.db.setListVars(client.me.id, "list_vvip", old_item)
        del ctx.vip_list_edit[item_id]

        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} **Sukses!**\nHarga paket VVIP **{name}** berhasil diubah.",
        )
    except listen.UserCancelled:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} Perubahan dibatalkan.",
        )
    except (asyncio.TimeoutError, ValueError) as e:
        await client.send_message(
            chat_id,
            f"**Input Tidak Valid / Timeout**\nProses dibatalkan.\n`{e}`",
        )