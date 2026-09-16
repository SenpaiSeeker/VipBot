import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import pyrogram
from pyrogram import filters
from services import initialize_bot_services
from .start import DEFAULT_START_PHOTO
from . import command, ctx, is_bot_owner, listen


@command(
    lambda ctx: filters.regex("^settings$"),
    handler_type="callback",
)
async def settings(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    layout = [
        [
            {
                "text": "🖼️ Atur Foto Start",
                "callback_data": "set_start_photo",
                "style": "blue",
                "emoji": client.ns.emoji.id("frame"),
            },
            {
                "text": "✍️ Atur Teks Start",
                "callback_data": "set_start_text",
                "style": "blue",
                "emoji": client.ns.emoji.id("writing_hand"),
            },
        ],
        [
            {
                "text": "➕ Tambah VVIP",
                "callback_data": "setup_listvvip",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            },
            {
                "text": "➖ Hapus VVIP",
                "callback_data": "delete_listvvip",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
        ],
        [
            {
                "text": "✏️ Edit Harga VVIP",
                "callback_data": "edit_price_listvvip",
                "style": "blue",
                "emoji": client.ns.emoji.id("pencil"),
            }
        ],
        [
            {
                "text": "👥 Total Pengguna",
                "callback_data": "total_users_count",
                "style": "blue",
                "emoji": client.ns.emoji.id("busts_in_silhouette"),
            },
            {
                "text": "👥 Cek Member VVIP",
                "callback_data": "list_members_0",
                "style": "blue",
                "emoji": client.ns.emoji.id("busts_in_silhouette"),
            },
        ],
        [
            {
                "text": "🕵️ Cek Member Aktif",
                "callback_data": "check_active_menu_init",
                "style": "blue",
                "emoji": client.ns.emoji.id("mag"),
            },
            {
                "text": "🔍 Cek Status Grup VVIP",
                "callback_data": "check_vvip_status",
                "style": "blue",
                "emoji": client.ns.emoji.id("mag_right"),
            },
        ],
        [
            {
                "text": "📢 Buat Broadcast",
                "callback_data": "broadcast",
                "style": "green",
                "emoji": client.ns.emoji.id("loudspeaker"),
            },
            {
                "text": "🌟 Harga Broadcast Paid",
                "callback_data": "set_broadcast_price",
                "style": "green",
                "emoji": client.ns.emoji.id("glowing_star"),
            },
        ],
        [
            {
                "text": "🔑 Kelola Kunci API",
                "callback_data": "api_settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("key"),
            },
            {
                "text": "🎟️ Kelola Kupon",
                "callback_data": "manage_coupons",
                "style": "blue",
                "emoji": client.ns.emoji.id("ticket_admit"),
            },
        ],
        [
            {
                "text": "🔔 Atur Tempat Notifikasi",
                "callback_data": "set_notif_chat",
                "style": "blue",
                "emoji": client.ns.emoji.id("bell"),
            }
        ],
        [
            {
                "text": "💰 Pendapatan VIP",
                "callback_data": "vip_revenue_menu",
                "style": "green",
                "emoji": client.ns.emoji.id("money_bag"),
            },
            {
                "text": "⭐ Statistik Stars",
                "callback_data": "stats_0",
                "style": "green",
                "emoji": client.ns.emoji.id("star"),
            },
        ],
        [
            {
                "text": "• Kembali ke Menu Utama •",
                "callback_data": "start",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]

    txt_content = f"**{client.ns.emoji.toolbox} Panel Pengaturan Owner**\n\nSelamat datang di pusat kendali bot Anda! Silakan pilih menu di bawah untuk mengelola berbagai aspek bot."
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt_content, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt_content, reply_markup=btn)


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

    await client.send_message(
        chat_id,
        f"**{client.ns.emoji.frame} Atur Foto Start**\n\n"
        f"Silakan pilih opsi di bawah ini untuk mengubah foto sambutan `/start`.\n\n"
        f"**{client.ns.emoji.warning} Perhatian:**\n"
        f"Semakin besar ukuran foto, maka semakin lama juga respon `/start`.\n"
        f"Gunakan foto berukuran kecil agar bot tetap cepat merespons.\n\n"
        f"Jika foto tidak diatur, maka `/start` hanya akan mengirim **teks sambutan saja**.",
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

    await client.send_message(
        chat_id,
        f"{client.ns.emoji.white_check_mark} **Sukses!**\n"
        f"Foto `/start` diatur ke **foto default**.",
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

    await client.send_message(
        chat_id,
        f"{client.ns.emoji.white_check_mark} **Sukses!**\n"
        f"Foto `/start` telah dihapus. Sekarang `/start` hanya akan mengirim **teks sambutan**.",
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
            f"**{client.ns.emoji.frame} Kirim Foto Baru**\n\n"
            f"Silakan kirim foto baru untuk menyambut user.\n\n"
            f"**{client.ns.emoji.warning} Perhatian:** Semakin besar ukuran foto, maka semakin lama juga respon `/start`.\n\n"
            f"Ketik `/batal` untuk membatalkan.\n"
            f"Ketik `/empty` untuk menghapus foto dan hanya mengirim teks."
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=120)

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
            f"**{client.ns.emoji.writing_hand} Atur Teks Start**\n\n"
            f"Silakan kirim teks baru untuk pesan /start. Anda dapat menggunakan variabel `{{mention}}` untuk menyapa pengguna.\n\n"
            f"Ketik `/empty` untuk menghapus teks kustom dan kembali ke default.\n\n"
            f"Ketik `/batal` untuk membatalkan."
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

    await client.send_message(
        chat_id,
        f"{client.ns.emoji.white_check_mark} Pemeriksaan Selesai.",
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
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )

        vvip_data["duration"] = int(
            validate(
                await ask(
                    f"**{client.ns.emoji.hourglass} Langkah 3/8: Durasi Keanggotaan (Hari)**\nKirim `0` untuk akses permanen."
                ),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )

        vvip_data["chat_id_normal"] = int(
            validate(
                await ask(
                    f"**{client.ns.emoji.id_card} Langkah 4/8: Chat ID Grup Normal**\nContoh: `-100123456789`."
                ),
                is_chatid,
                "settings.setup_vvip.err_must_be_chat_id",
            )
        )

        vvip_data["promo_price"] = int(
            validate(
                await ask(
                    f"**{client.ns.emoji.party_popper} Langkah 5/8: Harga Promo**\nKirim `0` jika tidak ada harga promo."
                ),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )

        if vvip_data["promo_price"] > 0:
            vvip_data["chat_id_promo"] = int(
                validate(
                    await ask(
                        f"**{client.ns.emoji.id_card} Langkah 6/8: Chat ID Grup Promo**\nDiisi jika Harga Promo > 0."
                    ),
                    is_chatid,
                    "settings.setup_vvip.err_must_be_chat_id",
                )
            )

            prompt_promo = (
                f"**{client.ns.emoji.pencil} Langkah 7/8: Teks Deskripsi Promo**\n"
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
            f"**{client.ns.emoji.pencil} Langkah 8/8: Teks Deskripsi Normal**\n"
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
        text = f"{client.ns.emoji.white_check_mark} Tidak ada paket VVIP untuk dihapus."
        btn = client.ns.telegram.button.build_button_grid([back_row])

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)

    if not hasattr(ctx, "vip_list"):
        ctx.vip_list = {}

    layout = []
    button_row = []

    for item in vvip_list:
        name = item.get("name", "Tanpa Nama")
        item_id = uuid.uuid4().hex[:8]
        ctx.vip_list[item_id] = name

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

    text = f"**{client.ns.emoji.minus} Hapus Paket VVIP**\n\nPilih paket VVIP yang ingin Anda hapus."
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


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
        text = f"{client.ns.emoji.cross_mark} Belum ada paket VVIP."
        btn = client.ns.telegram.button.build_button_grid([back_row])

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)

    if not hasattr(ctx, "vip_list_edit"):
        ctx.vip_list_edit = {}

    layout = []
    button_row = []

    for item in vvip_list:
        name = item.get("name", "Tanpa Nama")
        item_id = uuid.uuid4().hex[:8]
        ctx.vip_list_edit[item_id] = name

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

    text = f"**{client.ns.emoji.pencil} Edit Harga VVIP**\n\nPilih paket VVIP yang ingin Anda ubah harganya."
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


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


@command(
    lambda ctx: filters.regex("^api_settings$"),
    handler_type="callback",
)
async def api_settings_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    saweria_status = (
        f"{client.ns.emoji.white_check_mark} Ativ"
        if saweria_user_id
        else f"{client.ns.emoji.cross_mark} Belum Diatur"
    )

    layout = [
        [
            {
                "text": "💳 Atur Kunci Saweria",
                "callback_data": "set_api SAWERIA",
                "style": "green",
                "emoji": client.ns.emoji.id("gem"),
            }
        ],
        [
            {
                "text": "🗑️ Hapus Semua Kunci",
                "callback_data": "del_api_confirm",
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

    text = f"**{client.ns.emoji.key} Pengelola Kunci API untuk {client.me.mention}**\n\nAtur koneksi pembayaran Saweria untuk bot Anda.\n\n**Status Layanan:**\n- `Gateway Pembayaran (Saweria)`: **{saweria_status}**\n\nPilih tindakan:"
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^set_api\\s(.+)"),
    handler_type="callback",
)
async def set_api_key_prompt(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    _, key_name = callback_query.data.split(" ", 1)
    await callback_query.message.delete()

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan API •",
                "callback_data": "api_settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        def ask(p):
            return client.ask(
                chat_id,
                f"{p}\n\nKetik `/batal` untuk membatalkan.",
                timeout=600,
            )

        if key_name == "SAWERIA":
            username_msg = await ask(f"**2/2:** Kirim **Username Saweria** Anda.")
            if username_msg.text and username_msg.text.lower() == "/batal":
                raise listen.UserCancelled

            processing_msg = await client.send_message(
                chat_id,
                f"{client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.",
            )

            try:
                saweria_temp = client.ns.payment.SaweriaScraper()
                user_id_saweria = await saweria_temp.get_user_id(
                    username=username_msg.text
                )

                if not user_id_saweria:
                    raise Exception(
                        "Username Saweria tidak ditemukan."
                    )

                await ctx.db.setVars(
                    client.me.id,
                    "SAWERIA_USER_ID",
                    user_id_saweria,
                )

                await processing_msg.delete()

                await client.send_message(
                    chat_id,
                    f"{client.ns.emoji.white_check_mark} **Sukses!**\nKunci Saweria berhasil disimpan.",
                    reply_markup=back_btn,
                )

            except Exception as e:
                await processing_msg.edit_text(
                    f"{client.ns.emoji.cross_mark} **Gagal!**\n`Error: {e}`",
                    reply_markup=back_btn,
                )
                return
        else:
            await client.send_message(
                chat_id,
                "Fitur tidak didukung.",
                reply_markup=back_btn,
            )
            return

        await initialize_bot_services(client, ctx.db)

    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
            reply_markup=back_btn,
        )


@command(
    lambda ctx: filters.regex("^del_api_confirm$"),
    handler_type="callback",
)
async def confirm_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    text = f"**{client.ns.emoji.exclamation} Konfirmasi**\n\nAnda yakin ingin menghapus **SEMUA** kunci API?"
    layout = [
        [
            {
                "text": "✅ Ya, Hapus Semua",
                "callback_data": "do_del_api",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": "❌ Tidak, Batalkan",
                "callback_data": "api_settings",
                "style": "green",
                "emoji": client.ns.emoji.id("white_check_mark"),
            },
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^do_del_api$"),
    handler_type="callback",
)
async def do_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    await ctx.db.removeVars(client.me.id, "SAWERIA_USER_ID")

    await initialize_bot_services(client, ctx.db)

    await callback_query.answer(
        "Semua kunci API untuk bot ini telah berhasil dihapus.",
        show_alert=True,
    )
    await api_settings_callback(client, callback_query)


@command(
    lambda ctx: filters.regex("^manage_coupons"),
    handler_type="callback",
)
async def manage_coupons_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    text = f"**{client.ns.emoji.ticket_admit} Manajemen Kupon**\nKelola kode diskon untuk VVIP Anda."
    layout = [
        [
            {
                "text": "➕ Buat Kupon Baru",
                "callback_data": "add_coupon",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            }
        ],
        [
            {
                "text": "📋 Lihat Kupon",
                "callback_data": "list_coupons_0",
                "style": "blue",
                "emoji": client.ns.emoji.id("open_book"),
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^add_coupon"),
    handler_type="callback",
)
async def add_coupon_callback(client, callback_query):
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

        code = (
            await ask(f"**1/4:** Masukkan kode kupon unik (misal: `DISKONBARU`).")
        ).text.upper()

        type_msg = await ask(
            "**2/4:** Pilih tipe diskon:\n1. Persentase (%)\n2. Potongan Harga Tetap"
        )
        discount_type = "percentage" if "1" in type_msg.text else "fixed"

        value_prompt = (
            "**3/4:** Masukkan nilai persentase."
            if discount_type == "percentage"
            else "**3/4:** Masukkan jumlah potongan harga."
        )
        discount_value = int((await ask(value_prompt)).text)

        uses_left = int(
            (
                await ask(
                    "**4/4:** Berapa kali kupon ini bisa digunakan?"
                )
            ).text
        )

        expiry_days_msg = await ask(
            "**5/5:** Berapa hari kupon ini akan berlaku?"
        )
        expiry_days = int(expiry_days_msg.text)

        expiry_date = (
            (datetime.now(timezone.utc) + timedelta(days=expiry_days)).isoformat()
            if expiry_days > 0
            else None
        )

        coupon_data = {
            "code": code,
            "discount_type": discount_type,
            "discount_value": discount_value,
            "uses_left": uses_left,
            "expiry_date": expiry_date,
        }

        await ctx.db.setListVars(client.me.id, "coupons", coupon_data)

        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} Kupon `{code}` berhasil dibuat.",
        )

    except (listen.UserCancelled, asyncio.TimeoutError, ValueError):
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
        )


@command(
    lambda ctx: filters.regex("^list_coupons_(\\d+)"),
    handler_type="callback",
)
async def list_coupons_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    page = int(callback_query.data.split("_")[2])
    coupons = await ctx.db.getListVars(client.me.id, "coupons") or []

    back_row = [
        {
            "text": "• Kembali •",
            "callback_data": "manage_coupons",
            "style": "blue",
            "emoji": client.ns.emoji.id("back_arrow"),
        }
    ]

    if not coupons:
        text = "Tidak ada kupon yang dibuat."
        btn = client.ns.telegram.button.build_button_grid([back_row])
        await callback_query.edit_message_caption(text, reply_markup=btn)
        return

    total_pages = len(coupons)
    page = max(0, min(page, total_pages - 1))
    coupon = coupons[page]

    expiry_text = "Permanent"
    if coupon.get("expiry_date"):
        expiry_text = datetime.fromisoformat(coupon["expiry_date"]).strftime("%d %b %Y")

    text = (
        f"**{client.ns.emoji.pencil} Detail Kupon ({page + 1}/{total_pages})**\n"
        f"- Kode: `{coupon['code']}`\n"
        f"- Tipe: `{coupon['discount_type']}`\n"
        f"- Nilai: `{coupon['discount_value']}`\n"
        f"- Sisa Penggunaan: `{coupon['uses_left']}`\n"
        f"- Berlaku hingga: `{expiry_text}`"
    )

    layout = []
    pagination_row = []

    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages if page + 1 < total_pages else page

        pagination_row.extend(
            [
                {
                    "text": "«",
                    "callback_data": f"list_coupons_{prev_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                },
                {
                    "text": "»",
                    "callback_data": f"list_coupons_{next_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("right_pointing"),
                },
            ]
        )

    layout.append(
        [
            {
                "text": "🗑️ Hapus Kupon Ini",
                "callback_data": f"delete_coupon {coupon['code']} {page}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ]
    )

    if pagination_row:
        layout.append(pagination_row)
    layout.append(back_row)

    btn = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_caption(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^delete_coupon\\s(.+)\\s(\\d+)"),
    handler_type="callback",
)
async def delete_coupon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    _, code, page_str = callback_query.data.split()
    coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
    coupon_to_remove = next((c for c in coupons if c.get("code") == code), None)

    if coupon_to_remove:
        await ctx.db.removeListVars(client.me.id, "coupons", coupon_to_remove)
        await callback_query.answer("Kupon berhasil dihapus.", show_alert=True)

    new_page = int(page_str)
    remaining_coupons = await ctx.db.getListVars(client.me.id, "coupons") or []

    if new_page >= len(remaining_coupons) and len(remaining_coupons) > 0:
        new_page = len(remaining_coupons) - 1

    callback_query.data = f"list_coupons_{new_page}"
    await list_coupons_callback(client, callback_query)


@command(
    lambda ctx: filters.regex("^vip_revenue_menu$"),
    handler_type="callback",
)
async def vip_revenue_menu_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    text = f"**{client.ns.emoji.money_bag} Cek Pendapatan VIP**\n\nPilih periode waktu untuk melihat total pendapatan dari penjualan paket VIP."
    layout = [
        [
            {
                "text": "📅 Harian (Hari Ini)",
                "callback_data": "show_revenue_daily",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            },
            {
                "text": "🗓️ Mingguan (7 Hari)",
                "callback_data": "show_revenue_weekly",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            },
        ],
        [
            {
                "text": "📆 Bulanan (Bulan Ini)",
                "callback_data": "show_revenue_monthly",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^show_revenue_(daily|weekly|monthly)$"),
    handler_type="callback",
)
async def show_vip_revenue_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    period = callback_query.matches[0].group(1)
    revenue_history = (
        await ctx.db.getListVars(client.me.id, "vip_revenue_history") or []
    )

    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    total_amount = 0
    transaction_count = 0

    for record in revenue_history:
        try:
            record_date = datetime.fromisoformat(record["date"]).astimezone(
                ZoneInfo("Asia/Jakarta")
            )
            include_record = False

            if period == "daily":
                if record_date.date() == now.date():
                    include_record = True
            elif period == "weekly":
                if now - timedelta(days=7) <= record_date <= now:
                    include_record = True
            elif period == "monthly":
                if record_date.year == now.year and record_date.month == now.month:
                    include_record = True

            if include_record:
                total_amount += int(record["amount"])
                transaction_count += 1
        except Exception:
            continue

    period_text = {
        "daily": "Harian",
        "weekly": "Mingguan",
        "monthly": "Bulanan",
    }.get(period, "Harian")

    text = (
        f"**{client.ns.emoji.chart_bar} Laporan Pendapatan VIP**\n\n"
        f"**Periode:** {period_text}\n\n"
        f"{client.ns.emoji.money_bag} **Total Pendapatan:** `Rp {total_amount:,}`\n"
        f"{client.ns.emoji.repeat} **Jumlah Transaksi:** `{transaction_count}`"
    )

    layout = [
        [
            {
                "text": "• Kembali •",
                "callback_data": "vip_revenue_menu",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^set_notif_chat$"),
    handler_type="callback",
)
async def set_notif_chat_callback(client, callback_query):
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
            f"**{client.ns.emoji.bell} Atur Tempat Notifikasi**\n\n"
            f"Kirim ID chat atau @username tempat notifikasi pembayaran akan dikirim.\n\n"
            f"Ketik `/none` untuk kembali ke default (dikirim ke owner_id).\n\n"
            f"Ketik `/batal` untuk membatalkan."
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=600)

        if not ask_msg.text:
            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.cross_mark} **Gagal:** Pesan bukan teks.",
                reply_markup=back_btn,
            )

        if ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        if ask_msg.text.lower() == "/none":
            await ctx.db.removeVars(client.me.id, "notif_chat_id")

            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.white_check_mark} **Sukses!** Notifikasi kembali ke default (owner_id).",
                reply_markup=back_btn,
            )

        await ctx.db.setVars(client.me.id, "notif_chat_id", ask_msg.text)

        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} **Sukses!** Tempat notifikasi diatur ke `{ask_msg.text}`.",
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
            reply_markup=back_btn,
        )


@command(
    lambda ctx: filters.regex("^set_broadcast_price$"),
    handler_type="callback",
)
async def set_broadcast_price_callback(client, callback_query):
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
            f"**{client.ns.emoji.glowing_star} Atur Harga Broadcast Paid**\n\n"
            f"Masukkan jumlah Bintang (Stars) yang harus dibayar pengguna.\n\n"
            f"Ketik `0` atau `/empty` untuk menonaktifkan.\n\n"
            f"Ketik `/batal` untuk membatalkan."
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=300)

        if ask_msg.text:
            if ask_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if ask_msg.text.lower() in ["/empty", "0"]:
                await ctx.db.removeVars(client.me.id, "broadcast_price")

                return await client.send_message(
                    chat_id,
                    f"{client.ns.emoji.white_check_mark} **Sukses!** Fitur Paid Broadcast dinonaktifkan.",
                    reply_markup=back_btn,
                )

        if not ask_msg.text.isdigit():
            raise ValueError("**Format Salah**")

        stars_amount = int(ask_msg.text)
        await ctx.db.setVars(client.me.id, "broadcast_price", stars_amount)

        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} **Sukses!** Harga broadcast telah diatur menjadi `{stars_amount}` Stars.",
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError, ValueError) as e:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**\n{e}",
            reply_markup=back_btn,
        )


async def _send_broadcast_message(client, target_user_id, source_message, broadcast_price=0):
    caption_or_text = source_message.caption or source_message.text
    text_to_parse = caption_or_text.markdown if caption_or_text else ""
    reply_markup, cleaned_text = client.ns.telegram.button.create_inline_keyboard(
        text_to_parse
    )

    final_markup = (
        reply_markup
        if reply_markup.inline_keyboard
        else (source_message.reply_markup if source_message.reply_markup else None)
    )

    if broadcast_price > 0 and (source_message.photo or source_message.video):
        media_list = []

        if source_message.photo:
            media_list.append(
                pyrogram.types.InputPaidMediaPhoto(
                    source_message.photo.sizes[-1].file_id
                )
            )
        elif source_message.video:
            media_list.append(
                pyrogram.types.InputPaidMediaVideo(source_message.video.file_id)
            )

        await client.send_paid_media(
            chat_id=target_user_id,
            star_count=broadcast_price,
            media=media_list,
            caption=cleaned_text,
            reply_markup=final_markup,
        )
        return

    if source_message.photo:
        await client.send_photo(
            chat_id=target_user_id,
            photo=source_message.photo.sizes[-1].file_id,
            caption=cleaned_text,
            reply_markup=final_markup,
        )
    elif source_message.text:
        await client.send_message(
            chat_id=target_user_id,
            text=cleaned_text,
            reply_markup=final_markup,
        )
    else:
        await source_message.copy(
            chat_id=target_user_id,
            caption=cleaned_text,
            reply_markup=final_markup,
        )


@command(
    lambda ctx: filters.regex("^broadcast$"),
    handler_type="callback",
)
async def broadcast_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    chat_id = callback_query.message.chat.id
    bot_id = client.me.id

    try:
        await callback_query.message.delete()
        prompt = (
            f"**{client.ns.emoji.loudspeaker} Kirim Pesan Broadcast**\n\n"
            f"Silakan teruskan (forward) atau kirim pesan yang ingin disiarkan.\n\n"
            f"Ketik `/batal` untuk membatalkan."
        )
        ask_message = await client.ask(chat_id, text=prompt, timeout=600)

        if ask_message.text and ask_message.text.lower() == "/batal":
            raise listen.UserCancelled

        broadcast_price = await ctx.db.getVars(bot_id, "broadcast_price") or 0
        broadcast_price = int(broadcast_price)

        if broadcast_price > 0 and (not (ask_message.photo or ask_message.video)):
            raise ValueError(
                f"{client.ns.emoji.cross_mark} **Gagal:** Paid Broadcast memerlukan media foto/video!"
            )

        user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
        if not user_ids:
            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.cross_mark} **Gagal:** Tidak ada pengguna.",
            )

        progress_msg = await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} Memulai siaran ke `{len(user_ids)}` pengguna...",
        )
        success_count, fail_count = 0, 0

        async def send_to_user(target_user_id):
            nonlocal success_count, fail_count
            try:
                await _send_broadcast_message_internal(
                    client,
                    target_user_id,
                    ask_message,
                    broadcast_price,
                )
                success_count += 1
            except pyrogram.errors.FloodWait as e:
                await asyncio.sleep(e.value + 1)
                await send_to_user(target_user_id)
            except Exception:
                await ctx.db.removeListVars(client.me.id, "user_ids", target_user_id)
                fail_count += 1
            await asyncio.sleep(0.1)

        for user_id in user_ids:
            if user_id != ctx.owner_id:
                await send_to_user(user_id)

        await progress_msg.delete()

        await client.send_message(
            chat_id,
            f"**{client.ns.emoji.loudspeaker} Siaran Selesai!**\n"
            f"{client.ns.emoji.white_check_mark} **Terkirim:** `{success_count}`\n"
            f"{client.ns.emoji.cross_mark} **Gagal:** `{fail_count}`",
        )

    except (listen.UserCancelled, asyncio.TimeoutError, ValueError) as e:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Gagal/Batal**\n{e}",
        )


async def _send_broadcast_message_internal(client, target_user_id, source_message, broadcast_price):
    await _send_broadcast_message(client, target_user_id, source_message, broadcast_price)