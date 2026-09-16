import asyncio
from datetime import datetime, timezone, timedelta

import pyrogram
from pyrogram import filters
from config import BACKUP_BOT
from helpers import listen
from . import command, ctx, is_bot_owner

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

    return total, discount, final_price


async def get_bot_purchase_panel(client, user_id, months=1):
    total, discount, final_price = calculate_bot_price(months)

    formatted_price = f"{BASE_PRICE_BOT:,}"
    formatted_total = f"{total:,}"
    formatted_discount = f"-Rp {discount:,}"
    formatted_final = f"{final_price:,}"

    text = (
        f"**{client.ns.emoji.gem} Beli Akses Pembuatan Bot**\n\n"
        f"Dapatkan akses untuk membuat bot VVIP Anda sendiri dengan berlangganan.\n\n"
        f"Harga: `Rp {formatted_price}/bulan`\n\n"
        f"**Diskon:**\n"
        f"• 3+ Bulan: 10%\n"
        f"• 6+ Bulan: 20%\n\n"
        f"**Pilihan Anda:**\n"
        f"• Durasi: **{months} bulan**\n"
        f"• Harga Normal: `Rp {formatted_total}`\n"
        f"• Diskon: `{formatted_discount}`\n"
        f"• **Total Bayar: `Rp {formatted_final}`**"
    )

    layout = [
        [
            {
                "text": "➖",
                "callback_data": f"adjust_bot_month_{months - 1}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": f"{months} Bulan",
                "callback_data": "noop",
                "style": "blue",
            },
            {
                "text": "➕",
                "callback_data": f"adjust_bot_month_{months + 1}",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            },
        ],
        [
            {
                "text": f"Bayar via QRIS (Rp {formatted_final})",
                "callback_data": f"pay_bot_qris_{months}",
                "style": "green",
                "emoji": client.ns.emoji.id("gem"),
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": "start",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    return text, btn


@command(
    lambda ctx: filters.regex("^list_my_bots(_\\d+)?$"),
    handler_type="callback",
)
async def list_my_bots_callback(client, callback_query):
    user_id = callback_query.from_user.id
    my_bots = []
    all_bots_data = await ctx.db.getBots(is_token=True)

    for b in all_bots_data:
        owner = await ctx.db.getVars(int(b["name"]), "owner_id")

        if (owner or 0) == user_id:
            my_bots.append(b)

    if not my_bots:
        return await callback_query.answer(
            "Anda belum memiliki bot. Tekan 'Buat Bot' untuk memulai.",
            show_alert=True,
        )

    parts = callback_query.data.split("_")
    page = int(parts[-1]) if len(parts) > 2 and parts[-1].isdigit() else 0

    total_pages = len(my_bots)
    page = (page + total_pages) % total_pages

    bot_data = my_bots[page]
    bot_id = int(bot_data["name"])

    bot_name = f"ID {bot_id} (Offline)"
    bot_username = "N/A"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
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
        f"**{client.ns.emoji.folder} Daftar Bot Saya ({page + 1}/{total_pages})**\n\n"
        f"• **Nama Bot:** {bot_name}\n"
        f"• **ID Bot:** `{bot_id}`\n"
        f"• **Username Bot:** @{bot_username}\n"
        f"• **Sisa Masa Aktif:** `{days_left}` hari"
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
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                },
                {
                    "text": "Selanjutnya »",
                    "callback_data": f"list_my_bots_{next_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("right_pointing"),
                },
            ]
        )

    if pagination_row:
        layout.append(pagination_row)

    layout.extend(
        [
            [
                {
                    "text": f"⚙️ Kelola {bot_name}",
                    "callback_data": f"manage_bot {bot_id}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("toolbox"),
                }
            ],
            [
                {
                    "text": "• Kembali •",
                    "callback_data": "start",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^manage_bot\\s(\\d+)"),
    handler_type="callback",
)
async def manage_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    owner_of_target_bot = await ctx.db.getVars(bot_id_to_manage, "owner_id") or 0

    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await callback_query.answer("Ini bukan bot milik Anda.", show_alert=True)

    bot_name = f"ID {bot_id_to_manage}"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected:
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
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            }
        ],
        [
            {
                "text": "🗑️ Hapus Bot Ini",
                "callback_data": f"confirm_delete_bot {bot_id_to_manage}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ],
        [
            {
                "text": "⬅️ Kembali ke Daftar Bot",
                "callback_data": "list_my_bots_0",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]

    text = (
        f"**{client.ns.emoji.toolbox} Kelola Bot: {bot_name}**\n\n"
        f"**ID Bot:** `{bot_id_to_manage}`\n"
        f"**Sisa Masa Aktif:** `{days_left_text}`\n\n"
        f"Pilih tindakan yang ingin Anda lakukan:"
    )

    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^create_bot$"),
    handler_type="callback",
)
async def create_bot_callback(client, callback_query):
    all_bots_data = await ctx.db.getBots(is_token=True)

    if len(all_bots_data) >= 25:
        backup_text = f" melalui @{BACKUP_BOT}" if BACKUP_BOT else ""

        text_warning = (
            f"{client.ns.emoji.cross_mark} **Kapasitas Bot Penuh!**\n\n"
            f"Maaf, server saat ini sudah mencapai batas maksimal pembuatan bot (25 Bot). Silakan buat bot baru{backup_text}."
        )

        layout = [
            [
                {
                    "text": "• Kembali •",
                    "callback_data": "start",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(
                text_warning, reply_markup=btn
            )
        return await callback_query.edit_message_text(text_warning, reply_markup=btn)

    user_id = callback_query.from_user.id
    user_expiry_str = await ctx.db.getVars(user_id, "user_expiry_date")

    if user_expiry_str:
        expiry_date = datetime.fromisoformat(user_expiry_str)

        if expiry_date > datetime.now(timezone.utc):
            text = (
                f"{client.ns.emoji.white_check_mark} **Anda Sudah Berlangganan!**\n\n"
                f"Anda sudah memiliki akses untuk membuat bot. Tekan tombol di bawah untuk memulai proses pembuatan."
            )

            layout = [
                [
                    {
                        "text": "▶️ Lanjutkan Membuat Bot",
                        "callback_data": "start_creation_process",
                        "style": "green",
                        "emoji": client.ns.emoji.id("rocket"),
                    }
                ],
                [
                    {
                        "text": "• Kembali •",
                        "callback_data": "start",
                        "style": "blue",
                        "emoji": client.ns.emoji.id("back_arrow"),
                    }
                ],
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)

            if callback_query.message.photo:
                return await callback_query.edit_message_caption(text, reply_markup=btn)
            return await callback_query.edit_message_text(text, reply_markup=btn)

    text, btn = await get_bot_purchase_panel(client, user_id, 1)
    await callback_query.edit_message_caption(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^adjust_bot_month_(\\d+)"),
    handler_type="callback",
)
async def adjust_bot_month_callback(client, callback_query):
    months = int(callback_query.data.split("_")[-1])

    if 1 <= months <= 12:
        text, btn = await get_bot_purchase_panel(
            client, callback_query.from_user.id, months
        )
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.answer(
            "Durasi minimal 1 bulan dan maksimal 12 bulan.",
            show_alert=True,
        )


@command(
    lambda ctx: filters.regex("^pay_bot_qris_(\\d+)"),
    handler_type="callback",
)
async def proceed_bot_payment_callback(client, callback_query):
    user_id = callback_query.from_user.id
    months = int(callback_query.data.split("_")[-1])

    await callback_query.edit_message_caption(
        f"{client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar."
    )

    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")

    if not saweria_user_id:
        return await callback_query.edit_message_caption(
            "Maaf, layanan pembayaran saat ini tidak tersedia."
        )

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
            name=f"User-{user_id}",
            email=fakeinfo.email,
            message=f"Akses Buat Bot VVIP {months} bulan",
            creator_name=client.me.username,
        )

        order_data = f"{months}|{amount_raw}"
        await ctx.db.setVars(client.me.id, transaction_id, order_data)

        caption = (
            f"**{client.ns.emoji.white_check_mark} Pembayaran Siap Dilakukan!**\n\n"
            f"Silakan scan QRIS di atas untuk membayar. Setelah itu, tekan tombol **Konfirmasi Pembayaran**.\n\n"
            f"╭─ **Detail Tagihan**\n"
            f"│\n"
            f"├─ {client.ns.emoji.shopping_bags} **Produk:** Akses Buat Bot {months} Bulan (Langganan)\n"
            f"├─ {client.ns.emoji.gem} **Jumlah:** `Rp {amount_raw:,}`\n"
            f"├─ {client.ns.emoji.id_card} **Order ID:** [{transaction_id}](https://saweria.co/qris/{transaction_id})\n"
            f"│\n"
            f"╰─ {client.ns.emoji.down_pointing} **Jika sudah membayar, silakan klik tombol di bawah ini.**\n"
        )

        layout = [
            [
                {
                    "text": "✅ Konfirmasi Pembayaran",
                    "callback_data": f"confirm_bot_payment_{transaction_id}",
                    "style": "green",
                    "emoji": client.ns.emoji.id("white_check_mark"),
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await callback_query.message.delete()

        await client.send_photo(
            user_id,
            qr_image_stream,
            caption=caption,
            reply_markup=btn,
        )

    except Exception as e:
        await client.send_message(
            user_id,
            f"{client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>{e}</pre>",
        )


@command(
    lambda ctx: filters.regex("^confirm_bot_payment_(.+)"),
    handler_type="callback",
)
async def confirm_bot_payment_callback(client, callback_query):
    transaction_id = callback_query.data.split("_")[-1]
    user = callback_query.from_user
    order_data_str = await ctx.db.getVars(client.me.id, transaction_id)

    if not order_data_str:
        return await callback_query.answer(
            "<emoji id=6271786398404055377>⚠️</emoji> Invoice ini sudah tidak valid atau telah selesai.",
            show_alert=True,
        )

    months_str, amount_raw_str = order_data_str.split("|")
    months = int(months_str)
    amount_raw = int(amount_raw_str)

    try:
        is_paid = await client.services.saweria.check_paid_status(transaction_id)

        if is_paid:
            await ctx.db.removeVars(client.me.id, transaction_id)
            expiry_date = datetime.now(timezone.utc) + timedelta(days=30 * months)

            await ctx.db.setVars(
                user.id,
                "user_expiry_date",
                expiry_date.isoformat(),
            )
            await callback_query.message.delete()

            success_text = (
                f"{client.ns.emoji.white_check_mark} **Pembayaran Berhasil!**\n\n"
                f"Terima kasih! Langganan Anda untuk membuat bot selama **{months} bulan** telah diaktifkan."
            )

            layout = [
                [
                    {
                        "text": "▶️ Lanjutkan Membuat Bot",
                        "callback_data": "start_creation_process",
                        "style": "green",
                        "emoji": client.ns.emoji.id("rocket"),
                    }
                ]
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(user.id, success_text, reply_markup=btn)

            owner_mention = client.ns.telegram.arg.getMention(user)
            formatted_amount = f"{amount_raw:,}"

            owner_notif = (
                f"{client.ns.emoji.money_bag} **Langganan Akses Baru!**\n\n"
                f"**Pengguna:** {owner_mention}\n"
                f"**Durasi:** {months} bulan\n"
                f"**Jumlah:** `Rp {formatted_amount}`"
            )
            await client.send_message(ctx.owner_id, owner_notif)
        else:
            await callback_query.answer(
                "❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah beberapa saat.",
                show_alert=True,
            )
    except Exception as e:
        await callback_query.answer(
            f"❌ Terjadi kesalahan: {e}",
            show_alert=True,
        )


@command(
    lambda ctx: filters.regex("^start_creation_process$"),
    handler_type="callback",
)
async def start_creation_process_callback(client, callback_query):
    user_id = callback_query.from_user.id
    expiry_date_str = await ctx.db.getVars(user_id, "user_expiry_date")

    if not expiry_date_str or datetime.fromisoformat(expiry_date_str) < datetime.now(
        timezone.utc
    ):
        return await callback_query.answer(
            "Langganan Anda tidak valid atau telah berakhir.",
            show_alert=True,
        )

    all_bots_data = await ctx.db.getBots(is_token=True)

    if len(all_bots_data) >= 30:
        backup_text = f" melalui @{BACKUP_BOT}" if BACKUP_BOT else ""
        return await callback_query.answer(
            f"Kapasitas bot sudah penuh (30 Bot). Silakan buat bot baru{backup_text}.",
            show_alert=True,
        )

    await callback_query.message.delete()

    try:
        def ask(text):
            return client.ask(
                user_id,
                f"{text}\n\nKetik `/batal` untuk membatalkan.",
                timeout=600,
            )

        api_id_prompt = f"**{client.ns.emoji.lock} 1/3: Masukkan API ID Anda.**\nDapatkan dari my.telegram.org."
        api_id_msg = await ask(api_id_prompt)

        if api_id_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        api_id = api_id_msg.text

        api_hash_prompt = f"**{client.ns.emoji.lock} 2/3: Masukkan API Hash Anda.**\nDapatkan dari my.telegram.org."
        api_hash_msg = await ask(api_hash_prompt)

        if api_hash_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        api_hash = api_hash_msg.text

        token_prompt = f"**{client.ns.emoji.robot} 3/3: Masukkan Bot Token Anda.**\nDapatkan dari @BotFather."
        token_msg = await ask(token_prompt)

        if token_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        token = token_msg.text

        msg = await client.send_message(
            user_id,
            f"{client.ns.emoji.mag} `Memverifikasi data & token...`",
        )

        new_bot_name = await client.ns.telegram.arg.getNamebot(token)

        if "invalid" in [new_bot_name]:
            raise ValueError("Token bot yang Anda masukkan tidak valid.")

        await msg.edit(
            f"{client.ns.emoji.white_check_mark} Bot '{new_bot_name.first_name}' valid dan sedang disimpan. "
            f"`{client.ns.emoji.rocket} Memulai bot...`"
        )

        new_bot_id = int(token.split(":", 1)[0])
        bot_data = {
            "name": str(new_bot_id),
            "api_id": api_id,
            "api_hash": api_hash,
            "bot_token": token,
        }

        await ctx.manager.start_bot(bot_data)

        await ctx.db.saveBot(
            new_bot_id,
            api_id,
            api_hash,
            token,
            is_token=True,
        )

        await ctx.db.setVars(
            new_bot_id,
            "bot_expiration_date",
            expiry_date_str,
        )

        await ctx.db.setVars(new_bot_id, "owner_id", user_id)
        await ctx.db.removeVars(user_id, "user_expiry_date")

        await msg.edit(
            f"{client.ns.emoji.party_popper} **Selamat!** Bot **{new_bot_name.first_name}** berhasil dibuat dan aktif."
        )

    except listen.UserCancelled:
        await client.send_message(
            user_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
        )
    except asyncio.TimeoutError:
        await client.send_message(
            user_id,
            f"{client.ns.emoji.alarm_clock} **Waktu Habis**\nProses telah dibatalkan otomatis.",
        )
    except Exception as e:
        await client.send_message(
            user_id,
            f"{client.ns.emoji.cross_mark} **Error Pembuatan Bot:** `{e}`",
        )


@command(
    lambda ctx: filters.regex("^request_extend_duration\\s(\\d+)"),
    handler_type="callback",
)
async def request_extend_duration_callback(client, callback_query):
    bot_id_to_request = int(callback_query.data.split(" ", 1)[1])
    requester = callback_query.from_user
    bot_name = f"ID {bot_id_to_request}"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_request)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    try:
        main_bot_client = ctx.manager.main_bot_client
        if not main_bot_client or not main_bot_client.is_connected:
            raise ConnectionError(
                "Bot utama sedang tidak aktif, tidak dapat mengirim notifikasi."
            )

        requester_mention = main_bot_client.ns.telegram.arg.getMention(requester)
        txt_owner = (
            f"**{main_bot_client.ns.emoji.bell} Permintaan Perpanjangan Durasi**\n\n"
            f"**Pengguna:** {requester_mention} (`{requester.id}`)\n"
            f"**Bot:** **{bot_name}** (`{bot_id_to_request}`)\n\n"
            f"Setujui untuk menambah masa aktif bot ini sebanyak 30 hari."
        )

        layout_owner = [
            [
                {
                    "text": "✅ Setujui (+30 Hari)",
                    "callback_data": f"approve_extension {bot_id_to_request} {requester.id}",
                    "style": "green",
                    "emoji": main_bot_client.ns.emoji.id("white_check_mark"),
                },
                {
                    "text": "❌ Tolak Permintaan",
                    "callback_data": f"close_req {bot_id_to_request} {requester.id}",
                    "style": "red",
                    "emoji": main_bot_client.ns.emoji.id("cross_mark"),
                },
            ]
        ]
        btn_owner = main_bot_client.ns.telegram.button.build_button_grid(layout_owner)

        await main_bot_client.send_message(
            ctx.owner_id, txt_owner, reply_markup=btn_owner
        )
        await callback_query.answer(
            "✅ Permintaan perpanjangan telah dikirim ke Owner Utama. Anda akan dihubungi jika disetujui.",
            show_alert=True,
        )
    except Exception as e:
        await callback_query.answer(
            f"❌ Gagal mengirim permintaan ke Owner: {e}",
            show_alert=True,
        )


@command(
    lambda ctx: filters.regex("^approve_extension\\s(\\d+)\\s(\\d+)"),
    handler_type="callback",
)
async def owner_approve_extension_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa menyetujui permintaan ini.",
            show_alert=True,
        )

    try:
        _, bot_id_str, requester_id_str = callback_query.data.split()
        bot_id_to_extend, requester_id, days_to_add = (
            int(bot_id_str),
            int(requester_id_str),
            30,
        )

        exp_date_str = await ctx.db.getVars(bot_id_to_extend, "bot_expiration_date")
        current_exp_date = (
            datetime.fromisoformat(exp_date_str)
            if exp_date_str
            else datetime.now(timezone.utc)
        )

        new_exp_date = current_exp_date + timedelta(days=days_to_add)
        await ctx.db.setVars(
            bot_id_to_extend,
            "bot_expiration_date",
            new_exp_date.isoformat(),
        )

        await callback_query.edit_message_text(
            f"{client.ns.emoji.white_check_mark} **Persetujuan Berhasil!**\n"
            f"Durasi untuk bot `{bot_id_to_extend}` telah ditambah **{days_to_add} hari**."
        )

        try:
            bot_instance = ctx.manager.running_bots.get(bot_id_to_extend)
            bot_name = (
                bot_instance.me.first_name
                if bot_instance and bot_instance.is_connected
                else f"ID {bot_id_to_extend}"
            )

            await client.send_message(
                requester_id,
                f"{client.ns.emoji.party_popper} **Kabar Baik!**\n\n"
                f"Permintaan perpanjangan Anda untuk bot **{bot_name}** telah disetujui dan diperpanjang.",
            )
        except Exception as e:
            ctx.log.print(
                f"Gagal kirim notif persetujuan ke {requester_id}: {e}"
            )
    except Exception as e:
        await callback_query.edit_message_text(
            f"{client.ns.emoji.cross_mark} Gagal menyetujui permintaan: `{e}`"
        )


@command(
    lambda ctx: filters.regex("^close_req\\s(\\d+)\\s(\\d+)"),
    handler_type="callback",
)
async def owner_close_request_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa melakukan ini.",
            show_alert=True,
        )

    try:
        await callback_query.edit_message_text(
            f"{client.ns.emoji.cross_mark} Permintaan telah ditolak/ditutup oleh Owner Utama."
        )
    except Exception:
        pass


@command(
    lambda ctx: filters.regex("^confirm_delete_bot\\s(\\d+)"),
    handler_type="callback",
)
async def confirm_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    bot_name = f"ID {bot_id_to_manage}"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    text = (
        f"**{client.ns.emoji.exclamation} Konfirmasi Penghapusan**\n\n"
        f"Anda yakin ingin menghapus bot **{bot_name}** (`{bot_id_to_manage}`) secara permanen?\n\n"
        f"__Semua data (member, paket, pengaturan) bot ini akan hilang dan tindakan ini tidak dapat diurungkan.__"
    )

    layout = [
        [
            {
                "text": "✅ Ya, Saya Yakin Hapus",
                "callback_data": f"do_delete_bot {bot_id_to_manage}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": "❌ Tidak, Batalkan",
                "callback_data": f"manage_bot {bot_id_to_manage}",
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
    lambda ctx: filters.regex("^do_delete_bot\\s(\\d+)"),
    handler_type="callback",
)
async def do_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    owner_of_target_bot = await ctx.db.getVars(bot_id_to_manage, "owner_id") or 0

    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await callback_query.answer(
            "Anda tidak berhak menghapus bot ini.",
            show_alert=True,
        )

    await callback_query.edit_message_caption(
        f"{client.ns.emoji.hourglass} Sedang menghentikan dan menghapus bot `{bot_id_to_manage}`..."
    )

    try:
        await ctx.manager.stop_bot(bot_id_to_manage)
        await ctx.db.removeBot(bot_id_to_manage)
        await ctx.db.removeAllVars(bot_id_to_manage)

        layout = [
            [
                {
                    "text": "⬅️ Kembali ke Daftar Bot",
                    "callback_data": "list_my_bots_0",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await callback_query.edit_message_caption(
            f"{client.ns.emoji.white_check_mark} **Penghapusan Berhasil!**\n"
            f"Bot `{bot_id_to_manage}` beserta datanya telah dihapus dari sistem.",
            reply_markup=btn,
        )

    except Exception as e:
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.cross_mark} Terjadi kesalahan saat menghapus bot: `{e}`"
        )