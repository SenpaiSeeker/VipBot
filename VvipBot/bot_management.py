from . import *

BASE_PRICE_BOT = 75000


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
    (total, discount, final_price) = calculate_bot_price(months)
    text = "**<emoji id=6129870117619634982>💳</emoji> Beli Akses Pembuatan Bot**\n\nDapatkan akses untuk membuat bot VVIP Anda sendiri dengan berlangganan.\n\nHarga: `Rp {price}/bulan`\n\n**Diskon:**\n• 3+ Bulan: 10%\n• 6+ Bulan: 20%\n\n**Pilihan Anda:**\n• Durasi: **{months} bulan**\n• Harga Normal: `Rp {total}`\n• Diskon: `{discount}`\n• **Total Bayar: `Rp {final}`**".format(
        price=f"{BASE_PRICE_BOT:,}",
        months=months,
        total=f"{total:,}",
        discount=f"-Rp {discount:,}",
        final=f"{final_price:,}",
    )
    layout = [
        [
            {"text": "➖", "callback_data": f"adjust_bot_month_{months - 1}"},
            {"text": f"{months} {'Bulan'}", "callback_data": "noop"},
            {"text": "➕", "callback_data": f"adjust_bot_month_{months + 1}"},
        ],
        [
            {
                "text": "Bayar via QRIS (Rp {final})".format(final=f"{final_price:,}"),
                "callback_data": f"pay_bot_qris_{months}",
            }
        ],
        [{"text": "• Kembali •", "callback_data": "start"}],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)
    return (text, btn)


@command(lambda ctx: filters.regex("^create_bot$"), handler_type="callback")
async def create_bot_callback(client, callback_query):
    user_id = callback_query.from_user.id
    user_expiry_str = await ctx.db.getVars(user_id, "user_expiry_date")
    if user_expiry_str:
        expiry_date = datetime.fromisoformat(user_expiry_str)
        if expiry_date > datetime.now(timezone.utc):
            text = "<emoji id=6296367896398399651>✅</emoji> **Anda Sudah Berlangganan!**\n\nAnda sudah memiliki akses untuk membuat bot. Tekan tombol di bawah untuk memulai proses pembuatan."
            layout = [
                [
                    {
                        "text": "▶️ Lanjutkan Membuat Bot",
                        "callback_data": "start_creation_process",
                    }
                ],
                [{"text": "• Kembali •", "callback_data": "start"}],
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            return await callback_query.edit_message_caption(text, reply_markup=btn)
    (text, btn) = await get_bot_purchase_panel(client, user_id, 1)
    await callback_query.edit_message_caption(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^adjust_bot_month_(\\d+)"), handler_type="callback")
async def adjust_bot_month_callback(client, callback_query):
    months = int(callback_query.data.split("_")[-1])
    if 1 <= months <= 12:
        (text, btn) = await get_bot_purchase_panel(
            client, callback_query.from_user.id, months
        )
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.answer(
            "Durasi minimal 1 bulan dan maksimal 12 bulan.", show_alert=True
        )


@command(lambda ctx: filters.regex("^pay_bot_qris_(\\d+)"), handler_type="callback")
async def proceed_bot_payment_callback(client, callback_query):
    user_id = callback_query.from_user.id
    months = int(callback_query.data.split("_")[-1])
    await callback_query.edit_message_caption(
        "<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar."
    )
    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    if not saweria_user_id:
        return await callback_query.edit_message_caption(
            "Maaf, layanan pembayaran saat ini tidak tersedia."
        )
    (_, _, amount) = calculate_bot_price(months)
    fakeinfo = client.ns.utils.faker.generate()
    try:
        (qr_string, transaction_id, qr_image_stream, amount_raw) = (
            await client.services.saweria.create_payment(
                user_id=saweria_user_id,
                amount=int(amount),
                name=f"User-{user_id}",
                email=fakeinfo.email,
                message=f"Akses Buat Bot VVIP {months} bulan",
                creator_name=client.me.username,
            )
        )
        order_data = f"{months}|{amount_raw}"
        await ctx.db.setVars(client.me.id, transaction_id, order_data)
        caption = "**<emoji id=6296367896398399651>✅</emoji> Pembayaran Siap Dilakukan!**\n\nSilakan scan QRIS di atas untuk membayar. Setelah itu, tekan tombol **Konfirmasi Pembayaran**.\n\n╭─ **Detail Tagihan**\n│\n├─ <emoji id=5373052667671093676>🛍️</emoji> **Produk:** {name} ({type})\n├─ <emoji id=6129870117619634982>💳</emoji> **Jumlah:** `Rp {amount}`\n├─ <emoji id=6269253325477123346>🆔</emoji> **Order ID:** {id}\n│\n╰─ <emoji id=5470177992950946662>👇</emoji> **Jika sudah membayar, silakan klik tombol di bawah ini.**\n".format(
            name=f"Akses Buat Bot {months} Bulan",
            type="Langganan",
            amount=f"{amount_raw:,}",
            id=f"[{transaction_id}](https://saweria.co/qris/{transaction_id})",
        )
        layout = [
            [
                {
                    "text": "✅ Konfirmasi Pembayaran",
                    "callback_data": f"confirm_bot_payment_{transaction_id}",
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await callback_query.message.delete()
        await client.send_photo(
            user_id, qr_image_stream, caption=caption, reply_markup=btn
        )
    except Exception as e:
        await client.send_message(
            user_id,
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
        )


@command(
    lambda ctx: filters.regex("^confirm_bot_payment_(.+)"), handler_type="callback"
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
    (months_str, amount_raw_str) = order_data_str.split("|")
    months = int(months_str)
    amount_raw = int(amount_raw_str)
    try:
        is_paid = await client.services.saweria.check_paid_status(transaction_id)
        if is_paid:
            await ctx.db.removeVars(client.me.id, transaction_id)
            expiry_date = datetime.now(timezone.utc) + timedelta(days=30 * months)
            await ctx.db.setVars(user.id, "user_expiry_date", expiry_date.isoformat())
            await callback_query.message.delete()
            success_text = "<emoji id=6296367896398399651>✅</emoji> **Pembayaran Berhasil!**\n\nTerima kasih! Langganan Anda untuk membuat bot selama **{months} bulan** telah diaktifkan.".format(
                months=months
            )
            layout = [
                [
                    {
                        "text": "▶️ Lanjutkan Membuat Bot",
                        "callback_data": "start_creation_process",
                    }
                ]
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(user.id, success_text, reply_markup=btn)
            owner_notif = "<emoji id=5375296873982604963>💰</emoji> **Langganan Akses Baru!**\n\n**Pengguna:** {mention}\n**Durasi:** {months} bulan\n**Jumlah:** `Rp {amount}`".format(
                mention=client.ns.telegram.arg.getMention(user),
                months=months,
                amount=f"{amount_raw:,}",
            )
            await client.send_message(ctx.owner_id, owner_notif)
        else:
            await callback_query.answer(
                "❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah beberapa saat.",
                show_alert=True,
            )
    except Exception as e:
        await callback_query.answer(
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
            show_alert=True,
        )


@command(lambda ctx: filters.regex("^start_creation_process$"), handler_type="callback")
async def start_creation_process_callback(client, callback_query):
    user_id = callback_query.from_user.id
    expiry_date_str = await ctx.db.getVars(user_id, "user_expiry_date")
    if not expiry_date_str or datetime.fromisoformat(expiry_date_str) < datetime.now(
        timezone.utc
    ):
        return await callback_query.answer(
            "Langganan Anda tidak valid atau telah berakhir.", show_alert=True
        )
    await callback_query.message.delete()
    try:

        def ask(text):
            return client.ask(
                user_id,
                f'''{text}{"""

Ketik `/batal` untuk membatalkan."""}''',
                timeout=600,
            )

        api_id_msg = await ask(
            "**<emoji id=5472308992514464048>🔐</emoji> 1/3: Masukkan API ID Anda.**\nDapatkan dari my.telegram.org."
        )
        if api_id_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        api_id = api_id_msg.text
        api_hash_msg = await ask(
            "**<emoji id=5472308992514464048>🔐</emoji> 2/3: Masukkan API Hash Anda.**\nDapatkan dari my.telegram.org."
        )
        if api_hash_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        api_hash = api_hash_msg.text
        token_msg = await ask(
            "**<emoji id=5372981976804366741>🤖</emoji> 3/3: Masukkan Bot Token Anda.**\nDapatkan dari @BotFather."
        )
        if token_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        token = token_msg.text
        msg = await client.send_message(
            user_id,
            "<emoji id=5188217332748527444>🔍</emoji> `Memverifikasi data & token...`",
        )
        new_bot_name = await client.ns.telegram.arg.getNamebot(token)
        if "invalid" in [new_bot_name]:
            raise ValueError("Token bot yang Anda masukkan tidak valid.")
        await msg.edit(
            "<emoji id=6296367896398399651>✅</emoji> Bot '{name}' valid dan sedang disimpan. `<emoji id=5445284980978621387>🚀</emoji> Memulai bot...`".format(
                name=new_bot_name.first_name
            )
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
            "<emoji id=5436040291507247633>🎉</emoji> **Selamat!** Bot **{name}** berhasil dibuat dan aktif selama **30 hari**.".format(
                name=new_bot_name.first_name
            )
        )
    except listen.UserCancelled:
        await client.send_message(
            user_id, "<emoji id=6298671811345254603>🚫</emoji> **Proses Dibatalkan**"
        )
    except asyncio.TimeoutError:
        await client.send_message(
            user_id,
            "<emoji id=5413704112220949842>⏰</emoji> **Waktu Habis**\nProses telah dibatalkan otomatis.",
        )
    except Exception as e:
        await client.send_message(
            user_id,
            "<emoji id=6298671811345254603>❌</emoji> **Error Pembuatan Bot:** `{e}`".format(
                e=e
            ),
        )


@command(lambda ctx: filters.regex("^list_my_bots(_\\d+)?$"), handler_type="callback")
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
            "Anda belum memiliki bot. Tekan 'Buat Bot' untuk memulai.", show_alert=True
        )
    parts = callback_query.data.split("_")
    page = int(parts[-1]) if len(parts) > 2 and parts[-1].isdigit() else 0
    total_pages = len(my_bots)
    page = (page + total_pages) % total_pages
    bot_data = my_bots[page]
    bot_id = int(bot_data["name"])
    bot_name = f"ID {bot_id} ({'(Offline)'})"
    bot_username = "N/A"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username
    except Exception:
        bot_name = f"ID {bot_id} ({'(Error)'})"
    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    days_left = (
        (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days
        if exp_date_str
        else "N/A"
    )
    text = "**<emoji id=6283073379184415506>📦</emoji> Daftar Bot Saya ({page}/{total})**\n\n• **Nama Bot:** {bot_name}\n• **ID Bot:** `{bot_id}`\n• **Username Bot:** @{username}\n• **Sisa Aktif:** `{days_left}` hari".format(
        page=page + 1,
        total=total_pages,
        bot_name=bot_name,
        bot_id=bot_id,
        username=bot_username,
        days_left=days_left,
    )
    layout = []
    pagination_row = []
    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages
        pagination_row.extend(
            [
                {"text": "« Sebelumnya", "callback_data": f"list_my_bots_{prev_page}"},
                {"text": "Selanjutnya »", "callback_data": f"list_my_bots_{next_page}"},
            ]
        )
    if pagination_row:
        layout.append(pagination_row)
    layout.extend(
        [
            [
                {
                    "text": "⚙️ Kelola {name}".format(name=bot_name),
                    "callback_data": f"manage_bot {bot_id}",
                }
            ],
            [{"text": "• Kembali •", "callback_data": "start"}],
        ]
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^manage_bot\\s(\\d+)"), handler_type="callback")
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
        days_left_text = f"{days_left} {'hari'}"
    layout = [
        [
            {
                "text": "➕ Minta Perpanjangan",
                "callback_data": f"request_extend_duration {bot_id_to_manage}",
            }
        ],
        [
            {
                "text": "🗑️ Hapus Bot Ini",
                "callback_data": f"confirm_delete_bot {bot_id_to_manage}",
            }
        ],
        [{"text": "⬅️ Kembali ke Daftar Bot", "callback_data": "list_my_bots_0"}],
    ]
    text = "**<emoji id=6257780484281997093>⚙️</emoji> Kelola Bot: {name}**\n\n**ID Bot:** `{id}`\n**Sisa Masa Aktif:** `{days_left}`\n\nPilih tindakan yang ingin Anda lakukan:".format(
        name=bot_name, id=bot_id_to_manage, days_left=days_left_text
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


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
        txt_owner = "**<emoji id=5242628160297641831>🔔</emoji> Permintaan Perpanjangan Durasi**\n\n**Pengguna:** {mention} (`{id}`)\n**Bot:** **{bot_name}** (`{bot_id}`)\n\nSetujui untuk menambah masa aktif bot ini sebanyak 30 hari.".format(
            mention=main_bot_client.ns.telegram.arg.getMention(requester),
            id=requester.id,
            bot_name=bot_name,
            bot_id=bot_id_to_request,
        )
        layout_owner = [
            [
                {
                    "text": "✅ Setujui (+30 Hari)",
                    "callback_data": f"approve_extension {bot_id_to_request} {requester.id}",
                },
                {
                    "text": "❌ Tolak Permintaan",
                    "callback_data": f"close_req {bot_id_to_request} {requester.id}",
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
            "❌ Gagal mengirim permintaan ke Owner: {e}".format(e=e), show_alert=True
        )


@command(
    lambda ctx: filters.regex("^approve_extension\\s(\\d+)\\s(\\d+)"),
    handler_type="callback",
)
async def owner_approve_extension_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa menyetujui permintaan ini.", show_alert=True
        )
    try:
        (_, bot_id_str, requester_id_str) = callback_query.data.split()
        (bot_id_to_extend, requester_id, days_to_add) = (
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
            bot_id_to_extend, "bot_expiration_date", new_exp_date.isoformat()
        )
        await callback_query.edit_message_text(
            "<emoji id=6296367896398399651>✅</emoji> **Persetujuan Berhasil!**\nDurasi untuk bot `{bot_id}` telah ditambah **{days} hari**.".format(
                bot_id=bot_id_to_extend, days=days_to_add
            )
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
                "<emoji id=5436040291507247633>🎉</emoji> **Kabar Baik!**\n\nPermintaan perpanjangan Anda untuk bot **{bot_name}** telah disetujui dan diperpanjang.".format(
                    bot_name=bot_name
                ),
            )
        except Exception as e:
            ctx.log.print(
                f"{ctx.log.YELLOW}Gagal kirim notif persetujuan ke {requester_id}: {e}"
            )
    except Exception as e:
        await callback_query.edit_message_text(
            "<emoji id=6298671811345254603>❌</emoji> Gagal menyetujui permintaan: `{e}`".format(
                e=e
            )
        )


@command(
    lambda ctx: filters.regex("^close_req\\s(\\d+)\\s(\\d+)"), handler_type="callback"
)
async def owner_close_request_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa melakukan ini.", show_alert=True
        )
    try:
        await callback_query.edit_message_text(
            "<emoji id=6298671811345254603>🚫</emoji> Permintaan telah ditolak/ditutup oleh Owner Utama."
        )
    except Exception:
        pass


@command(
    lambda ctx: filters.regex("^confirm_delete_bot\\s(\\d+)"), handler_type="callback"
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
    text = "**<emoji id=6271786398404055377>⚠️</emoji> Konfirmasi Penghapusan**\n\nAnda yakin ingin menghapus bot **{name}** (`{id}`) secara permanen?\n\n__Semua data (member, paket, pengaturan) bot ini akan hilang dan tindakan ini tidak dapat diurungkan.__".format(
        name=bot_name, id=bot_id_to_manage
    )
    layout = [
        [
            {
                "text": "✅ Ya, Saya Yakin Hapus",
                "callback_data": f"do_delete_bot {bot_id_to_manage}",
            },
            {
                "text": "❌ Tidak, Batalkan",
                "callback_data": f"manage_bot {bot_id_to_manage}",
            },
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^do_delete_bot\\s(\\d+)"), handler_type="callback")
async def do_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    owner_of_target_bot = await ctx.db.getVars(bot_id_to_manage, "owner_id") or 0
    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await callback_query.answer(
            "Anda tidak berhak menghapus bot ini.", show_alert=True
        )
    await callback_query.edit_message_caption(
        "<emoji id=5451732530048802485>⏳</emoji> Sedang menghentikan dan menghapus bot `{id}`...".format(
            bot_id=bot_id_to_manage
        )
    )
    try:
        await ctx.manager.stop_bot(bot_id_to_manage)
        await ctx.db.removeBot(bot_id_to_manage)
        await ctx.db.removeAllVars(bot_id_to_manage)
        ctx.log.print(
            f"{ctx.log.ORANGE}Bot {bot_id_to_manage} telah dihapus oleh owner-nya ({user_id})."
        )
        layout = [
            [{"text": "⬅️ Kembali ke Daftar Bot", "callback_data": "list_my_bots_0"}]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await callback_query.edit_message_caption(
            "<emoji id=6296367896398399651>✅</emoji> **Penghapusan Berhasil!**\nBot `{id}` beserta datanya telah dihapus dari sistem.".format(
                id=bot_id_to_manage
            ),
            reply_markup=btn,
        )
    except Exception as e:
        await callback_query.edit_message_caption(
            "<emoji id=6298671811345254603>❌</emoji> Terjadi kesalahan saat menghapus bot: `{e}`".format(
                e=e
            )
        )
