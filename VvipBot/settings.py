from . import *


@command(lambda ctx: filters.regex("^settings$"), handler_type="callback")
async def settings(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True
        )
    layout = [
        [
            {"text": "🖼️ Atur Foto Start", "callback_data": "set_start_photo"},
            {"text": "✍️ Atur Teks Start", "callback_data": "set_start_text"},
        ],
        [
            {"text": "➕ Tambah VVIP", "callback_data": "setup_listvvip"},
            {"text": "➖ Hapus VVIP", "callback_data": "delete_listvvip"},
        ],
        [
            {"text": "👥 Total Pengguna", "callback_data": "total_users_count"},
            {"text": "👥 Cek Member VVIP", "callback_data": "list_members_0"},
        ],
        [
            {"text": "🕵️ Cek Member Aktif", "callback_data": "check_active_menu_init"},
            {"text": "🔍 Cek Status Grup VVIP", "callback_data": "check_vvip_status"},
        ],
        [
            {"text": "📢 Buat Broadcast", "callback_data": "broadcast"},
            {"text": "🌟 Harga Broadcast Paid", "callback_data": "set_broadcast_price"},
        ],
        [
            {"text": "🔑 Kelola Kunci API", "callback_data": "api_settings"},
            {"text": "🎟️ Kelola Kupon", "callback_data": "manage_coupons"},
        ],
        [
            {"text": "💰 Pendapatan VIP", "callback_data": "vip_revenue_menu"},
            {"text": "⭐ Statistik Stars", "callback_data": "stats_0"},
        ],
        [{"text": "• Kembali ke Menu Utama •", "callback_data": "start"}],
    ]
    txt_content = "**<emoji id=6257780484281997093>🛠️</emoji> Panel Pengaturan Owner**\n\nSelamat datang di pusat kendali bot Anda! Silakan pilih menu di bawah untuk mengelola berbagai aspek bot."
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt_content, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt_content, reply_markup=btn)


@command(lambda ctx: filters.regex("^check_vvip_status$"), handler_type="callback")
async def check_vvip_status_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True
        )
    chat_id = callback_query.message.chat.id
    await callback_query.message.delete()
    status_msg = await client.send_message(
        chat_id,
        "<emoji id=5451732530048802485>⏳</emoji> Sedang Memeriksa Status Grup...\nMohon tunggu, proses ini mungkin memakan waktu.",
    )
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    if not vvip_list:
        return await status_msg.edit(
            "<emoji id=6298671811345254603>❌</emoji> Belum ada data VVIP."
        )
    report_text = "<emoji id=6271786398404055377>🕵️</emoji> Laporan Status Grup VVIP\n\n"
    for item in vvip_list:
        chat_id_target = item.get("chat_id_normal")
        name = item.get("name")
        try:
            chat = await client.get_chat(chat_id_target)
            if hasattr(chat, "restrictions") and chat.restrictions:
                restriction = chat.restrictions[0]
                reason_text = f"{restriction.reason}: {restriction.text}"
                report_text += "<emoji id=6283073379184415506>📦</emoji> Nama: {name}\n<emoji id=6129870117619634982>💡</emoji> Grup: {title}\n<emoji id=6298671811345254603>⛔</emoji> STATUS: BANNED/DIBATASI\n<emoji id=5334882760735598374>📝</emoji> Alasan: {reason}\n\n".format(
                    name=name, title=chat.title, reason=reason_text
                )
            else:
                link = chat.invite_link or "N/A"
                report_text += "<emoji id=6283073379184415506>📦</emoji> Nama: {name}\n<emoji id=6129870117619634982>💡</emoji> Grup: {title}\n<emoji id=5373052667671093676>🔗</emoji> Link: {link}\n<emoji id=6296367896398399651>✅</emoji> Status: Aman\n\n".format(
                    name=name, title=chat.title, link=link
                )
        except Exception:
            report_text += "<emoji id=6283073379184415506>📦</emoji> Nama: {name}\n<emoji id=6298671811345254603>❌</emoji> Error: Tidak dapat mengakses grup (ID: {chat_id}). Pastikan bot adalah admin.\n\n".format(
                name=name, chat_id=chat_id_target
            )
        if len(report_text) > 3500:
            await client.send_message(chat_id, report_text)
            report_text = ""
    if report_text:
        await client.send_message(chat_id, report_text)
    layout = [[{"text": "• Kembali ke Pengaturan •", "callback_data": "settings"}]]
    btn = client.ns.telegram.button.build_button_grid(layout)
    await status_msg.delete()
    await client.send_message(
        chat_id,
        "<emoji id=6296367896398399651>✅</emoji> Pemeriksaan Selesai.",
        reply_markup=btn,
    )


@command(lambda ctx: filters.regex("^vip_revenue_menu$"), handler_type="callback")
async def vip_revenue_menu_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    text = "**<emoji id=5375296873982604963>💰</emoji> Cek Pendapatan VIP**\n\nPilih periode waktu untuk melihat total pendapatan dari penjualan paket VIP."
    layout = [
        [
            {"text": "📅 Harian (Hari Ini)", "callback_data": "show_revenue_daily"},
            {"text": "🗓️ Mingguan (7 Hari)", "callback_data": "show_revenue_weekly"},
        ],
        [{"text": "📆 Bulanan (Bulan Ini)", "callback_data": "show_revenue_monthly"}],
        [{"text": "• Kembali ke Pengaturan •", "callback_data": "settings"}],
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
    period_text = {"daily": "Harian", "weekly": "Mingguan", "monthly": "Bulanan"}.get(
        period, "Harian"
    )
    text = "**<emoji id=5431577498364158238>📊</emoji> Laporan Pendapatan VIP**\n\n**Periode:** {period}\n\n<emoji id=5375296873982604963>💰</emoji> **Total Pendapatan:** `Rp {total}`\n<emoji id=5264727218734524899>🔄</emoji> **Jumlah Transaksi:** `{count}`".format(
        period=period_text, total=f"{total_amount:,}", count=transaction_count
    )
    layout = [[{"text": "• Kembali •", "callback_data": "vip_revenue_menu"}]]
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^set_start_photo$"), handler_type="callback")
async def set_start_photo_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    await callback_query.message.delete()
    layout = [[{"text": "• Kembali ke Pengaturan •", "callback_data": "settings"}]]
    back_btn = client.ns.telegram.button.build_button_grid(layout)
    try:
        prompt = f'''{"""<emoji id=5375074927252621134>🖼️</emoji> **Atur Foto Start**

Silakan kirim foto baru yang ingin Anda gunakan sebagai gambar di pesan /start.

Ketik `/empty` untuk menghapus foto saat ini dan kembali ke default."""}{"""

Ketik `/batal` untuk membatalkan."""}'''
        ask_photo_msg = await client.ask(chat_id, prompt, timeout=300)
        if ask_photo_msg.text:
            if ask_photo_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if ask_photo_msg.text.lower() == "/empty":
                await ctx.db.removeVars(client.me.id, "start_photo_id")
                return await client.send_message(
                    chat_id,
                    "<emoji id=6296367896398399651>✅</emoji> **Sukses!** Foto /start telah dihapus dan akan kembali ke default.",
                    reply_markup=back_btn,
                )
        if not ask_photo_msg.photo:
            return await client.send_message(
                chat_id,
                "<emoji id=6298671811345254603>❌</emoji> **Gagal:** Pesan yang dikirim bukan foto. Proses dibatalkan.",
                reply_markup=back_btn,
            )
        photo_id = ask_photo_msg.photo.sizes[-1].file_id
        await ctx.db.setVars(client.me.id, "start_photo_id", photo_id)
        await client.send_message(
            chat_id,
            "<emoji id=6296367896398399651>✅</emoji> **Sukses!** Foto /start telah berhasil diperbarui.",
            reply_markup=back_btn,
        )
    except listen.UserCancelled:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>🚫</emoji> **Proses Dibatalkan**",
            reply_markup=back_btn,
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            "<emoji id=5413704112220949842>⏰</emoji> **Waktu Habis**\nProses telah dibatalkan otomatis.",
            reply_markup=back_btn,
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
            reply_markup=back_btn,
        )


@command(lambda ctx: filters.regex("^set_start_text$"), handler_type="callback")
async def set_start_text_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    await callback_query.message.delete()
    layout = [[{"text": "• Kembali ke Pengaturan •", "callback_data": "settings"}]]
    back_btn = client.ns.telegram.button.build_button_grid(layout)
    try:
        prompt = f'''{"""<emoji id=5470060791883374114>✍️</emoji> **Atur Teks Start**

Silakan kirim teks baru untuk pesan /start. Anda dapat menggunakan variabel `{mention}` untuk menyapa pengguna.

**Contoh:** `Halo {mention}, selamat datang di bot saya!`

Ketik `/empty` untuk menghapus teks kustom dan kembali ke default."""}{"""

Ketik `/batal` untuk membatalkan."""}'''
        ask_text_msg = await client.ask(chat_id, prompt, timeout=600)
        if not ask_text_msg.text:
            return await client.send_message(
                chat_id,
                "<emoji id=6298671811345254603>❌</emoji> **Gagal:** Pesan yang dikirim tidak berisi teks. Proses dibatalkan.",
                reply_markup=back_btn,
            )
        if ask_text_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        if ask_text_msg.text.lower() == "/empty":
            await ctx.db.removeVars(client.me.id, "start_text_template")
            return await client.send_message(
                chat_id,
                "<emoji id=6296367896398399651>✅</emoji> **Sukses!** Teks /start telah dihapus dan akan kembali ke default.",
                reply_markup=back_btn,
            )
        await ctx.db.setVars(
            client.me.id, "start_text_template", ask_text_msg.text.html
        )
        await client.send_message(
            chat_id,
            "<emoji id=6296367896398399651>✅</emoji> **Sukses!** Teks /start telah berhasil diperbarui.",
            reply_markup=back_btn,
        )
    except listen.UserCancelled:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>🚫</emoji> **Proses Dibatalkan**",
            reply_markup=back_btn,
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            "<emoji id=5413704112220949842>⏰</emoji> **Waktu Habis**\nProses telah dibatalkan otomatis.",
            reply_markup=back_btn,
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
            reply_markup=back_btn,
        )


@command(lambda ctx: filters.regex("^set_broadcast_price$"), handler_type="callback")
async def set_broadcast_price_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    await callback_query.message.delete()
    layout = [[{"text": "• Kembali ke Pengaturan •", "callback_data": "settings"}]]
    back_btn = client.ns.telegram.button.build_button_grid(layout)
    try:
        prompt = f'''{"""<emoji id=5458799228719472718>🌟</emoji> **Atur Harga Broadcast Paid**

Masukkan jumlah Bintang (Stars) yang harus dibayar pengguna untuk melihat media broadcast.

Ketik `0` atau `/empty` untuk menonaktifkan fitur ini (Broadcast akan kembali normal dan gratis)."""}{"""

Ketik `/batal` untuk membatalkan."""}'''
        ask_msg = await client.ask(chat_id, prompt, timeout=300)
        if ask_msg.text:
            if ask_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if ask_msg.text.lower() in ["/empty", "0"]:
                await ctx.db.removeVars(client.me.id, "broadcast_price")
                return await client.send_message(
                    chat_id,
                    "<emoji id=6296367896398399651>✅</emoji> **Sukses!** Fitur Paid Broadcast dinonaktifkan. Broadcast akan berjalan normal seperti biasa.",
                    reply_markup=back_btn,
                )
        if not ask_msg.text.isdigit():
            raise ValueError("**Format Salah**")
        stars_amount = int(ask_msg.text)
        await ctx.db.setVars(client.me.id, "broadcast_price", stars_amount)
        await client.send_message(
            chat_id,
            "<emoji id=6296367896398399651>✅</emoji> **Sukses!** Harga broadcast telah diatur menjadi `{stars}` Stars.".format(
                stars=stars_amount
            ),
            reply_markup=back_btn,
        )
    except listen.UserCancelled:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>🚫</emoji> **Proses Dibatalkan**",
            reply_markup=back_btn,
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            "<emoji id=5413704112220949842>⏰</emoji> **Waktu Habis**\nProses telah dibatalkan otomatis.",
            reply_markup=back_btn,
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
            reply_markup=back_btn,
        )


async def _send_broadcast_message(
    client, target_user_id, source_message, broadcast_price=0
):
    caption_or_text = source_message.caption or source_message.text
    text_to_parse = caption_or_text.html if caption_or_text else ""
    (reply_markup, cleaned_text) = client.ns.telegram.button.create_inline_keyboard(
        text_to_parse
    )
    final_markup = (
        reply_markup
        if reply_markup.inline_keyboard
        else source_message.reply_markup if source_message.reply_markup else None
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
            chat_id=target_user_id, text=cleaned_text, reply_markup=final_markup
        )
    else:
        await source_message.copy(
            chat_id=target_user_id, caption=cleaned_text, reply_markup=final_markup
        )


@command(lambda ctx: filters.regex("^broadcast$"), handler_type="callback")
async def broadcast_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True
        )
    chat_id = callback_query.message.chat.id
    bot_id = client.me.id
    try:
        await callback_query.message.delete()
        prompt = f'''{"""**<emoji id=5368776520921784743>📢</emoji> Kirim Pesan Broadcast**

Silakan teruskan (forward) atau kirim pesan yang ingin Anda siarkan ke semua pengguna yang pernah memulai bot ini. Anda bisa menggunakan tombol format."""}{"""

Ketik `/batal` untuk membatalkan."""}'''
        ask_message = await client.ask(chat_id, text=prompt, timeout=600)
        if ask_message.text and ask_message.text.lower() == "/batal":
            raise listen.UserCancelled
        broadcast_price = await ctx.db.getVars(bot_id, "broadcast_price") or 0
        broadcast_price = int(broadcast_price)
        if broadcast_price > 0 and (not (ask_message.photo or ask_message.video)):
            raise ValueError(
                "<emoji id=6298671811345254603>❌</emoji> **Gagal:** Fitur Paid Broadcast sedang aktif seharga {stars} Stars. Pesan broadcast Anda HARUS berupa Foto atau Video agar bisa dikunci!".format(
                    stars=broadcast_price
                )
            )
        user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
        if not user_ids:
            return await client.send_message(
                chat_id,
                "<emoji id=6298671811345254603>❌</emoji> **Gagal:** Tidak ada pengguna untuk disiarkan.",
            )
        progress_msg = await client.send_message(
            chat_id,
            "<emoji id=6296367896398399651>✅</emoji> Memulai siaran ke `{count}` pengguna...".format(
                count=len(user_ids)
            ),
        )
        (success_count, fail_count) = (0, 0)

        async def send_to_user(target_user_id):
            nonlocal success_count, fail_count
            try:
                await _send_broadcast_message(
                    client, target_user_id, ask_message, broadcast_price
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
        return await client.send_message(
            chat_id,
            "**<emoji id=5368776520921784743>📢</emoji> Siaran Selesai!**\n<emoji id=6296367896398399651>✅</emoji> **Terkirim:** `{success}`\n<emoji id=6298671811345254603>❌</emoji> **Gagal:** `{fail}` (pengguna gagal telah dihapus dari database)".format(
                success=success_count, fail=fail_count
            ),
        )
    except listen.UserCancelled:
        await client.send_message(
            chat_id, "<emoji id=6298671811345254603>🚫</emoji> **Proses Dibatalkan**"
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            "<emoji id=5413704112220949842>⏰</emoji> **Waktu Habis**\nProses telah dibatalkan otomatis.",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
        )


@command(lambda ctx: filters.regex("^setup_listvvip$"), handler_type="callback")
async def setup_listvvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    await callback_query.message.delete()
    try:

        def ask(text):
            return client.ask(
                chat_id,
                f'''{text}{"""

Ketik `/batal` untuk membatalkan."""}''',
                timeout=600,
            )

        def validate(msg, check_func, err_msg_key):
            if msg.text and msg.text.lower() == "/batal":
                raise listen.UserCancelled
            if not check_func(msg.text):
                errors = {
                    "settings.setup_vvip.err_must_be_number": "**Input Tidak Valid!** Nilai harus berupa angka.",
                    "settings.setup_vvip.err_must_be_chat_id": "**Input Tidak Valid!** Format Chat ID salah. Harus berupa angka dan boleh diawali `-`.",
                }
                raise ValueError(errors.get(err_msg_key, "**Input tidak valid.**"))
            return msg.text

        def is_digit(t):
            return t.isdigit()

        def is_chatid(t):
            return t.lstrip("-").isdigit()

        vvip_data = {}
        vvip_data["name"] = validate(
            await ask(
                "**<emoji id=5470060791883374114>✍️</emoji> Langkah 1/8: Nama Kategori**\nContoh: `VVIP Bulanan`"
            ),
            lambda t: True,
            "",
        )
        vvip_data["price"] = int(
            validate(
                await ask(
                    "**<emoji id=5375296873982604963>💰</emoji> Langkah 2/8: Harga Normal**\nContoh: `50000` (tanpa titik atau koma)"
                ),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )
        vvip_data["duration"] = int(
            validate(
                await ask(
                    "**<emoji id=5451732530048802485>⏳</emoji> Langkah 3/8: Durasi Keanggotaan (Hari)**\nKirim `0` untuk akses permanen."
                ),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )
        vvip_data["chat_id_normal"] = int(
            validate(
                await ask(
                    "**<emoji id=6269253325477123346>🆔</emoji> Langkah 4/8: Chat ID Grup Normal**\nContoh: `-100123456789`. Ini adalah grup tujuan untuk member."
                ),
                is_chatid,
                "settings.setup_vvip.err_must_be_chat_id",
            )
        )
        vvip_data["promo_price"] = int(
            validate(
                await ask(
                    "**<emoji id=5436040291507247633>🎉</emoji> Langkah 5/8: Harga Promo**\nKirim `0` jika tidak ada harga promo."
                ),
                is_digit,
                "settings.setup_vvip.err_must_be_number",
            )
        )
        if vvip_data["promo_price"] > 0:
            vvip_data["chat_id_promo"] = int(
                validate(
                    await ask(
                        "**<emoji id=6269253325477123346>🆔</emoji> Langkah 6/8: Chat ID Grup Promo**\nDiisi jika Harga Promo > 0."
                    ),
                    is_chatid,
                    "settings.setup_vvip.err_must_be_chat_id",
                )
            )
            prompt_promo = f'''{"""**<emoji id=5334882760735598374>📝</emoji> Langkah 7/8: Teks Deskripsi Promo**
Gunakan `{name}` dan `{promo_price}`."""}{"""
Ketik `/skip` untuk menggunakan teks default."""}{"""

Ketik `/batal` untuk membatalkan."""}'''
            promo_text_msg = await client.ask(chat_id, prompt_promo, timeout=600)
            if promo_text_msg.text and promo_text_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            vvip_data["promo_text"] = (
                "" if promo_text_msg.text.lower() == "/skip" else promo_text_msg.text
            )
        else:
            (vvip_data["chat_id_promo"], vvip_data["promo_text"]) = (0, "")
        prompt_normal = f'''{"""**<emoji id=5334882760735598374>📝</emoji> Langkah 8/8: Teks Deskripsi Normal**
Gunakan `{name}` dan `{price}`."""}{"""
Ketik `/skip` untuk menggunakan teks default."""}{"""

Ketik `/batal` untuk membatalkan."""}'''
        normal_text_msg = await client.ask(chat_id, prompt_normal, timeout=600)
        if normal_text_msg.text and normal_text_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        vvip_data["normal_text"] = (
            "" if normal_text_msg.text.lower() == "/skip" else normal_text_msg.text
        )
        await ctx.db.setListVars(client.me.id, "list_vvip", vvip_data)
        await client.send_message(
            chat_id,
            "<emoji id=6296367896398399651>✅</emoji> **Sukses!**\nPaket VVIP **{name}** berhasil ditambahkan.".format(
                name=vvip_data["name"]
            ),
        )
    except listen.UserCancelled:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>🚫</emoji> Setup paket VVIP dibatalkan oleh pengguna.",
        )
    except (asyncio.TimeoutError, ValueError) as e:
        await client.send_message(
            chat_id,
            f'''{"""**Input Tidak Valid / Timeout**
Proses dibatalkan."""}\n`{e}`''',
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
        )


@command(lambda ctx: filters.regex("^delete_listvvip$"), handler_type="callback")
async def delete_listvvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    back_row = [{"text": "• Kembali ke Pengaturan •", "callback_data": "settings"}]
    if not vvip_list:
        text = "<emoji id=6296367896398399651>✅</emoji> Bagus! Tidak ada paket VVIP untuk dihapus."
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
                "text": "🗑️ Hapus {name}".format(name=name),
                "callback_data": f"delete_vvip {item_id}",
            }
        )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []
    if button_row:
        layout.append(button_row)
    layout.append(back_row)
    text = "**<emoji id=6156513311585211842>🗑️</emoji> Hapus Paket VVIP**\n\nPilih paket VVIP yang ingin Anda hapus dari daftar."
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^delete_vvip\\s(.+)"), handler_type="callback")
async def confirm_delete_vvip(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    (_, item_id) = callback_query.data.split(" ", 1)
    if not hasattr(ctx, "vip_list") or item_id not in ctx.vip_list:
        return await callback_query.answer(
            "Sesi tidak ditemukan atau kedaluwarsa. Silakan muat ulang menu.",
            show_alert=True,
        )
    name = ctx.vip_list[item_id]
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    item_to_remove = next(
        (item for item in vvip_list if item.get("name") == name), None
    )
    back_row = [
        {"text": "• Kembali ke Pengaturan •", "callback_data": "delete_listvvip"}
    ]
    if item_to_remove:
        await ctx.db.removeListVars(client.me.id, "list_vvip", item_to_remove)
        ctx.log.print(
            f"{ctx.log.ORANGE}Owner bot {client.me.id} menghapus VVIP: {name}"
        )
        message = "<emoji id=6296367896398399651>✅</emoji> **Berhasil!** Paket **{name}** telah dihapus.".format(
            name=name
        )
        del ctx.vip_list[item_id]
    else:
        message = "<emoji id=6298671811345254603>❌</emoji> **Gagal!** Paket **{name}** tidak ditemukan lagi.".format(
            name=name
        )
    btn = client.ns.telegram.button.build_button_grid([back_row])
    if callback_query.message.photo:
        await callback_query.edit_message_caption(message, reply_markup=btn)
    else:
        await callback_query.edit_message_text(message, reply_markup=btn)


@command(lambda ctx: filters.regex("^api_settings$"), handler_type="callback")
async def api_settings_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    saweria_status = (
        "<emoji id=6296367896398399651>✅</emoji> Aktif"
        if saweria_user_id
        else "<emoji id=6298671811345254603>❌</emoji> Belum Diatur"
    )
    layout = [
        [{"text": "💳 Atur Kunci Saweria", "callback_data": "set_api SAWERIA"}],
        [{"text": "🗑️ Hapus Semua Kunci", "callback_data": "del_api_confirm"}],
        [{"text": "• Kembali ke Pengaturan •", "callback_data": "settings"}],
    ]
    text = f"**<emoji id=6176966310920983412>🔑</emoji> Pengelola Kunci API untuk {client.me.mention}**\n\nAtur koneksi pembayaran Saweria untuk bot Anda.\n\n**Status Layanan:**\n- `Gateway Pembayaran (Saweria)`: **{saweria_status}**\n\nPilih tindakan:"
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^set_api\\s(.+)"), handler_type="callback")
async def set_api_key_prompt(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    (_, key_name) = callback_query.data.split(" ", 1)
    await callback_query.message.delete()
    layout = [
        [{"text": "• Kembali ke Pengaturan API •", "callback_data": "api_settings"}]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)
    try:

        def ask(p):
            return client.ask(
                chat_id,
                f'''{p}{"""

Ketik `/batal` untuk membatalkan."""}''',
                timeout=600,
            )

        if key_name == "SAWERIA":
            username_msg = await ask("**2/2:** Kirim **Username Saweria** Anda.")
            if username_msg.text and username_msg.text.lower() == "/batal":
                raise listen.UserCancelled
            processing_msg = await client.send_message(
                chat_id,
                "<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar.",
            )
            try:
                saweria_temp = client.ns.payment.SaweriaScraper()
                user_id_saweria = await saweria_temp.get_user_id(
                    username=username_msg.text
                )
                if not user_id_saweria:
                    raise Exception(
                        "Username Saweria tidak ditemukan atau gagal melewati Cloudflare."
                    )
                await ctx.db.setVars(client.me.id, "SAWERIA_USER_ID", user_id_saweria)
                await processing_msg.delete()
                await client.send_message(
                    chat_id,
                    "<emoji id=6296367896398399651>✅</emoji> **Sukses!**\nKunci Saweria berhasil diverifikasi dan disimpan.",
                    reply_markup=back_btn,
                )
            except Exception as e:
                await processing_msg.edit_text(
                    "<emoji id=6298671811345254603>❌</emoji> **Gagal!**\nUsername Saweria tidak ditemukan atau API Key salah.\n\n`Error: {e}`".format(
                        e=e
                    ),
                    reply_markup=back_btn,
                )
                return
        else:
            await client.send_message(
                chat_id, "Fitur ini sudah dinonaktifkan.", reply_markup=back_btn
            )
            return
        from services import initialize_bot_services

        await initialize_bot_services(client, ctx.db)
    except listen.UserCancelled:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>🚫</emoji> **Proses Dibatalkan**",
            reply_markup=back_btn,
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            "<emoji id=5413704112220949842>⏰</emoji> **Waktu Habis**\nProses telah dibatalkan otomatis.",
            reply_markup=back_btn,
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
            reply_markup=back_btn,
        )


@command(lambda ctx: filters.regex("^del_api_confirm$"), handler_type="callback")
async def confirm_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    text = "**⚠️ Konfirmasi**\n\nAnda yakin ingin menghapus **SEMUA** kunci API (Saweria & Gemini) untuk bot ini?"
    layout = [
        [
            {"text": "✅ Ya, Hapus Semua", "callback_data": "do_del_api"},
            {"text": "❌ Tidak, Batalkan", "callback_data": "api_settings"},
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^do_del_api$"), handler_type="callback")
async def do_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    await ctx.db.removeVars(client.me.id, "SAWERIA_USER_ID")
    from services import initialize_bot_services

    await initialize_bot_services(client, ctx.db)
    await callback_query.answer(
        "<emoji id=6296367896398399651>✅</emoji> Semua kunci API untuk bot ini telah berhasil dihapus.",
        show_alert=True,
    )
    await api_settings_callback(client, callback_query)


@command(lambda ctx: filters.regex("^manage_coupons"), handler_type="callback")
async def manage_coupons_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    text = "**<emoji id=5377599075237502153>🎟️</emoji> Manajemen Kupon**\nKelola kode diskon untuk VVIP Anda."
    layout = [
        [{"text": "➕ Buat Kupon Baru", "callback_data": "add_coupon"}],
        [{"text": "📋 Lihat Kupon", "callback_data": "list_coupons_0"}],
        [{"text": "• Kembali ke Pengaturan •", "callback_data": "settings"}],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^add_coupon"), handler_type="callback")
async def add_coupon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    chat_id = callback_query.from_user.id
    await callback_query.message.delete()
    try:

        def ask(text):
            return client.ask(
                chat_id,
                f'''{text}{"""

Ketik `/batal` untuk membatalkan."""}''',
                timeout=600,
            )

        code = (
            await ask("**1/4:** Masukkan kode kupon unik (misal: `DISKONBARU`).")
        ).text.upper()
        type_msg = await ask(
            "**2/4:** Pilih tipe diskon:\n1. Persentase (%)\n2. Potongan Harga Tetap (misal: 10000)"
        )
        discount_type = "percentage" if "1" in type_msg.text else "fixed"
        value_prompt = (
            "**3/4:** Masukkan nilai persentase (misal: `15` untuk 15%)."
            if discount_type == "percentage"
            else "**3/4:** Masukkan jumlah potongan harga (misal: `10000` untuk Rp 10.000)."
        )
        discount_value = int((await ask(value_prompt)).text)
        uses_left = int(
            (
                await ask(
                    "**4/4:** Berapa kali kupon ini bisa digunakan? (masukkan angka)"
                )
            ).text
        )
        expiry_days_msg = await ask(
            "**5/5:** Berapa hari kupon ini akan berlaku? (masukkan angka)"
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
            "<emoji id=6296367896398399651>✅</emoji> Kupon `{code}` berhasil dibuat.".format(
                code=code
            ),
        )
    except (listen.UserCancelled, asyncio.TimeoutError, ValueError) as e:
        await client.send_message(
            chat_id, "<emoji id=6298671811345254603>🚫</emoji> **Proses Dibatalkan**"
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
        )


@command(lambda ctx: filters.regex("^list_coupons_(\\d+)"), handler_type="callback")
async def list_coupons_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    page = int(callback_query.data.split("_")[2])
    coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
    back_row = [{"text": "• Kembali •", "callback_data": "manage_coupons"}]
    if not coupons:
        text = "Tidak ada kupon yang dibuat."
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await callback_query.edit_message_caption(text, reply_markup=btn)
    total_pages = len(coupons)
    page = max(0, min(page, total_pages - 1))
    coupon = coupons[page]
    expiry_text = "Permanent"
    if coupon.get("expiry_date"):
        expiry_text = datetime.fromisoformat(coupon["expiry_date"]).strftime("%d %b %Y")
    text = "**<emoji id=5334882760735598374>📋</emoji> Detail Kupon ({page}/{total})**\n- Kode: `{code}`\n- Tipe: `{type}`\n- Nilai: `{value}`\n- Sisa Penggunaan: `{uses}`\n- Berlaku hingga: `{expiry}`".format(
        page=page + 1,
        total=total_pages,
        code=coupon["code"],
        type=coupon["discount_type"],
        value=coupon["discount_value"],
        uses=coupon["uses_left"],
        expiry=expiry_text,
    )
    layout = []
    pagination_row = []
    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages if page + 1 < total_pages else page
        pagination_row.extend(
            [
                {"text": "«", "callback_data": f"list_coupons_{prev_page}"},
                {"text": "»", "callback_data": f"list_coupons_{next_page}"},
            ]
        )
    layout.append(
        [
            {
                "text": "🗑️ Hapus Kupon Ini",
                "callback_data": f"delete_coupon {coupon['code']} {page}",
            }
        ]
    )
    if pagination_row:
        layout.append(pagination_row)
    layout.append(back_row)
    btn = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_caption(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^delete_coupon\\s(.+)\\s(\\d+)"), handler_type="callback"
)
async def delete_coupon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    (_, code, page_str) = callback_query.data.split()
    coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
    coupon_to_remove = next((c for c in coupons if c.get("code") == code), None)
    if coupon_to_remove:
        await ctx.db.removeListVars(client.me.id, "coupons", coupon_to_remove)
        await callback_query.answer(
            "<emoji id=6296367896398399651>✅</emoji> Kupon berhasil dihapus.",
            show_alert=True,
        )
    new_page = int(page_str)
    remaining_coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
    if new_page >= len(remaining_coupons) and len(remaining_coupons) > 0:
        new_page = len(remaining_coupons) - 1
    callback_query.data = f"list_coupons_{new_page}"
    await list_coupons_callback(client, callback_query)
