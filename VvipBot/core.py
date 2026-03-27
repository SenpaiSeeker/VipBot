from . import *


async def get_start_keyboard_and_content(client, user):
    is_owner = await is_bot_owner(client, user.id)
    is_main_bot = client.me.id == ctx.manager.main_bot_id
    main_text_template = await ctx.db.getVars(client.me.id, "start_text_template")
    photo_id = await ctx.db.getVars(client.me.id, "start_photo_id") or "https://files.catbox.moe/ozzvtz.jpg"
    if not main_text_template:
        if is_main_bot:
            main_text_template = "<emoji id=5458904472598095631>👋🏻</emoji> **Selamat Datang, {mention}!**\n\nSaya adalah asisten utama untuk membuat dan mengelola <emoji id=6244241334320762892>💎</emoji> **Bot VVIP** Anda sendiri. Jelajahi semua fitur yang tersedia melalui tombol di bawah ini."
        else:
            main_text_template = "<emoji id=5458904472598095631>👋🏻</emoji> **Selamat Datang, {mention}!**\n\nSaya adalah asisten pribadi Anda untuk mengakses konten eksklusif. Jelajahi semua fitur yang tersedia melalui tombol di bawah ini."
    welcome_text = main_text_template.format(mention=client.ns.telegram.arg.getMention(user))
    layout = []
    if is_main_bot:
        layout.append(
            [
                {
                    "text": "🤖 Buat Bot",
                    "callback_data": "create_bot",
                },
                {
                    "text": "📦 Bot Saya",
                    "callback_data": "list_my_bots_0",
                },
            ]
        )
    if is_owner:
        layout.append(
            [
                {
                    "text": "⚙️ Panel Pengaturan ⚙️",
                    "callback_data": "settings",
                }
            ]
        )
    layout.extend(
        [
            [
                {
                    "text": "📚 Lihat Daftar VVIP 📚",
                    "callback_data": "list_vvip",
                },
            ],
            [
                {
                    "text": "ℹ️ About",
                    "callback_data": "about_bot",
                },
                {
                    "text": "Donasi ❤️",
                    "callback_data": "donate_stars",
                },
            ],
        ]
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    return (btn, welcome_text, photo_id)


@command(lambda ctx: filters.command("start") & filters.private)
@check_new_user
async def start_bot(client, message):
    btn, txt, photo_id = await get_start_keyboard_and_content(client, message.from_user)
    await message.reply_photo(photo=photo_id, caption=txt, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^start$"),
    handler_type="callback",
)
async def start_callback(client, callback_query):
    btn, txt, photo_id = await get_start_keyboard_and_content(client, callback_query.from_user)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.message.delete()
        await client.send_photo(
            callback_query.from_user.id,
            photo=photo_id,
            caption=txt,
            reply_markup=btn,
        )


@command(
    lambda ctx: filters.regex("^about_bot$"),
    handler_type="callback",
)
async def about_bot_callback(client, callback_query):
    text = "<emoji id=5458799228719472718>🌟</emoji> **Tentang Bot VVIP Ini**\n\nSelamat datang! Saya adalah asisten otomatis yang dirancang untuk memberikan Anda kemudahan dalam mengakses grup VVIP.\n\n<emoji id=5372981976804366741>🤖</emoji> **Fungsi Utama Saya:**\nSaya menyediakan sistem pembayaran otomatis yang aman via QRIS, memastikan Anda mendapatkan akses instan ke konten premium setelah transaksi berhasil.\n\n<emoji id=5445284980978621387>🚀</emoji> **Alur Penggunaan:**\n1. **Pilih Paket:** Jelajahi daftar VVIP yang tersedia.\n2. **Lakukan Pembayaran:** Scan QRIS yang saya berikan.\n3. **Akses Instan:** Link undangan akan otomatis terkirim setelah pembayaran terkonfirmasi.\n\nSemua proses dirancang agar cepat, aman, dan tanpa perlu menunggu konfirmasi manual!"
    layout = [
        [
            {
                "text": "• Kembali ke Menu Utama •",
                "callback_data": "start",
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
    layout = []
    if not vvip_list:
        text = "<emoji id=5431736674147114227>🗂️</emoji> Saat ini belum ada paket VVIP yang tersedia."
        layout.append(
            [
                {
                    "text": "• Kembali ke Menu Utama •",
                    "callback_data": "start",
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
                "text": "📂 {name}".format(name=name),
                "callback_data": f"notes_{index}",
            }
        ]
        if promo_price > 0:
            button_row.append(
                {
                    "text": "🎉 Promo {name}".format(name=name),
                    "callback_data": f"promo_detail_{index}",
                }
            )
        layout.append(button_row)
    layout.append(
        [
            {
                "text": "🛒 Ambil Semua VIP",
                "callback_data": "pay_all_vvip",
            }
        ]
    )
    layout.append(
        [
            {
                "text": "• Kembali ke Menu Utama •",
                "callback_data": "start",
            }
        ]
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    text = "<emoji id=5334882760735598374>📚</emoji> **Daftar VVIP Bot: {mention}**\n\nBerikut adalah daftar paket eksklusif yang kami tawarkan. Klik pada salah satu paket untuk melihat detail lengkap dan penawaran spesial.".format(
        mention=client.me.mention
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
    text = "<emoji id=6271607783599117330>❤️</emoji> **Dukung Kami dengan Telegram Stars!**\n\nDonasi Anda sangat berarti untuk membantu kami terus mengembangkan dan memelihara bot ini.\n\nSetiap Star yang Anda berikan memberikan kami semangat untuk terus berinovasi. Pilih jumlah donasi di bawah ini untuk memulai.\n\nTerima kasih atas dukungan Anda!"
    layout = [
        [
            {
                "text": "25 ⭐",
                "callback_data": "donate_pay_25",
            },
            {
                "text": "50 ⭐",
                "callback_data": "donate_pay_50",
            },
        ],
        [
            {
                "text": "75 ⭐",
                "callback_data": "donate_pay_75",
            },
            {
                "text": "100 ⭐",
                "callback_data": "donate_pay_100",
            },
        ],
        [
            {
                "text": "• Kembali ke Menu Utama •",
                "callback_data": "start",
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
        return await callback_query.answer("Jumlah donasi tidak valid!", show_alert=True)
    await callback_query.answer("Mempersiapkan invoice donasi...")
    invoice = {
        "title": "Donasi untuk Pengembangan Bot",
        "description": "Dukungan Anda sebesar {stars} Bintang (Stars) sangat kami hargai. Terima kasih!".format(
            stars=star_amount
        ),
        "payload": f"donation_{star_amount}_{callback_query.from_user.id}_{int(time())}",
        "currency": "XTR",
        "prices": [pyrogram.types.LabeledPrice(f"Donasi {star_amount} Stars", star_amount)],
    }
    try:
        await client.send_invoice(callback_query.from_user.id, **invoice)
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal mengirim invoice Stars: {e}")
        await callback_query.answer(
            "Gagal membuat invoice donasi. Coba lagi nanti.",
            show_alert=True,
        )
