from .. import *

DEFAULT_START_PHOTO = "https://files.catbox.moe/ozzvtz.jpg"


async def get_start_keyboard_and_content(client, user):
    is_owner = await is_bot_owner(client, user.id)
    is_main_bot = client.me.id == ctx.manager.main_bot_id

    if is_main_bot:
        _default_text = (
            f"{client.ns.emoji.waving} **Selamat Datang, {{mention}}!**\n\n"
            f"Saya adalah asisten utama untuk membuat dan mengelola "
            f"{client.ns.emoji.gem} **Bot VVIP** Anda sendiri. "
            f"Jelajahi semua fitur yang tersedia melalui tombol di bawah ini."
        )
    else:
        _default_text = (
            f"{client.ns.emoji.waving} **Selamat Datang, {{mention}}!**\n\n"
            f"Saya adalah asisten pribadi Anda untuk mengakses konten eksklusif. "
            f"Jelajahi semua fitur yang tersedia melalui tombol di bawah ini."
        )

    db_text_template = await ctx.db.getVars(client.me.id, "start_text_template")
    main_text_template = (
        db_text_template if db_text_template is not None else _default_text
    )

    db_photo_id = await ctx.db.getVars(client.me.id, "start_photo_id")
    photo_id = db_photo_id if db_photo_id is not None else None

    welcome_text = main_text_template.format(
        mention=client.ns.telegram.arg.getMention(user)
    )

    layout = []

    if is_main_bot:
        layout.append(
            [
                {
                    "text": "🤖 Buat Bot",
                    "callback_data": "create_bot",
                    "style": "green",
                    "emoji": client.ns.emoji.id("robot"),
                },
                {
                    "text": "📦 Bot Saya",
                    "callback_data": "list_my_bots_0",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("folder"),
                },
            ]
        )

    if is_owner:
        layout.append(
            [
                {
                    "text": "⚙️ Panel Pengaturan ⚙️",
                    "callback_data": "settings",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("toolbox"),
                }
            ]
        )

    layout.extend(
        [
            [
                {
                    "text": "📚 Lihat Daftar VVIP 📚",
                    "callback_data": "list_vvip",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("books"),
                },
            ],
            [
                {
                    "text": "ℹ️ About",
                    "callback_data": "about_bot",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("open_book"),
                },
                {
                    "text": "Donasi ❤️",
                    "callback_data": "donate_stars",
                    "style": "green",
                    "emoji": client.ns.emoji.id("red_heart"),
                },
            ],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)
    return btn, welcome_text, photo_id


@command(lambda ctx: filters.command("start") & filters.private)
async def start_bot(client, message):
    btn, txt, photo_id = await get_start_keyboard_and_content(client, message.from_user)
    if photo_id:
        await message.reply_photo(photo=photo_id, caption=txt, reply_markup=btn)
    else:
        await message.reply_text(txt, reply_markup=btn)
    await check_new_user(client, message)


@command(
    lambda ctx: filters.regex("^start$"),
    handler_type="callback",
)
async def start_callback(client, callback_query):
    btn, txt, photo_id = await get_start_keyboard_and_content(
        client, callback_query.from_user
    )

    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        if photo_id:
            await callback_query.message.delete()
            await client.send_photo(
                callback_query.from_user.id,
                photo=photo_id,
                caption=txt,
                reply_markup=btn,
            )
        else:
            await callback_query.edit_message_text(txt, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^about_bot$"),
    handler_type="callback",
)
async def about_bot_callback(client, callback_query):
    text = (
        f"{client.ns.emoji.glowing_star} **Tentang Bot VVIP Ini**\n\n"
        f"Selamat datang! Saya adalah asisten otomatis yang dirancang untuk memberikan Anda kemudahan dalam mengakses grup VVIP.\n\n"
        f"{client.ns.emoji.robot} **Fungsi Utama Saya:**\n"
        f"Saya menyediakan sistem pembayaran otomatis yang aman via QRIS, memastikan Anda mendapatkan akses instan ke konten premium setelah transaksi berhasil.\n\n"
        f"{client.ns.emoji.rocket} **Alur Penggunaan:**\n"
        f"1. **Pilih Paket:** Jelajahi daftar VVIP yang tersedia.\n"
        f"2. **Lakukan Pembayaran:** Scan QRIS yang saya berikan.\n"
        f"3. **Akses Instan:** Link undangan akan otomatis terkirim setelah pembayaran terkonfirmasi.\n\n"
        f"Semua proses dirancang agar cepat, aman, dan tanpa perlu menunggu konfirmasi manual!"
    )

    layout = [
        [
            {
                "text": "• Kembali ke Menu Utama •",
                "callback_data": "start",
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
    lambda ctx: filters.regex("^close_panel$"),
    handler_type="callback",
)
async def close_panel_callback(client, callback_query):
    try:
        await callback_query.message.delete()
    except Exception:
        await callback_query.answer("Done.")


@command(
    lambda ctx: filters.regex("^list_vvip$"),
    handler_type="callback",
)
async def list_vvip_bot(client, callback_query):
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    normal_icon = await get_list_vvip_icon(client, "normal")
    promo_icon = await get_list_vvip_icon(client, "promo")
    layout = []

    if not vvip_list:
        text = f"{client.ns.emoji.card_index_dividers} Saat ini belum ada paket VVIP yang tersedia."
        layout.append(
            [
                {
                    "text": "• Kembali ke Menu Utama •",
                    "callback_data": "start",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ]
        )
        btn = client.ns.telegram.button.build_button_grid(layout)

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)

    for index, item in enumerate(vvip_list):
        name = item.get("name", "N/A")
        promo_price = item.get("promo_price", 0)

        button_row = [
            {
                "text": f"📂 {name}",
                "callback_data": f"notes_{index}",
                "style": "blue",
                "emoji": normal_icon,
            }
        ]

        if promo_price > 0:
            button_row.append(
                {
                    "text": f"🎉 Promo {name}",
                    "callback_data": f"promo_detail_{index}",
                    "style": "green",
                    "emoji": promo_icon,
                }
            )
        layout.append(button_row)

    layout.append(
        [
            {
                "text": "🛒 Ambil Semua VIP",
                "callback_data": "pay_all_vvip",
                "style": "green",
                "emoji": client.ns.emoji.id("shopping_cart"),
            }
        ]
    )

    layout.append(
        [
            {
                "text": "• Kembali ke Menu Utama •",
                "callback_data": "start",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    text = (
        f"{client.ns.emoji.books} **Daftar VVIP Bot: {client.me.mention}**\n\n"
        f"Berikut adalah daftar paket eksklusif yang kami tawarkan. Klik pada salah satu paket untuk melihat detail lengkap dan penawaran spesial."
    )

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^donate_stars$"),
    handler_type="callback",
)
async def donate_callback(client, callback_query):
    photo_url = "https://files.catbox.moe/1f9j10.jpg"
    text = (
        f"{client.ns.emoji.red_heart} **Dukung Kami dengan Telegram Stars!**\n\n"
        f"Donasi Anda sangat berarti untuk membantu kami terus mengembangkan dan memelihara bot ini.\n\n"
        f"Setiap Star yang Anda berikan memberikan kami semangat untuk terus berinovasi. Pilih jumlah donasi di bawah ini untuk memulai.\n\n"
        f"Terima kasih atas dukungan Anda!"
    )

    layout = [
        [
            {
                "text": "25 ⭐",
                "callback_data": "donate_pay_25",
                "style": "blue",
                "emoji": client.ns.emoji.id("star"),
            },
            {
                "text": "50 ⭐",
                "callback_data": "donate_pay_50",
                "style": "blue",
                "emoji": client.ns.emoji.id("star"),
            },
        ],
        [
            {
                "text": "75 ⭐",
                "callback_data": "donate_pay_75",
                "style": "blue",
                "emoji": client.ns.emoji.id("star"),
            },
            {
                "text": "100 ⭐",
                "callback_data": "donate_pay_100",
                "style": "blue",
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
    btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        if callback_query.message.photo:
            await callback_query.edit_message_caption(caption=text, reply_markup=btn)
        else:
            await callback_query.message.delete()
            await client.send_photo(
                callback_query.from_user.id,
                photo=photo_url,
                caption=text,
                reply_markup=btn,
            )
    except Exception:
        await callback_query.message.delete()
        await client.send_photo(
            callback_query.from_user.id,
            photo=photo_url,
            caption=text,
            reply_markup=btn,
        )


@command(
    lambda ctx: filters.regex("^donate_pay_(\\d+)$"),
    handler_type="callback",
)
async def process_donation_callback(client, callback_query):
    try:
        star_amount = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        return await callback_query.answer(
            "Jumlah donasi tidak valid!", show_alert=True
        )

    await callback_query.answer("Mempersiapkan invoice donasi...")

    invoice = {
        "title": "Donasi untuk Pengembangan Bot",
        "description": "Dukungan Anda sebesar {stars} Bintang (Stars) sangat kami hargai. Terima kasih!".format(
            stars=star_amount
        ),
        "payload": f"donation_{star_amount}_{callback_query.from_user.id}_{int(time())}",
        "currency": "XTR",
        "prices": [
            pyrogram.types.LabeledPrice(f"Donasi {star_amount} Stars", star_amount)
        ],
    }

    try:
        await client.send_invoice(callback_query.from_user.id, **invoice)
    except Exception as e:
        ctx.log.print(f"Gagal mengirim invoice Stars: {e}")
        await callback_query.answer(
            "Gagal membuat invoice donasi. Coba lagi nanti.",
            show_alert=True,
        )
