import asyncio
from datetime import datetime, timedelta, timezone

from telethon import events

from .. import command, ctx

BASE_PRICE_BOT = 100000


def calculate_bot_price(months):
    total = BASE_PRICE_BOT * months
    discount_percentage = 0

    if months >= 6:
        discount_percentage = 0.2
    elif months >= 3:
        discount_percentage = 0.1

    discount = int(total * discount_percentage)
    final_price = total - discount

    return (total, discount, final_price)


async def get_bot_purchase_panel(client, user_id, months=1):
    total, discount, final_price = calculate_bot_price(months)
    em = client.ns.emoji

    text = (
        f"{em.money_bag} <b>Beli Akses Pembuatan Bot</b>\n\n"
        f"Dapatkan akses untuk membuat bot VVIP Anda sendiri dengan berlangganan.\n\n"
        f"Harga: <code>Rp {BASE_PRICE_BOT:,}/bulan</code>\n\n"
        f"<b>Diskon:</b>\n"
        f"• 3+ Bulan: 10%\n"
        f"• 6+ Bulan: 20%\n\n"
        f"<b>Pilihan Anda:</b>\n"
        f"• Durasi: <b>{months} bulan</b>\n"
        f"• Harga Normal: <code>Rp {total:,}</code>\n"
        f"• Diskon: <code>-Rp {discount:,}</code>\n"
        f"• <b>Total Bayar: <code>Rp {final_price:,}</code></b>"
    )

    layout = [
        [
            {
                "text": "➖",
                "callback_data": f"adjust_bot_month_{months - 1}",
                "style": "danger",
                "emoji": 5229113891081956317,
            },
            {
                "text": f"📅 {months} Bulan",
                "callback_data": "noop",
                "style": "primary",
                "emoji": 5431897022456145283,
            },
            {
                "text": "➕",
                "callback_data": f"adjust_bot_month_{months + 1}",
                "style": "success",
                "emoji": 5226945370684140473,
            },
        ],
        [
            {
                "text": f"💳 Bayar via QRIS (Rp {final_price:,})",
                "callback_data": f"pay_bot_qris_{months}",
                "style": "success",
                "emoji": 5375296873982604963,
            }
        ],
        [
            {
                "text": "◀️ Kembali",
                "callback_data": "start",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)

    return (text, btn)


@command(lambda ctx: events.CallbackQuery(pattern=b"^create_bot$"))
async def create_bot_callback(client, event):
    em = client.ns.emoji
    all_bots_data = await ctx.db.getBots(is_token=True)

    if len(all_bots_data) >= 25:
        text_warning = (
            f"{em.cross_mark} <b>Kapasitas Bot Penuh!</b>\n\n"
            f"Maaf, server saat ini sudah mencapai batas maksimal pembuatan bot (25 Bot). "
            f"Silakan coba lagi nanti."
        )
        layout = [
            [
                {
                    "text": "◀️ Kembali",
                    "callback_data": "start",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        return await event.edit(text_warning, buttons=btn, parse_mode="html")

    sender = await event.get_sender()
    user_expiry_str = await ctx.db.getVars(sender.id, "user_expiry_date")

    if user_expiry_str:
        expiry_date = datetime.fromisoformat(user_expiry_str)
        if expiry_date > datetime.now(timezone.utc):
            text = (
                f"{em.white_check_mark} <b>Anda Sudah Berlangganan!</b>\n\n"
                f"Anda sudah memiliki akses untuk membuat bot. "
                f"Tekan tombol di bawah untuk memulai proses pembuatan."
            )
            layout = [
                [
                    {
                        "text": "🚀 Lanjutkan Membuat Bot",
                        "callback_data": "start_creation_process",
                        "style": "primary",
                        "emoji": 5445284980978621387,
                    }
                ],
                [
                    {
                        "text": "◀️ Kembali",
                        "callback_data": "start",
                        "style": "primary",
                        "emoji": 5373098009640836781,
                    }
                ],
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            return await event.edit(text, buttons=btn, parse_mode="html")

    text, btn = await get_bot_purchase_panel(client, sender.id, 1)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^adjust_bot_month_"))
async def adjust_bot_month_callback(client, event):
    payload = event.data.decode("utf-8")
    months = int(payload.split("_")[-1])
    sender = await event.get_sender()

    if 1 <= months <= 12:
        text, btn = await get_bot_purchase_panel(client, sender.id, months)
        await event.edit(text, buttons=btn, parse_mode="html")
    else:
        await event.answer("Durasi minimal 1 bulan dan maksimal 12 bulan.", alert=True)


@command(lambda ctx: events.CallbackQuery(pattern=b"^pay_bot_qris_"))
async def proceed_bot_payment_callback(client, event):
    sender = await event.get_sender()
    payload = event.data.decode("utf-8")
    months = int(payload.split("_")[-1])
    em = client.ns.emoji

    await event.edit(
        f"{em.hourglass} <b>Sedang Memproses...</b>\nMohon tunggu sebentar.",
        parse_mode="html",
    )

    saweria_user_id = await ctx.db.getVars(client.uid, "SAWERIA_USER_ID")
    if not saweria_user_id:
        return await event.edit("Maaf, layanan pembayaran saat ini tidak tersedia.")

    _, _, amount = calculate_bot_price(months)
    fakeinfo = client.ns.utils.faker.generate()

    try:
        (
            qr_string,
            transaction_id,
            qr_image_stream,
            amount_raw,
        ) = await client.services.saweria.create_payment(
            user_id=saweria_user_id,
            amount=int(amount),
            name=f"User-{sender.id}",
            email=fakeinfo.email,
            message=f"Akses Buat Bot VVIP {months} bulan",
            creator_name=client.me.username,
        )
        order_data = f"{months}|{amount_raw}"
        await ctx.db.setVars(client.uid, transaction_id, order_data)

        caption = (
            f"{em.white_check_mark} <b>Pembayaran Siap Dilakukan!</b>\n\n"
            f"Silakan scan QRIS di atas untuk membayar. Setelah itu, tekan tombol "
            f"<b>Konfirmasi Pembayaran</b>.\n\n"
            f"╭─ <b>Detail Tagihan</b>\n"
            f"│\n"
            f"├─ {em.shopping_bags} <b>Produk:</b> Akses Buat Bot {months} Bulan (Langganan)\n"
            f"├─ {em.money_bag} <b>Jumlah:</b> <code>Rp {amount_raw:,}</code>\n"
            f'├─ <b>Order ID:</b> <a href="https://saweria.co/qris/{transaction_id}">{transaction_id}</a>\n'
            f"│\n"
            f"╰─ {em.down_pointing} <b>Jika sudah membayar, silakan klik tombol di bawah ini.</b>\n"
        )
        layout = [
            [
                {
                    "text": "✅ Konfirmasi Pembayaran",
                    "callback_data": f"confirm_bot_payment_{transaction_id}",
                    "style": "success",
                    "emoji": 5427009714745517609,
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await event.delete()
        await client.send_message(
            sender.id, caption, file=qr_image_stream, buttons=btn, parse_mode="html"
        )
    except Exception as e:
        await client.send_message(
            sender.id,
            f"{em.cross_mark} <b>Terjadi Kesalahan</b>\n<pre>{e}</pre>",
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^confirm_bot_payment_"))
async def confirm_bot_payment_callback(client, event):
    payload = event.data.decode("utf-8")
    transaction_id = payload.split("_")[-1]
    sender = await event.get_sender()
    em = client.ns.emoji

    order_data_str = await ctx.db.getVars(client.uid, transaction_id)
    if not order_data_str:
        return await event.answer(
            "% Invoice ini sudah tidak valid atau telah selesai.", alert=True
        )

    months_str, amount_raw_str = order_data_str.split("|")
    months = int(months_str)
    amount_raw = int(amount_raw_str)

    try:
        is_paid = await client.services.saweria.check_paid_status(transaction_id)
        if is_paid:
            await ctx.db.removeVars(client.uid, transaction_id)
            expiry_date = datetime.now(timezone.utc) + timedelta(days=30 * months)
            await ctx.db.setVars(sender.id, "user_expiry_date", expiry_date.isoformat())

            await event.delete()

            success_text = (
                f"{em.white_check_mark} <b>Pembayaran Berhasil!</b>\n\n"
                f"Terima kasih! Langganan Anda untuk membuat bot selama "
                f"<b>{months} bulan</b> telah diaktifkan."
            )
            layout = [
                [
                    {
                        "text": "🚀 Lanjutkan Membuat Bot",
                        "callback_data": "start_creation_process",
                        "style": "primary",
                        "emoji": 5445284980978621387,
                    }
                ]
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(
                sender.id, success_text, buttons=btn, parse_mode="html"
            )

            owner_notif = (
                f"{em.money_bag} <b>Langganan Akses Baru!</b>\n\n"
                f"<b>Pengguna:</b> {client.ns.telegram.arg.getMention(sender)}\n"
                f"<b>Durasi:</b> {months} bulan\n"
                f"<b>Jumlah:</b> <code>Rp {amount_raw:,}</code>"
            )
            await client.send_message(ctx.owner_id, owner_notif, parse_mode="html")
        else:
            await event.answer(
                "❌ Pembayaran belum terdeteksi. Silakan coba lagi nanti.",
                alert=True,
            )
    except Exception as e:
        await event.answer(f"❌ Terjadi Kesalahan: {e}", alert=True)


@command(lambda ctx: events.CallbackQuery(pattern=b"^start_creation_process$"))
async def start_creation_process_callback(client, event):
    sender = await event.get_sender()
    user_id = sender.id
    em = client.ns.emoji

    expiry_date_str = await ctx.db.getVars(user_id, "user_expiry_date")
    if not expiry_date_str or datetime.fromisoformat(expiry_date_str) < datetime.now(
        timezone.utc
    ):
        return await event.answer(
            "Langganan Anda tidak valid atau telah berakhir.", alert=True
        )

    all_bots_data = await ctx.db.getBots(is_token=True)
    if len(all_bots_data) >= 30:
        return await event.answer(
            "Kapasitas bot sudah penuh (30 Bot). Silakan buat nanti.", alert=True
        )

    await event.delete()
    try:
        api_id_msg = await client.ask(
            user_id,
            f"{em.lock_with_key} <b>1/3: Masukkan API ID Anda.</b>\nDapatkan dari my.telegram.org.\n\nKetik <code>/batal</code> untuk membatalkan.",
            parse_mode="html",
        )
        api_id = api_id_msg.text.strip()

        api_hash_msg = await client.ask(
            user_id,
            f"{em.lock_with_key} <b>2/3: Masukkan API Hash Anda.</b>\nDapatkan dari my.telegram.org.\n\nKetik <code>/batal</code> untuk membatalkan.",
            parse_mode="html",
        )
        api_hash = api_hash_msg.text.strip()

        token_msg = await client.ask(
            user_id,
            f"{em.robot} <b>3/3: Masukkan Bot Token Anda.</b>\nDapatkan dari @BotFather.\n\nKetik <code>/batal</code> untuk membatalkan.",
            parse_mode="html",
        )
        token = token_msg.text.strip()

        msg = await client.send_message(
            user_id,
            f"{em.mag} <code>Memverifikasi data &amp; token...</code>",
            parse_mode="html",
        )
        new_bot_name = await client.ns.telegram.arg.getNamebot(token)

        if "invalid" in [new_bot_name]:
            raise ValueError("Token bot yang Anda masukkan tidak valid.")

        await msg.edit(
            f"{em.white_check_mark} Bot <b>{new_bot_name.first_name}</b> valid dan sedang disimpan. "
            f"{em.rocket} <code>Memulai bot...</code>",
            parse_mode="html",
        )
        new_bot_id = int(token.split(":", 1)[0])
        bot_data = {
            "name": str(new_bot_id),
            "api_id": api_id,
            "api_hash": api_hash,
            "bot_token": token,
        }

        await ctx.manager.start_bot(bot_data)
        await ctx.db.saveBot(new_bot_id, api_id, api_hash, token, is_token=True)
        await ctx.db.setVars(new_bot_id, "bot_expiration_date", expiry_date_str)
        await ctx.db.setVars(new_bot_id, "owner_id", user_id)
        await ctx.db.removeVars(user_id, "user_expiry_date")

        await msg.edit(
            f"{em.party_popper} <b>Selamat!</b> Bot <b>{new_bot_name.first_name}</b> berhasil dibuat dan aktif.",
            parse_mode="html",
        )
    except client.userCancel:
        await client.send_message(
            user_id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        await client.send_message(
            user_id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses telah dibatalkan otomatis.",
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(
            user_id,
            f"{em.cross_mark} <b>Error Pembuatan Bot:</b> <code>{e}</code>",
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^list_my_bots"))
async def list_my_bots_callback(client, event):
    sender = await event.get_sender()
    user_id = sender.id
    em = client.ns.emoji
    my_bots = []

    all_bots_data = await ctx.db.getBots(is_token=True)
    for b in all_bots_data:
        owner = await ctx.db.getVars(int(b["name"]), "owner_id")
        if (owner or 0) == user_id:
            my_bots.append(b)

    if not my_bots:
        return await event.answer(
            "Anda belum memiliki bot. Tekan 'Buat Bot' untuk memulai.", alert=True
        )

    payload = event.data.decode("utf-8")
    parts = payload.split("_")
    page = int(parts[-1]) if len(parts) > 3 and parts[-1].isdigit() else 0

    total_pages = len(my_bots)
    page = (page + total_pages) % total_pages
    bot_data = my_bots[page]
    bot_id = int(bot_data["name"])

    bot_name = f"ID {bot_id} (Offline)"
    bot_username = "N/A"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected():
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username
    except Exception:
        bot_name = f"ID {bot_id} (Error)"

    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    days_left = (
        (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days
        if exp_date_str
        else "N/A"
    )

    text = (
        f"{em.card_index_dividers} <b>Daftar Bot Saya ({page + 1}/{total_pages})</b>\n\n"
        f"• <b>Nama Bot:</b> {bot_name}\n"
        f"• <b>ID Bot:</b> <code>{bot_id}</code>\n"
        f"• <b>Username Bot:</b> @{bot_username}\n"
        f"• <b>Sisa Aktif:</b> <code>{days_left}</code> hari"
    )

    layout = []
    pagination_row = []

    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages
        pagination_row.extend(
            [
                {
                    "text": "« Sebelumnya",
                    "callback_data": f"list_my_bots_{prev_page}",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                },
                {
                    "text": "Selanjutnya »",
                    "callback_data": f"list_my_bots_{next_page}",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                },
            ]
        )

    if pagination_row:
        layout.append(pagination_row)

    layout.extend(
        [
            [
                {
                    "text": f"🔧 Kelola {bot_name}",
                    "callback_data": f"manage_bot {bot_id}",
                    "style": "primary",
                    "emoji": 5449428597922079323,
                }
            ],
            [
                {
                    "text": "◀️ Kembali",
                    "callback_data": "start",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^manage_bot "))
async def manage_bot_callback(client, event):
    payload = event.data.decode("utf-8")
    bot_id_to_manage = int(payload.split(" ", 1)[1])
    sender = await event.get_sender()
    user_id = sender.id
    em = client.ns.emoji

    owner_of_target_bot = await ctx.db.getVars(bot_id_to_manage, "owner_id") or 0
    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await event.answer("Ini bukan bot milik Anda.", alert=True)

    bot_name = f"ID {bot_id_to_manage}"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected():
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    exp_date_str = await ctx.db.getVars(bot_id_to_manage, "bot_expiration_date")
    days_left_text = "Tidak diatur"
    if exp_date_str:
        days_left = (
            datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)
        ).days
        days_left_text = f"{days_left} hari"

    layout = [
        [
            {
                "text": "➕ Minta Perpanjangan",
                "callback_data": f"request_extend_duration {bot_id_to_manage}",
                "style": "success",
                "emoji": 5226945370684140473,
            }
        ],
        [
            {
                "text": f"🗑️ Hapus Bot Ini",
                "callback_data": f"confirm_delete_bot {bot_id_to_manage}",
                "style": "danger",
                "emoji": 5229113891081956317,
            }
        ],
        [
            {
                "text": "◀️ Kembali ke Daftar Bot",
                "callback_data": "list_my_bots_0",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ],
    ]

    text = (
        f"{em.toolbox} <b>Kelola Bot: {bot_name}</b>\n\n"
        f"<b>ID Bot:</b> <code>{bot_id_to_manage}</code>\n"
        f"<b>Sisa Masa Aktif:</b> <code>{days_left_text}</code>\n\n"
        f"Pilih tindakan yang ingin Anda lakukan:"
    )

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^request_extend_duration "))
async def request_extend_duration_callback(client, event):
    payload = event.data.decode("utf-8")
    bot_id_to_request = int(payload.split(" ", 1)[1])
    sender = await event.get_sender()
    em = client.ns.emoji

    bot_name = f"ID {bot_id_to_request}"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_request)
        if bot_instance and bot_instance.is_connected():
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    try:
        main_bot_client = ctx.manager.main_bot_client
        if not main_bot_client or not main_bot_client.is_connected():
            raise ConnectionError("Bot utama sedang tidak aktif.")

        txt_owner = (
            f"{em.bell} <b>Permintaan Perpanjangan Durasi</b>\n\n"
            f"<b>Pengguna:</b> {main_bot_client.ns.telegram.arg.getMention(sender)} "
            f"(<code>{sender.id}</code>)\n"
            f"<b>Bot:</b> <b>{bot_name}</b> (<code>{bot_id_to_request}</code>)\n\n"
            f"Setujui untuk menambah masa aktif bot ini sebanyak 30 hari."
        )

        layout_owner = [
            [
                {
                    "text": "✅ Setujui (+30 Hari)",
                    "callback_data": f"approve_extension {bot_id_to_request} {sender.id}",
                    "style": "success",
                    "emoji": 5427009714745517609,
                },
                {
                    "text": "❌ Tolak Permintaan",
                    "callback_data": f"close_req {bot_id_to_request} {sender.id}",
                    "style": "danger",
                    "emoji": 5465665476971471368,
                },
            ]
        ]
        btn_owner = main_bot_client.ns.telegram.button.build_button_grid(layout_owner)
        await main_bot_client.send_message(
            ctx.owner_id, txt_owner, buttons=btn_owner, parse_mode="html"
        )

        await event.answer(
            "✅ Permintaan perpanjangan telah dikirim ke Owner Utama.",
            alert=True,
        )
    except Exception as e:
        await event.answer(f"❌ Gagal mengirim permintaan ke Owner: {e}", alert=True)


@command(lambda ctx: events.CallbackQuery(pattern=b"^approve_extension "))
async def owner_approve_extension_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if sender.id != ctx.owner_id:
        return await event.answer("Hanya Owner Utama yang bisa menyetujui.", alert=True)

    try:
        payload = event.data.decode("utf-8")
        _, bot_id_str, requester_id_str = payload.split()
        bot_id_to_extend = int(bot_id_str)
        requester_id = int(requester_id_str)
        days_to_add = 30

        exp_date_str = await ctx.db.getVars(bot_id_to_extend, "bot_expiration_date")
        current_exp_date = (
            datetime.fromisoformat(exp_date_str)
            if exp_date_str
            else datetime.now(timezone.utc)
        )
        new_exp_date = current_exp_date + timedelta(days=days_to_add)

        await ctx.db.setVars(
            bot_id_to_extend, "bot_expiration_date", new_exp_date.isoformat()
        )
        await event.edit(
            f"{em.white_check_mark} <b>Persetujuan Berhasil!</b>\n"
            f"Durasi untuk bot <code>{bot_id_to_extend}</code> telah ditambah "
            f"<b>{days_to_add} hari</b>.",
            parse_mode="html",
        )

        try:
            bot_instance = ctx.manager.running_bots.get(bot_id_to_extend)
            bot_name = f"ID {bot_id_to_extend}"
            if bot_instance and bot_instance.is_connected():
                bot_name = bot_instance.me.first_name

            await client.send_message(
                requester_id,
                f"{em.party_popper} <b>Kabar Baik!</b>\n\n"
                f"Permintaan perpanjangan Anda untuk bot <b>{bot_name}</b> telah disetujui.",
                parse_mode="html",
            )
        except Exception as e:
            ctx.log.print(f"Gagal kirim notif persetujuan ke {requester_id}: {e}")
    except Exception as e:
        await event.edit(
            f"{em.cross_mark} Gagal menyetujui permintaan: <code>{e}</code>",
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^close_req "))
async def owner_close_request_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if sender.id != ctx.owner_id:
        return await event.answer(
            "Hanya Owner Utama yang bisa melakukan ini.", alert=True
        )

    try:
        await event.edit(
            f"{em.cross_mark} Permintaan telah ditolak/ditutup oleh Owner Utama.",
            parse_mode="html",
        )
    except Exception:
        pass


@command(lambda ctx: events.CallbackQuery(pattern=b"^confirm_delete_bot "))
async def confirm_delete_bot_callback(client, event):
    payload = event.data.decode("utf-8")
    bot_id_to_manage = int(payload.split(" ", 1)[1])
    em = client.ns.emoji

    bot_name = f"ID {bot_id_to_manage}"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected():
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    text = (
        f"{em.anger} <b>Konfirmasi Penghapusan</b>\n\n"
        f"Anda yakin ingin menghapus bot <b>{bot_name}</b> (<code>{bot_id_to_manage}</code>) secara permanen?\n\n"
        f"<i>Semua data (member, paket, pengaturan) bot ini akan hilang dan tindakan ini tidak dapat diurungkan.</i>"
    )

    layout = [
        [
            {
                "text": "✅ Ya, Saya Yakin Hapus",
                "callback_data": f"do_delete_bot {bot_id_to_manage}",
                "style": "success",
                "emoji": 5427009714745517609,
            },
            {
                "text": "❌ Tidak, Batalkan",
                "callback_data": f"manage_bot {bot_id_to_manage}",
                "style": "danger",
                "emoji": 5465665476971471368,
            },
        ]
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^do_delete_bot "))
async def do_delete_bot_callback(client, event):
    payload = event.data.decode("utf-8")
    bot_id_to_manage = int(payload.split(" ", 1)[1])
    sender = await event.get_sender()
    user_id = sender.id
    em = client.ns.emoji

    owner_of_target_bot = await ctx.db.getVars(bot_id_to_manage, "owner_id") or 0
    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await event.answer("Anda tidak berhak menghapus bot ini.", alert=True)

    await event.edit(
        f"{em.hourglass} Sedang menghentikan dan menghapus bot...",
        parse_mode="html",
    )

    try:
        await ctx.manager.stop_bot(bot_id_to_manage)
        await ctx.db.removeBot(bot_id_to_manage)
        await ctx.db.removeAllVars(bot_id_to_manage)

        ctx.log.print(
            f"Bot {bot_id_to_manage} telah dihapus oleh owner-nya ({user_id})."
        )

        layout = [
            [
                {
                    "text": "◀️ Kembali ke Daftar Bot",
                    "callback_data": "list_my_bots_0",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await event.edit(
            f"{em.white_check_mark} <b>Penghapusan Berhasil!</b>\n"
            f"Bot <code>{bot_id_to_manage}</code> beserta datanya telah dihapus dari sistem.",
            buttons=btn,
            parse_mode="html",
        )
    except Exception as e:
        await event.edit(
            f"{em.cross_mark} Terjadi kesalahan saat menghapus bot: <code>{e}</code>",
            parse_mode="html",
        )
