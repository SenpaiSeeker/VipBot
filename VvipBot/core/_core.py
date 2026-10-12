from .. import *

DEFAULT_START_PHOTO = "https://files.catbox.moe/ozzvtz.jpg"


async def get_start_keyboard_and_content(client, user):
    is_owner = await is_bot_owner(client, user.id)
    is_main_bot = client.me.id == ctx.manager.main_bot_id

    if is_main_bot:
        _default_text = (
            f"{client.ns.emoji.md('waving')} **Selamat Datang, {{mention}}!**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Peran', 'Asisten utama pembuatan dan pengelolaan Bot VVIP'], ['Navigasi', 'Jelajahi semua fitur melalui tombol di bawah ini']])}"
        )
    else:
        _default_text = (
            f"{client.ns.emoji.md('waving')} **Selamat Datang, {{mention}}!**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Peran', 'Asisten pribadi akses konten eksklusif'], ['Navigasi', 'Jelajahi semua fitur melalui tombol di bawah ini']])}"
        )

    db_text_template = await ctx.db.getVars(client.me.id, "start_text_template")
    main_text_template = (
        db_text_template if db_text_template is not None else _default_text
    )

    db_photo_id = await ctx.db.getVars(client.me.id, "start_photo_id")
    photo_id = db_photo_id if db_photo_id is not None else None

    welcome_text = main_text_template.replace(
        "{mention}", client.ns.telegram.arg.getMention(user, md=True)
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
    await message.reply_rich(
        client.ns.table.rich_photo(photo=photo_id, markdown=txt, alias="start_photo"),
        reply_markup=btn,
    )
    await check_new_user(client, message)


@command(
    lambda ctx: filters.regex("^start$"),
    handler_type="callback",
)
async def start_callback(client, callback_query):
    btn, txt, photo_id = await get_start_keyboard_and_content(
        client, callback_query.from_user
    )

    if photo_id:
        await callback_query.message.delete()
        await client.send_rich_message(
            callback_query.from_user.id,
            client.ns.table.rich_photo(
                photo=photo_id, markdown=txt, alias="start_photo"
            ),
            reply_markup=btn,
        )
    else:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=txt),
            reply_markup=btn,
        )


@command(
    lambda ctx: filters.regex("^about_bot$"),
    handler_type="callback",
)
async def about_bot_callback(client, callback_query):
    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('glowing_star')} **Tentang Bot VVIP Ini**\n\n"
        f"Selamat datang! Saya adalah asisten otomatis yang dirancang untuk memberikan Anda kemudahan dalam accessing grup VVIP.\n\n"
        f"{client.ns.emoji.md('robot')} **Fungsi Utama Saya**\n\n"
        f"{table.md(['Fitur', 'Keterangan'], [['Pembayaran', 'Otomatis dan aman via QRIS'], ['Akses', 'Instan setelah transaksi berhasil'], ['Konfirmasi', 'Tanpa menunggu konfirmasi manual']])}\n\n"
        f"{client.ns.emoji.md('rocket')} **Alur Penggunaan**\n\n"
        f"{table.md(['Langkah', 'Tindakan'], [['1', 'Pilih paket — jelajahi daftar VVIP yang tersedia'], ['2', 'Lakukan pembayaran — scan QRIS yang saya berikan'], ['3', 'Akses instan — link undangan terkirim otomatis setelah pembayaran terkonfirmasi']])}"
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

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


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
    normal_icon = client.ns.emoji.id(LIST_VVIP_ICON_DEFAULT["normal"])
    promo_icon = client.ns.emoji.id(LIST_VVIP_ICON_DEFAULT["promo"])
    custom_icons = await get_list_vvip_icons(client)
    layout = []

    if not vvip_list:
        table = client.ns.table
        empty_rows = [
            ["Jumlah Paket", "`0`"],
            ["Status", "Belum ada paket VVIP tersedia"],
            ["Aksi", "Tambahkan paket melalui pengaturan"],
        ]
        text = (
            f"{client.ns.emoji.md('card_index_dividers')} **Daftar Paket VVIP**\n\n"
            f"{table.md(['Info', 'Nilai'], empty_rows)}"
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

        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=btn,
        )

    for index, item in enumerate(vvip_list):
        name = item.get("name", "N/A")
        promo_price = item.get("promo_price", 0)

        item_entry = custom_icons.get(name)
        item_icon = item_entry["id"] if item_entry else None
        item_normal_icon = item_icon or normal_icon
        item_promo_icon = item_icon or promo_icon

        button_row = [
            {
                "text": name,
                "callback_data": f"notes_{index}",
                "style": "blue",
                "emoji": item_normal_icon,
            }
        ]

        if promo_price > 0:
            button_row.append(
                {
                    "text": f"Promo {name}",
                    "callback_data": f"promo_detail_{index}",
                    "style": "green",
                    "emoji": item_promo_icon,
                }
            )
        layout.append(button_row)

    buy_all_entry = custom_icons.get(LIST_VVIP_ICON_BUY_ALL_KEY)
    buy_all_icon = (
        buy_all_entry["id"] if buy_all_entry else client.ns.emoji.id("shopping_cart")
    )

    if len(vvip_list) > 1:
        layout.append(
            [
                {
                    "text": "Pilih Paket Sendiri",
                    "callback_data": "pick_vvip",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("shopping_bags"),
                }
            ]
        )
        layout.append(
            [
                {
                    "text": "Ambil Semua VIP",
                    "callback_data": "pay_all_vvip",
                    "style": "green",
                    "emoji": buy_all_icon,
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
        f"{client.ns.emoji.md('books')} **Daftar VVIP Bot**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', client.ns.telegram.arg.getMention(client.me, md=True)], ['Keterangan', 'Daftar paket eksklusif. Klik paket untuk detail lengkap dan penawaran spesial.']])}"
    )

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


@command(
    lambda ctx: filters.regex("^donate_stars$"),
    handler_type="callback",
)
async def donate_callback(client, callback_query):
    photo_url = "https://files.catbox.moe/1f9j10.jpg"
    donate_rows = [
        ["25 ⭐", "Paling ringan"],
        ["50 ⭐", "Dukungan dasar"],
        ["75 ⭐", "Dukungan sedang"],
        ["100 ⭐", "Dukungan maksimal"],
    ]
    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('red_heart')} **Dukung Kami dengan Telegram Stars**\n\n"
        f"{table.md(['Jumlah', 'Keterangan'], donate_rows)}\n\n"
        f"Setiap Star yang Anda berikan memberi kami semangat untuk terus berinovasi."
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

    if callback_query.message.photo:
        await callback_query.message.delete()

    try:
        await client.send_rich_message(
            callback_query.from_user.id,
            client.ns.table.rich_photo(
                photo=photo_url, markdown=text, alias="donate_photo"
            ),
            reply_markup=btn,
        )
    except Exception:
        await client.send_rich_message(
            callback_query.from_user.id,
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
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