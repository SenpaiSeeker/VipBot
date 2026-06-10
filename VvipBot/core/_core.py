import binascii
import uuid
from time import time

from telethon import events, functions, types

from VvipBot import check_new_user, command, ctx, is_bot_owner

BOT_SETTINGS_CACHE = {}


async def get_cached_setting(bot_id, key, default_value=None):
    cache_key = f"{bot_id}_{key}"

    if cache_key in BOT_SETTINGS_CACHE:
        return BOT_SETTINGS_CACHE[cache_key]

    value = await ctx.db.getVars(bot_id, key)
    final_value = value if value is not None else default_value
    BOT_SETTINGS_CACHE[cache_key] = final_value

    return final_value


def invalidate_setting_cache(bot_id, key):
    BOT_SETTINGS_CACHE.pop(f"{bot_id}_{key}", None)


async def get_start_keyboard_and_content(client, user):
    is_owner = await is_bot_owner(client, user.id)
    is_main_bot = client.uid == ctx.manager.main_bot_id
    em = client.ns.emoji

    if is_main_bot:
        default_text = (
            f"{em.waving} <b>Selamat Datang, {{mention}}!</b>"
            f"\n\nSaya adalah asisten utama untuk membuat dan mengelola "
            f"{em.gem} <b>Bot VVIP</b> Anda sendiri. "
            f"Jelajahi semua fitur yang tersedia melalui tombol di bawah ini."
        )
    else:
        default_text = (
            f"{em.waving} <b>Selamat Datang, {{mention}}!</b>"
            f"\n\nSaya adalah asisten pribadi Anda untuk mengakses konten eksklusif. "
            f"Jelajahi semua fitur yang tersedia melalui tombol di bawah ini."
        )

    main_text_template = await get_cached_setting(
        client.uid, "start_text_template", default_text
    )
    photo_id = await get_cached_setting(
        client.uid, "start_photo_id", "https://files.catbox.moe/ozzvtz.jpg"
    )

    if isinstance(photo_id, dict) and "id" in photo_id:
        photo_ref = binascii.unhexlify(photo_id["file_reference"])
        photo_id = types.InputPhoto(
            id=photo_id["id"],
            access_hash=photo_id["access_hash"],
            file_reference=photo_ref,
        )

    welcome_text = main_text_template.format(
        mention=client.ns.telegram.arg.getMention(user)
    )

    layout = []

    if is_main_bot:
        layout.append(
            [
                {
                    "text": "🆕 Buat Bot",
                    "callback_data": "create_bot",
                    "style": "primary",
                    "emoji": 5372981976804366741,
                },
                {
                    "text": "🤖 Bot Saya",
                    "callback_data": "list_my_bots_0",
                    "style": "primary",
                    "emoji": 5346808226542126040,
                },
            ]
        )

    if is_owner:
        layout.append(
            [
                {
                    "text": "⚙️ Panel Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5449428597922079323,
                },
            ]
        )

    layout.extend(
        [
            [
                {
                    "text": "📋 Lihat Daftar VVIP",
                    "callback_data": "list_vvip",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ],
            [
                {
                    "text": "ℹ️ About",
                    "callback_data": "about_bot",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                },
                {
                    "text": "❤️ Donasi",
                    "callback_data": "donate_stars",
                    "style": "primary",
                    "emoji": 5449505950283078474,
                },
            ],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)

    return btn, welcome_text, photo_id


@command(
    lambda ctx: events.NewMessage(
        incoming=True, pattern=r"^/start$", func=lambda e: e.is_private
    )
)
@check_new_user
async def start_bot(client, event):
    sender = await event.get_sender()
    btn, txt, photo_id = await get_start_keyboard_and_content(client, sender)

    await client.send_message(
        event.chat_id, txt, file=photo_id, buttons=btn, parse_mode="html"
    )


@command(lambda ctx: events.CallbackQuery(pattern=b"^start$"))
async def start_callback(client, event):
    sender = await event.get_sender()
    btn, txt, photo_id = await get_start_keyboard_and_content(client, sender)

    message = await event.get_message()

    if message.photo:
        await event.edit(txt, buttons=btn, parse_mode="html")
    else:
        await event.delete()
        await client.send_message(
            sender.id, txt, file=photo_id, buttons=btn, parse_mode="html"
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^about_bot$"))
async def about_bot_callback(client, event):
    em = client.ns.emoji
    text = (
        f"{em.glowing_star} <b>Tentang Bot VVIP Ini</b>\n\n"
        f"Selamat datang! Saya adalah asisten otomatis yang dirancang untuk memberikan "
        f"Anda kemudahan dalam mengakses grup VVIP.\n\n"
        f"{em.robot} <b>Fungsi Utama Saya:</b>\n"
        f"Saya menyediakan sistem pembayaran otomatis yang aman via QRIS, memastikan "
        f"Anda mendapatkan akses instan ke konten premium setelah transaksi berhasil.\n\n"
        f"{em.rocket} <b>Alur Penggunaan:</b>\n"
        f"1. <b>Pilih Paket:</b> Jelajahi daftar VVIP yang tersedia.\n"
        f"2. <b>Lakukan Pembayaran:</b> Scan QRIS yang saya berikan.\n"
        f"3. <b>Akses Instan:</b> Link undangan akan otomatis terkirim setelah pembayaran terkonfirmasi.\n\n"
        f"Semua proses dirancang agar cepat, aman, dan tanpa perlu menunggu konfirmasi manual!"
    )

    layout = [[{"text": "◀️ Kembali ke Menu Utama", "callback_data": "start", "style": "primary", "emoji": 5373098009640836781}]]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^close_panel$"))
async def close_panel_callback(client, event):
    try:
        await event.delete()
    except Exception:
        await event.answer("Done.")


@command(lambda ctx: events.CallbackQuery(pattern=b"^list_vvip$"))
async def list_vvip_bot(client, event):
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    em = client.ns.emoji
    layout = []

    if not vvip_list:
        text = f"{em.card_index_dividers} Saat ini belum ada paket VVIP yang tersedia."
        layout.append([{"text": "◀️ Kembali ke Menu Utama", "callback_data": "start", "style": "primary", "emoji": 5373098009640836781}])
        btn = client.ns.telegram.button.build_button_grid(layout)
        await event.edit(text, buttons=btn, parse_mode="html")
        return

    for index, item in enumerate(vvip_list):
        name = item.get("name", "N/A")
        promo_price = item.get("promo_price", 0)
        button_row = [
            {
                "text": f"💎 {name}",
                "callback_data": f"notes_{index}",
                "style": "primary",
                "emoji": 5431721976769027887,
            }
        ]

        if promo_price > 0:
            button_row.append(
                {
                    "text": f"🎉 Promo {name}",
                    "callback_data": f"promo_detail_{index}",
                    "style": "primary",
                    "emoji": 5436040291507247633,
                }
            )

        layout.append(button_row)

    layout.append(
        [
            {
                "text": "🛒 Ambil Semua VIP",
                "callback_data": "pay_all_vvip",
                "style": "success",
                "emoji": 5431499171045581032,
            }
        ]
    )
    layout.append([{"text": "◀️ Kembali ke Menu Utama", "callback_data": "start", "style": "primary", "emoji": 5373098009640836781}])

    btn = client.ns.telegram.button.build_button_grid(layout)
    text = (
        f"{em.books} <b>Daftar VVIP Bot: {client.me.first_name}</b>\n\n"
        f"Berikut adalah daftar paket eksklusif yang kami tawarkan. Klik pada salah "
        f"satu paket untuk melihat detail lengkap dan penawaran spesial."
    )

    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^donate_stars$"))
async def donate_callback(client, event):
    em = client.ns.emoji
    photo_url = "https://files.catbox.moe/1f9j10.jpg"
    text = (
        f"{em.red_heart} <b>Dukung Kami dengan Telegram Stars!</b>\n\n"
        f"Donasi Anda sangat berarti untuk membantu kami terus mengembangkan dan "
        f"memelihara bot ini.\n\n"
        f"Setiap Star yang Anda berikan memberikan kami semangat untuk terus berinovasi. "
        f"Pilih jumlah donasi di bawah ini untuk memulai.\n\n"
        f"Terima kasih atas dukungan Anda!"
    )

    layout = [
        [
            {
                "text": "⭐ 25 Stars",
                "callback_data": "donate_pay_25",
                "style": "primary",
                "emoji": 6298332994260175589,
            },
            {
                "text": "⭐ 50 Stars",
                "callback_data": "donate_pay_50",
                "style": "primary",
                "emoji": 6298332994260175589,
            },
        ],
        [
            {
                "text": "⭐ 75 Stars",
                "callback_data": "donate_pay_75",
                "style": "primary",
                "emoji": 6298332994260175589,
            },
            {
                "text": "⭐ 100 Stars",
                "callback_data": "donate_pay_100",
                "style": "primary",
                "emoji": 6298332994260175589,
            },
        ],
        [{"text": "◀️ Kembali ke Menu Utama", "callback_data": "start", "style": "primary", "emoji": 5373098009640836781}],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    message = await event.get_message()

    try:
        if message.photo:
            await event.edit(text, buttons=btn, parse_mode="html")
        else:
            await event.delete()
            await client.send_message(
                event.chat_id, text, file=photo_url, buttons=btn, parse_mode="html"
            )
    except Exception:
        await event.delete()
        await client.send_message(
            event.chat_id, text, file=photo_url, buttons=btn, parse_mode="html"
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^donate_pay_"))
async def process_donation_callback(client, event):
    payload_str = event.data.decode("utf-8")

    try:
        star_amount = int(payload_str.split("_")[2])
    except (IndexError, ValueError):
        return await event.answer("Jumlah donasi tidak valid!", alert=True)

    await event.answer("Mempersiapkan invoice donasi...")

    sender = await event.get_sender()
    price = types.LabeledPrice(label=f"Donasi {star_amount} Stars", amount=star_amount)

    invoice_media = types.InputMediaInvoice(
        title="Donasi untuk Pengembangan Bot",
        description=f"Dukungan Anda sebesar {star_amount} Bintang (Stars) sangat kami hargai. Terima kasih!",
        invoice=types.Invoice(currency="XTR", prices=[price]),
        payload=f"donation_{star_amount}_{sender.id}_{int(time())}".encode("utf-8"),
        provider="",
        provider_data=types.DataJSON("{}"),
    )

    try:
        await client.send_message(sender.id, file=invoice_media)
    except Exception as e:
        ctx.log.print(f"Gagal mengirim invoice Stars: {e}")
        await event.answer("Gagal membuat invoice donasi. Coba lagi nanti.", alert=True)


@command(lambda ctx: events.Raw(types.UpdateBotPrecheckoutQuery))
async def pre_checkout_handler(client, event):
    await client(
        functions.messages.SetBotPrecheckoutResultsRequest(
            query_id=event.query_id,
            success=True,
            error=None,
        )
    )


@command(lambda ctx: events.Raw(types.UpdateNewMessage))
async def successful_donation_handler(client, event):
    if not event.message or not event.message.action:
        return

    if not isinstance(event.message.action, types.MessageActionPaymentSentMe):
        return

    action = event.message.action
    payload = (
        action.payload.decode("utf-8")
        if isinstance(action.payload, bytes)
        else action.payload
    )

    if not payload.startswith("donation_"):
        return

    parts = payload.split("_")
    stars_donated = action.total_amount
    charge_id = event.message.id
    user_id = int(parts[2])
    current_bot_id = client.uid
    super_admin_id = ctx.owner_id
    em = client.ns.emoji

    try:
        user = await client.get_entity(user_id)
    except Exception:
        return

    await client.send_message(
        user.id,
        f"{em.party_popper} <b>Terima Kasih Banyak, {user.first_name}!</b>\n\n"
        f"Kami telah menerima donasi Anda sebesar "
        f"<b>{stars_donated} Stars ({em.tg_stars})</b>.\n"
        f"Dukungan Anda adalah bahan bakar semangat bagi kami. "
        f"Semoga hari Anda menyenangkan!",
        parse_mode="html",
    )

    owner_of_this_bot = (
        await ctx.db.getVars(current_bot_id, "owner_id") or super_admin_id
    )

    try:
        notification_text = (
            f"{em.sparkles} <b>Donasi Baru Diterima!</b>\n\n"
            f"<b>Jumlah:</b> <code>{stars_donated}</code> Stars ({em.tg_stars})\n"
            f"<b>Dari:</b> {client.ns.telegram.arg.getMention(user)} "
            f"(<code>{user.id}</code>)\n"
            f"<b>Melalui Bot:</b> {client.me.first_name}"
        )

        refund_key = uuid.uuid4().hex[:16]
        refund_data = {
            "user_id": user.id,
            "charge_id": charge_id,
        }
        await ctx.db.setVars(current_bot_id, f"refund_{refund_key}", refund_data)

        layout = [
            [
                {
                    "text": "↩️ Kembalikan Donasi",
                    "callback_data": f"refund_stars_{refund_key}",
                    "style": "danger",
                    "emoji": 5386322783009874717,
                }
            ]
        ]
        refund_btn = client.ns.telegram.button.build_button_grid(layout)

        await client.send_message(
            owner_of_this_bot,
            notification_text,
            buttons=refund_btn,
            parse_mode="html",
        )
    except Exception as e:
        ctx.log.print(f"Gagal mengirim notifikasi donasi: {e}")
