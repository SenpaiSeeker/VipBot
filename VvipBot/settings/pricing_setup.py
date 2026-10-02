import asyncio
import uuid

import pyrogram
from pyrogram import filters

from .. import command, ctx, is_bot_owner, listen
from ..core import DEFAULT_START_PHOTO


@command(
    lambda ctx: filters.regex("^set_start_photo$"),
    handler_type="callback",
)
async def set_start_photo_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    layout = [
        [
            {
                "text": "🖼️ Gunakan Foto Default",
                "callback_data": "set_default_start_photo",
                "style": "blue",
                "emoji": client.ns.emoji.id("frame"),
            },
            {
                "text": "📤 Kirim Foto Baru",
                "callback_data": "ask_start_photo",
                "style": "green",
                "emoji": client.ns.emoji.id("inbox_tray"),
            },
        ],
        [
            {
                "text": "🗑️ Hapus Foto (Teks Saja)",
                "callback_data": "clear_start_photo",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ],
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await client.send_rich_message(
        chat_id,
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('frame')} **Atur Foto Start**\n\n"
                f"Silakan pilih opsi di bawah ini untuk mengubah foto sambutan "
                f"`/start`.\n\n"
                f"{client.ns.emoji.md('warning')} **Perhatian:**\n"
                f"Semakin besar ukuran foto, maka semakin lama juga respon "
                f"`/start`.\n"
                f"Gunakan foto berukuran kecil agar bot tetap cepat merespons.\n\n"
                f"Jika foto tidak diatur, maka `/start` hanya akan "
                f"mengirim **teks sambutan saja**."
            )
        ),
        reply_markup=btn,
    )


@command(
    lambda ctx: filters.regex("^set_default_start_photo$"),
    handler_type="callback",
)
async def set_default_start_photo_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await ctx.db.setVars(client.me.id, "start_photo_id", DEFAULT_START_PHOTO)

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.message.delete()

    await client.send_rich_message(
        chat_id,
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n"
                f"Foto `/start` diatur ke **foto default**."
            )
        ),
        reply_markup=btn,
    )


@command(
    lambda ctx: filters.regex("^clear_start_photo$"),
    handler_type="callback",
)
async def clear_start_photo_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await ctx.db.removeVars(client.me.id, "start_photo_id")

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.message.delete()

    await client.send_rich_message(
        chat_id,
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n"
                f"Foto `/start` telah dihapus. Sekarang `/start` "
                f"hanya akan mengirim **teks sambutan**."
            )
        ),
        reply_markup=btn,
    )


@command(
    lambda ctx: filters.regex("^ask_start_photo$"),
    handler_type="callback",
)
async def ask_start_photo_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        prompt = (
            f"{client.ns.emoji.md('frame')} **Kirim Foto Baru**\n\n"
            f"Silakan kirim foto baru untuk menyambut user.\n\n"
            f"{client.ns.emoji.md('warning')} **Perhatian:** Semakin besar ukuran foto, "
            f"maka semakin lama juga respon `/start`.\n\n"
            f"Ketik `/batal` untuk membatalkan.\n"
            f"Ketik `/empty` untuk menghapus foto dan hanya mengirim teks."
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=120)

        if ask_msg.text:
            if ask_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if ask_msg.text.lower() == "/empty":
                await ctx.db.removeVars(client.me.id, "start_photo_id")

                return await client.send_rich_message(
                    chat_id,
                    pyrogram.types.InputRichMessage(
                        markdown=(
                            f"{client.ns.emoji.md('white_check_mark')} **Sukses!** "
                            f"Foto /start telah dihapus."
                        )
                    ),
                    reply_markup=back_btn,
                )

        if not ask_msg.photo:
            return await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=f"{client.ns.emoji.md('cross_mark')} **Gagal:** Pesan bukan foto."
                ),
                reply_markup=back_btn,
            )

        photo_id = ask_msg.photo.sizes[-1].file_id
        await ctx.db.setVars(client.me.id, "start_photo_id", photo_id)

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Sukses!** "
                    f"Foto /start berhasil diperbarui."
                )
            ),
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Proses Dibatalkan**"
            ),
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

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        prompt = (
            f"{client.ns.emoji.md('writing_hand')} **Atur Teks Start**\n\n"
            f"Silakan kirim teks baru untuk pesan /start. Anda dapat menggunakan "
            f"variabel `{{mention}}` untuk menyapa pengguna.\n\n"
            f"Ketik `/empty` untuk menghapus teks kustom dan kembali ke default."
            f"\n\n"
            f"Ketik `/batal` untuk membatalkan."
        )
        ask_text_msg = await client.ask(chat_id, prompt, timeout=600)

        if not ask_text_msg.text:
            return await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=f"{client.ns.emoji.md('cross_mark')} **Gagal:** Pesan bukan teks."
                ),
                reply_markup=back_btn,
            )

        if ask_text_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        if ask_text_msg.text.lower() == "/empty":
            await ctx.db.removeVars(client.me.id, "start_text_template")

            return await client.send_rich_message(
                chat_id,
                    pyrogram.types.InputRichMessage(
                        markdown=(
                            f"{client.ns.emoji.md('white_check_mark')} **Sukses!** "
                            f"Teks /start telah dihapus."
                        )
                    ),
                reply_markup=back_btn,
            )

        await ctx.db.setVars(
            client.me.id,
            "start_text_template",
            ask_text_msg.text.markdown,
        )

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Sukses!** "
                    f"Teks /start berhasil diperbarui."
                )
            ),
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Proses Dibatalkan**"
            ),
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

    status_msg = await client.send_rich_message(
        chat_id,
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('hourglass')} Sedang Memeriksa Status Grup...\n"
                f"Mohon tunggu, proses ini mungkin memakan waktu."
            )
        ),
    )

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    if not vvip_list:
        empty_rows = [
            ["Jumlah Paket", "`0`"],
            ["Status", "Belum ada data VVIP"],
        ]
        return await status_msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Laporan Status Grup VVIP**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], empty_rows)}"
                )
            )
        )

    report_header = f"{client.ns.emoji.md('mag')} **Laporan Status Grup VVIP**\n\n"
    report_headers = ["Nama", "Grup", "Status", "Keterangan"]
    report_rows = []

    def build_report(rows):
        return report_header + client.ns.table.md(report_headers, rows)

    for item in vvip_list:
        chat_id_target = item.get("chat_id_normal")
        name = item.get("name")

        try:
            chat = await client.get_chat(chat_id_target)

            if hasattr(chat, "restrictions") and chat.restrictions:
                restriction = chat.restrictions[0]
                reason_text = f"{restriction.reason}: {restriction.text}"
                report_rows.append([name, chat.title, "BANNED/DIBATASI", reason_text])
            else:
                link = chat.invite_link or "N/A"
                link_cell = f"[Buka Grup]({link})" if link != "N/A" else link
                report_rows.append([name, chat.title, "Aman", link_cell])
        except Exception:
            report_rows.append(
                [
                    name,
                    chat_id_target,
                    "Error",
                    "Tidak dapat mengakses grup. Pastikan bot adalah admin.",
                ]
            )

        if len(build_report(report_rows)) > 3500:
            await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(markdown=build_report(report_rows)),
            )
            report_rows = []

    if report_rows:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(markdown=build_report(report_rows)),
        )

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await status_msg.delete()

    await client.send_rich_message(
        chat_id,
        pyrogram.types.InputRichMessage(
            markdown=f"{client.ns.emoji.md('white_check_mark')} Pemeriksaan Selesai."
        ),
        reply_markup=btn,
    )


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

        def validate(msg, check_func, err_msg_key):
            if msg.text and msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if not check_func(msg.text):
                errors = {
                    "settings.setup_vvip.err_must_be_number": "**Input Tidak Valid!** Nilai harus berupa angka.",
                    "settings.setup_vvip.err_must_be_chat_id": "**Input Tidak Valid!** Format Chat ID salah.",
                }
                raise ValueError(
                    errors.get(
                        err_msg_key,
                        "**Input tidak valid.**",
                    )
                )
            return msg.text

        def is_digit(t):
            return t.isdigit()

        def is_chatid(t):
            return t.lstrip("-").isdigit()

        vvip_data = {}

        vvip_data["name"] = validate(
            await ask(
                f"{client.ns.emoji.md('pencil')} **Langkah 1/8: Nama Kategori**\nContoh: `VVIP Bulanan`"
            ),
            lambda t: True,
            "",
        )

        vvip_data["price"] = int(
            validate(
                await ask(
                    f"{client.ns.emoji.md('money_bag')} **Langkah 2/8: Harga Normal**\nContoh: `50000`"
                ),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )

        vvip_data["duration"] = int(
            validate(
                await ask(
                    f"{client.ns.emoji.md('hourglass')} **Langkah 3/8: Durasi Keanggotaan (Hari)**\nKirim `0` untuk akses permanen."
                ),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )

        vvip_data["chat_id_normal"] = int(
            validate(
                await ask(
                    f"{client.ns.emoji.md('id_card')} **Langkah 4/8: Chat ID Grup Normal**\nContoh: `-100123456789`."
                ),
                is_chatid,
                "settings.setup_vvip.err_must_be_chat_id",
            )
        )

        vvip_data["promo_price"] = int(
            validate(
                await ask(
                    f"{client.ns.emoji.md('party_popper')} **Langkah 5/8: Harga Promo**\nKirim `0` jika tidak ada harga promo."
                ),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )

        if vvip_data["promo_price"] > 0:
            vvip_data["chat_id_promo"] = int(
                validate(
                    await ask(
                        f"{client.ns.emoji.md('id_card')} **Langkah 6/8: Chat ID Grup Promo**\nDiisi jika Harga Promo > 0."
                    ),
                    is_chatid,
                    "settings.setup_vvip.err_must_be_chat_id",
                )
            )

            prompt_promo = (
                f"{client.ns.emoji.md('pencil')} **Langkah 7/8: Teks Deskripsi Promo**\n"
                f"Gunakan `{{name}}` dan `{{promo_price}}`.\n\n"
                f"Ketik `/skip` untuk menggunakan teks default.\n\n"
                f"Ketik `/batal` untuk membatalkan."
            )
            promo_text_msg = await client.ask(chat_id, prompt_promo, timeout=600)

            if promo_text_msg.text and promo_text_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            vvip_data["promo_text"] = (
                "" if promo_text_msg.text.lower() == "/skip" else promo_text_msg.text
            )
        else:
            (
                vvip_data["chat_id_promo"],
                vvip_data["promo_text"],
            ) = (0, "")

        prompt_normal = (
            f"{client.ns.emoji.md('pencil')} **Langkah 8/8: Teks Deskripsi Normal**\n"
            f"Gunakan `{{name}}` and `{{price}}`.\n\n"
            f"Ketik `/skip` untuk menggunakan teks default.\n\n"
            f"Ketik `/batal` untuk membatalkan."
        )
        normal_text_msg = await client.ask(chat_id, prompt_normal, timeout=600)

        if normal_text_msg.text and normal_text_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        vvip_data["normal_text"] = (
            "" if normal_text_msg.text.lower() == "/skip" else normal_text_msg.text
        )

        await ctx.db.setListVars(client.me.id, "list_vvip", vvip_data)

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\nPaket VVIP **{vvip_data['name']}** berhasil ditambahkan."
            ),
        )

    except listen.UserCancelled:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} Setup paket VVIP dibatalkan."
            ),
        )
    except (asyncio.TimeoutError, ValueError) as e:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Input Tidak Valid / Timeout**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Input tidak valid atau timeout'], ['Tindakan', 'Proses dibatalkan'], ['Error', f'`{e}`']])}"
                )
            ),
        )


@command(
    lambda ctx: filters.regex("^delete_listvvip$"),
    handler_type="callback",
)
async def delete_listvvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    back_row = [
        {
            "text": "• Kembali ke Pengaturan •",
            "callback_data": "settings",
            "style": "blue",
            "emoji": client.ns.emoji.id("back_arrow"),
        }
    ]

    if not vvip_list:
        table = client.ns.table
        empty_rows = [["Jumlah Paket", "`0`"], ["Status", "Tidak ada paket VVIP"]]
        text = (
            f"{client.ns.emoji.md('minus')} **Hapus Paket VVIP**\n\n"
            f"{table.md(['Info', 'Nilai'], empty_rows)}"
        )
        btn = client.ns.telegram.button.build_button_grid([back_row])

        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=btn,
        )

    if not hasattr(ctx, "vip_list"):
        ctx.vip_list = {}

    layout = []
    button_row = []

    for item in vvip_list:
        name = item.get("name", "Tanpa Nama")
        item_id = uuid.uuid4().hex[:8]
        ctx.vip_list[item_id] = item

        button_row.append(
            {
                "text": f"🗑️ Hapus {name}",
                "callback_data": f"delete_vvip {item_id}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []

    if button_row:
        layout.append(button_row)
    layout.append(back_row)

    menu_rows = [
        [f"{client.ns.emoji.md('minus')} Mode", "Hapus Paket VVIP"],
        [f"{client.ns.emoji.md('back_arrow')} Tombol", "Kembali ke Pengaturan"],
        ["Jumlah Paket", f"`{len(vvip_list)}`"],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('minus')} **Hapus Paket VVIP**\n\n"
        f"{table.md(['Info', 'Nilai'], menu_rows)}\n\n"
        f"Pilih paket VVIP yang ingin Anda hapus."
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
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

    name = ctx.vip_list[item_id].get("name", "Tanpa Nama")
    item_to_remove = ctx.vip_list[item_id]

    if item_to_remove:
        await ctx.db.removeListVars(client.me.id, "list_vvip", item_to_remove)
        ctx.vip_list.pop(item_id, None)
        await callback_query.answer("Kategori berhasil dihapus.", show_alert=True)

    await delete_listvvip(client, callback_query)


@command(
    lambda ctx: filters.regex("^edit_price_listvvip$"),
    handler_type="callback",
)
async def edit_price_listvvip_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    back_row = [
        {
            "text": "• Kembali ke Pengaturan •",
            "callback_data": "settings",
            "style": "blue",
            "emoji": client.ns.emoji.id("back_arrow"),
        }
    ]

    if not vvip_list:
        table = client.ns.table
        empty_rows = [["Jumlah Paket", "`0`"], ["Status", "Belum ada paket VVIP"]]
        text = (
            f"{client.ns.emoji.md('pencil')} **Edit Harga VVIP**\n\n"
            f"{table.md(['Info', 'Nilai'], empty_rows)}"
        )
        btn = client.ns.telegram.button.build_button_grid([back_row])

        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=btn,
        )

    if not hasattr(ctx, "vip_list_edit"):
        ctx.vip_list_edit = {}

    layout = []
    button_row = []

    for item in vvip_list:
        name = item.get("name", "Tanpa Nama")
        item_id = uuid.uuid4().hex[:8]
        ctx.vip_list_edit[item_id] = item

        button_row.append(
            {
                "text": f"✏️ Edit {name}",
                "callback_data": f"edit_vvip_price {item_id}",
                "style": "blue",
                "emoji": client.ns.emoji.id("pencil"),
            }
        )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []

    if button_row:
        layout.append(button_row)
    layout.append(back_row)

    menu_rows = [
        [f"{client.ns.emoji.md('pencil')} Mode", "Edit Harga VVIP"],
        [f"{client.ns.emoji.md('back_arrow')} Tombol", "Kembali ke Pengaturan"],
        ["Jumlah Paket", f"`{len(vvip_list)}`"],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('pencil')} **Edit Harga VVIP**\n\n"
        f"{table.md(['Info', 'Nilai'], menu_rows)}\n\n"
        f"Pilih paket VVIP yang ingin Anda ubah harganya."
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
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

    name = ctx.vip_list_edit[item_id].get("name", "Tanpa Nama")
    old_item = ctx.vip_list_edit[item_id]

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    item_index = next(
        (i for i, item in enumerate(vvip_list) if item == old_item),
        None,
    )

    if item_index is None:
        return await callback_query.answer(
            "Paket VVIP tidak ditemukan atau telah berubah.",
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
            f"{client.ns.emoji.md('money_bag')} **Masukkan Harga Normal Baru**\nContoh: `50000`\n\nHarga sebelumnya: `{old_item.get('price', 0)}`"
        )

        if new_price_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        if not new_price_msg.text.isdigit():
            raise ValueError

        new_price = int(new_price_msg.text)

        new_promo_msg = await ask(
            f"{client.ns.emoji.md('party_popper')} **Masukkan Harga Promo Baru**\nContoh: `25000` atau `0`.\n\nHarga sebelumnya: `{old_item.get('promo_price', 0)}`"
        )

        if new_promo_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        if not new_promo_msg.text.isdigit():
            raise ValueError

        new_promo = int(new_promo_msg.text)

        vvip_list[item_index]["price"] = new_price
        vvip_list[item_index]["promo_price"] = new_promo

        await ctx.db.replaceListVars(client.me.id, "list_vvip", vvip_list)
        ctx.vip_list_edit.pop(item_id, None)

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\nHarga paket VVIP **{name}** berhasil diubah."
            ),
        )

    except listen.UserCancelled:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} Perubahan dibatalkan."
            ),
        )
    except (asyncio.TimeoutError, ValueError) as e:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Input Tidak Valid / Timeout**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Input tidak valid atau timeout'], ['Tindakan', 'Proses dibatalkan'], ['Error', f'`{e}`']])}"
                )
            ),
        )
