# Laporan Analisis Mendalam — VvipBot (settings, payment, allbots, send_gift)

Dokumen ini adalah spesifikasi lengkap seluruh logika Python agar dapat ditulis ulang di TypeScript tanpa membaca file aslinya.

---

## 0. Konteks Kerangka (`VvipBot/__init__.py` + helper)

### Registrasi handler
- `command(filter_lambda, handler_type="message")` → append `(func, filter_lambda, handler_type)` ke `ALL_HANDLERS`.
- `handler_type` valid: `"message"` (MessageHandler), `"callback"` (CallbackQueryHandler), `"pre_checkout"` (PreCheckoutQueryHandler). Default `"message"`.
- Filter sbg lambda: `filters.regex("^...$")` untuk callback, `filters.command("x")`, `filters.successful_payment`, `filters.PreCheckoutQuery`, kombinasinya dengan `&`.

### Objek `ctx` (global SimpleNamespace)
- `ctx.db` — database (lihat §helper DB).
- `ctx.manager` — BotManager: `.running_bots` (dict bot_id→client), `.main_bot_client`, `.stop_bot(bot_id)`, `.start_bot(bot_data)`.
- `ctx.owner_id` — ID super-admin (pemilik semua bot).
- `ctx.log` — logger global (`ctx.log.print`, `ctx.log.GREEN`, `ctx.log.RED`, `ctx.log.CYAN`).
- Atribut sesi dinamis di-set saat runtime: `ctx.vip_list` (dict id→nama utk hapus VVIP), `ctx.vip_list_edit` (dict id→nama utk edit harga).

### Fungsi otentikasi / target (di `VvipBot/__init__.py`)
- `is_bot_owner(client, user_id)` → `True` jika `user_id == ctx.owner_id` ATAU db var `owner_id` milik bot itu == `user_id`.
- `get_notification_target(client)` → db var `notif_chat_id`; jika kosong → db var `owner_id`; jika kosong → `ctx.owner_id`.
- `check_new_user(client, update)` (dipanggil dari listener message): append user.id ke list `user_ids` bot, kirim notifikasi "Pengguna Baru" ke owner bot.

### `client.ask(chat_id, text, timeout=...)` (`helpers/listen.py`)
- Kirim pesan & tunggu balasan teks.
- Jika pengguna kirim `/batal` → raise `listen.UserCancelled`.
- Timeout → raise `asyncio.TimeoutError`.
- Return objek Message (memiliki `.text`, `.text.markdown`, `.photo`, `.video`, dll).

### `client.ns` (namespace per bot)
- `client.ns.emoji.<name>` — string emoji (mis. `.money_bag`, `.party_popper`, `.white_check_mark`, `.cross_mark`, `.hourglass`, `.bell`, `.star`, `.gift`, `.pencil`, `.minus`, `.plus`, `.calendar`, `.folder`, `.bulb`, `.link`, `.mag`, `.mag_right`, `.toolbox`, `.key`, `.ticket_admit`, `.loudspeaker`, `.glowing_star`, `.repeat`, `.chart_bar`, `.alarm_clock`, `.warning`, `.exclamation`, `.down_pointing`, `.open_folder`, `.open_book`, `.id_card`, `.gem`, `.sparkles`, `.shopping_bags`, `.writing_hand`, `.frame`, `.busts_in_silhouette`, `.bust_in_silhouette`, `.performing_arts`, `.back_arrow`, `.right_pointing`, `.robot`).
- `client.ns.emoji.id(name)` — kembalikan ID custom emoji (angka) utk icon_custom_emoji_id.
- `client.ns.telegram.button.build_button_grid(layout)` — layout: `list[list[dict]]`; tiap dict `{text, callback_data, style: "blue"|"green"|"red", emoji: id}` → dibangun jadi `InlineKeyboardMarkup`; tombol diberi `icon_custom_emoji_id`, style dipetakan ke `ButtonStyle.PRIMARY/SUCCESS/DANGER`.
- `client.ns.telegram.button.create_inline_keyboard(text)` — parse pattern `| label - cbdata ;params |`, `same` utk sekolom; return `(InlineKeyboardMarkup, cleaned_text)`.
- `client.ns.telegram.arg.getMention(user)` — markdown mention.
- `client.ns.utils.faker.generate()` — objek FakeName `{name, email}`.
- `client.ns.payment.SaweriaScraper()` — instance scraper Saweria.

### `client.services.saweria` (dibuat `initialize_bot_services(client, db)`)
- `create_payment(user_id, amount, name, email, message, creator_name)` → `(qr_string, transaction_id, qr_image_stream(BytesIO), amount_raw:int)`.
- `check_paid_status(transaction_id)` → bool.
- `get_user_id(username)` → user_id Saweria.

### `helpers/saweria_message_generator.py`
- `generate_safe_saweria_message(name)` → string pesan aman utk Saweria.

### DB methods (`helpers/database.py`) — semua ber-prefix key `client.me.id` (bot id) kecuali `getBots/removeBot`
- `setVars(user_id, key, value)` / `getVars(user_id, key)` / `removeVars(user_id, key)` — simpan JSON terenkripsi (getVars auto JSON-decode jika value string JSON → angka/kamus yang tersimpan ketemu sebagai primitif; note: `setVars` numerik tersimpan via `json.dumps` sehingga `getVars` mengembalikan int).
- `setListVars(user_id, listName, value)` — append (dedupe by encrypted value) ke bucket list.
- `getListVars(user_id, listName)` — return list hasil decode.
- `removeListVars(user_id, listName, value)` — hapus value tertentu dari list.
- `removeAllVars(user_id)` — hapus SEMUA vars milik user_id (untuk penghapusan bot).
- `getBots(is_token=True)` — list dict `{name: user_id_str, api_id, api_hash, bot_token/A session_string}` di mana name == bot_id.
- `removeBot(user_id)` — hapus entri dari daftar bots.

---

# A. DIRECTORY `settings/`

## A.1 `settings/__init__.py`
Hanya re-export: `from .panel import *`, `.pricing_setup`, `.broadcast`, `.api`, `.coupons`, `.revenue`, `.notification`. Tidak ada logika handler.

---

## A.2 `settings/panel.py` — Panel Pengaturan Owner

### Handler 1: `settings`
- **Dekorator**: `@command(lambda ctx: filters.regex("^settings$"), handler_type="callback")`
- **Fungsi**: `async def settings(client, callback_query)`
- **Parameter**: `client`, `callback_query` (CallbackQuery).
- **Alur**:
  1. `if not await is_bot_owner(client, callback_query.from_user.id)` → `await callback_query.answer("🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True)` & return.
  2. Susun `txt_content` + `btn = build_button_grid(_settings_layout(client))`.
  3. Jika `callback_query.message.photo` → `edit_message_caption(txt_content, reply_markup=btn)`; else `edit_message_text(...)`.

- **Teks pesan (verbatim)**:
  ```
  **{client.ns.emoji.toolbox} Panel Pengaturan Owner**

  Selamat datang di pusat kendali bot Anda! Silakan pilih menu di bawah untuk mengelola berbagai aspek bot.
  ```
  ({client.ns.emoji.toolbox} = emoji toolbox)
  - Alert non-owner: `🚫 Anda tidak memiliki akses ke menu ini.`

- **Layout `_settings_layout(client)`** (callback_data / text / style):
  - Baris 1: `🖼️ Atur Foto Start` → `set_start_photo` (blue); `✍️ Atur Teks Start` → `set_start_text` (blue).
  - Baris 2: `➕ Tambah VVIP` → `setup_listvvip` (green); `➖ Hapus VVIP` → `delete_listvvip` (red).
  - Baris 3: `✏️ Edit Harga VVIP` → `edit_price_listvvip` (blue).
  - Baris 4: `👥 Total Pengguna` → `total_users_count` (blue); `👥 Cek Member VVIP` → `list_members_0` (blue).
  - Baris 5: `🕵️ Cek Member Aktif` → `check_active_menu_init` (blue); `🔍 Cek Status Grup VVIP` → `check_vvip_status` (blue).
  - Baris 6: `📢 Buat Broadcast` → `broadcast` (green); `🌟 Harga Broadcast Paid` → `set_broadcast_price` (green).
  - Baris 7: `🔑 Kelola Kunci API` → `api_settings` (blue); `🎟️ Kelola Kupon` → `manage_coupons` (blue).
  - Baris 8: `🔔 Atur Tempat Notifikasi` → `set_notif_chat` (blue).
  - Baris 9: `💰 Pendapatan VIP` → `vip_revenue_menu` (green); `⭐ Statistik Stars` → `stats_0` (green).
  - Baris 10: `• Kembali ke Menu Utama •` → `start` (blue).

- **DB**: hanya baca via `is_bot_owner`.
- **API**: `callback_query.answer`, `edit_message_text`/`edit_message_caption`.
- **Helper**: `client.ns.emoji.*`, `client.ns.telegram.button.build_button_grid`.

---

## A.3 `settings/revenue.py` — Laporan Pendapatan VIP

- **Emoji**: `TIMEZONE = ZoneInfo("Asia/Jakarta")` utk semua perhitungan.

### Helper `_back_to_revenue_layout(client)`
- Baris tunggal: `• Kembali •` → `vip_revenue_menu` (blue).

### Helper `_reply(client, callback_query, text, btn)`
- Jika pesan photo → `edit_message_caption(text, reply_markup=btn)`; else `edit_message_text`.

### Handler 1: `vip_revenue_menu`
- **Dekorator**: `@command(lambda ctx: filters.regex("^vip_revenue_menu$"), handler_type="callback")`
- **Fungsi**: `async def vip_revenue_menu_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner; jika bukan → return (tidak ada pesan).
  2. Kirim teks + layout via `_reply`.

- **Teks (verbatim)**:
  ```
  **{emoji.money_bag} Cek Pendapatan VIP**

  Pilih periode waktu untuk melihat total pendapatan dari penjualan paket VIP.
  ```

- **Layout**:
  - Baris 1: `📅 Harian (Hari Ini)` → `show_revenue_daily` (blue); `🗓️ Mingguan (7 Hari)` → `show_revenue_weekly` (blue).
  - Baris 2: `📆 Bulanan (Bulan Ini)` → `show_revenue_monthly` (blue).
  - Baris 3: `• Kembali •` → `settings` (blue).

### Handler 2: `show_revenue_(daily|weekly|monthly)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^show_revenue_(daily|weekly|monthly)$"), handler_type="callback")`
- **Fungsi**: `async def show_vip_revenue_callback(client, callback_query)`.
- **Cara ambil periode**: `period = callback_query.matches[0].group(1)` (regex capture group).
- **Alur**:
  1. Cek owner.
  2. `revenue_history = await ctx.db.getListVars(client.me.id, "vip_revenue_history") or []`.
  3. `now = datetime.now(TIMEZONE)` (Asia/Jakarta).
  4. Loop tiap record: `record_date = datetime.fromisoformat(record["date"]).astimezone(TIMEZONE)`; jika `_include_record(period, record_date, now)` → `total += int(record["amount"])`, `transaction_count += 1`. Exception → skip.
  5. Susun teks & tombol kembali → `_reply`.

- **Fungsi filter `_include_record(period, record_date, now)`**:
  - daily: `record_date.date() == now.date()`.
  - weekly: `now - timedelta(days=7) <= record_date <= now`.
  - monthly: `record_date.year == now.year and record_date.month == now.month`.
  - else False.

- **Teks (verbatim)**:
  ```
  **{emoji.chart_bar} Laporan Pendapatan VIP**

  **Periode:** {period_text}

  {emoji.money_bag} **Total Pendapatan:** `Rp {total_amount:,}`
  {emoji.repeat} **Jumlah Transaksi:** `{transaction_count}`
  ```
  - `period_text`: `Harian`/`Mingguan`/`Bulanan`.
  - `total_amount` diformat dengan ribuan (`50000` → `50,000`), diformat markdown code.

- **DB dibaca**: list `vip_revenue_history` (baca, per bot id).
- **Helper**: `client.ns.emoji.id(...)`, `build_button_grid`, `_reply`.

---

## A.4 `settings/api.py` — Kelola Kunci API Saweria

### Helper `_back_to_api_layout(client)`
- Baris: `• Kembali ke Pengaturan API •` → `api_settings` (blue).

### Helper `_reply(client, callback_query, text, btn)` — sama pola caption/text.

### Handler 1: `api_settings`
- **Dekorator**: `@command(lambda ctx: filters.regex("^api_settings$"), handler_type="callback")`
- **Fungsi**: `async def api_settings_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")`.
  3. `saweria_status` = `"✓ Aktif"` jika ada, selainnya `"✗ Belum Diatur"` (pakai `emoji.white_check_mark` / `emoji.cross_mark`).
  4. Kirim teks + layout via `_reply`.

- **Teks (verbatim)**:
  ```
  **{emoji.key} Pengelola Kunci API untuk {client.me.mention}**

  Atur koneksi pembayaran Saweria untuk bot Anda.

  **Status Layanan:**
  - `Gateway Pembayaran (Saweria)`: **{saweria_status}**

  Pilih tindakan:
  ```

- **Layout**:
  - Baris 1: `💳 Atur Kunci Saweria` → `set_api SAWERIA` (green).
  - Baris 2: `🗑️ Hapus Semua Kunci` → `del_api_confirm` (red).
  - Baris 3: `• Kembali ke Pengaturan •` → `settings` (blue).

- **DB dibaca**: `SAWERIA_USER_ID`.

### Handler 2: `set_api\s(.+)` (prompt input username)
- **Dekorator**: `@command(lambda ctx: filters.regex("^set_api\\s(.+)"), handler_type="callback")`
- **Fungsi**: `async def set_api_key_prompt(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `chat_id = callback_query.from_user.id`; `_, key_name = callback_query.data.split(" ", 1)` → key_name = bagian setelah `set_api ` (mis. `SAWERIA`).
  3. `await callback_query.message.delete()`.
  4. `back_btn = build_button_grid(_back_to_api_layout(client))`.
  5. Definisi `ask(p)` = `client.ask(chat_id, f"{p}\n\nKetik `/batal` untuk membatalkan.", timeout=600)`.
  6. **Jika key_name == "SAWERIA"**:
     - `username_msg = await ask("**2/2:** Kirim **Username Saweria** Anda.")`; jika `username_msg.text.lower() == "/batal"` → raise UserCancelled.
     - Kirim `processing_msg`: `"{emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar."`.
     - `saweria_temp = client.ns.payment.SaweriaScraper()`; `user_id_saweria = await saweria_temp.get_user_id(username=username_msg.text)`.
     - Jika tidak didapat → raise `Exception("Username Saweria tidak ditemukan.")`.
     - `await ctx.db.setVars(client.me.id, "SAWERIA_USER_ID", user_id_saweria)`.
     - Hapus processing_msg; kirim `"{emoji.white_check_mark} **Sukses!**\nKunci Saweria berhasil disimpan."` + back_btn.
     - Jika exception → `processing_msg.edit_text("{emoji.cross_mark} **Gagal!**\n`Error: {e}`", reply_markup=back_btn)` dan return.
  7. Else → kirim `"Fitur tidak didukung."` + back_btn, return.
  8. Setelah sukses → `await initialize_bot_services(client, ctx.db)` (rebuild `client.services.saweria`).
  9. `except (listen.UserCancelled, asyncio.TimeoutError)` → kirim `"{emoji.cross_mark} **Proses Dibatalkan**"` + back_btn.

- **Teks prompt (verbatim)**:
  - `**2/2:** Kirim **Username Saweria** Anda.`
  - `{emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.`
  - `{emoji.white_check_mark} **Sukses!**\nKunci Saweria berhasil disimpan.`
  - `{emoji.cross_mark} **Gagal!**\n`Error: {e}``
  - `Fitur tidak didukung.`
  - `{emoji.cross_mark} **Proses Dibatalkan**`
  - Semua prompt ask diberi akhiran `\n\nKetik `/batal` untuk membatalkan.`

- **DB tulis**: `SAWERIA_USER_ID`.
- **API**: `client.ask`, `client.send_message`, `client.send_message(..., reply_markup=back_btn)`, `callback_query.message.delete`.

### Handler 3: `del_api_confirm`
- **Dekorator**: `@command(lambda ctx: filters.regex("^del_api_confirm$"), handler_type="callback")`
- **Fungsi**: `async def confirm_delete_api_keys(client, callback_query)`.
- **Alur**: cek owner → kirim teks konfirmasi + 2 tombol via `_reply`.

- **Teks (verbatim)**:
  ```
  **{emoji.exclamation} Konfirmasi**

  Anda yakin ingin menghapus **SEMUA** kunci API?
  ```

- **Layout**:
  - Baris tunggal: `✅ Ya, Hapus Semua` → `do_del_api` (red); `❌ Tidak, Batalkan` → `api_settings` (green).

### Handler 4: `do_del_api`
- **Dekorator**: `@command(lambda ctx: filters.regex("^do_del_api$"), handler_type="callback")`
- **Fungsi**: `async def do_delete_api_keys(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `await ctx.db.removeVars(client.me.id, "SAWERIA_USER_ID")`.
  3. `await initialize_bot_services(client, ctx.db)`.
  4. `await callback_query.answer("Semua kunci API untuk bot ini telah berhasil dihapus.", show_alert=True)`.
  5. `await api_settings_callback(client, callback_query)` (render ulang menu API).

- **DB tulis**: remove `SAWERIA_USER_ID`.
- **Helper**: `initialize_bot_services` (services.py).

---

## A.5 `settings/notification.py` — Atur Tempat Notifikasi

### Helper `_back_to_settings_layout(client)`
- Baris: `• Kembali ke Pengaturan •` → `settings` (blue).

### Handler: `set_notif_chat`
- **Dekorator**: `@command(lambda ctx: filters.regex("^set_notif_chat$"), handler_type="callback")`
- **Fungsi**: `async def set_notif_chat_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `chat_id = callback_query.from_user.id`; `await callback_query.message.delete()`.
  3. `back_btn = build_button_grid(_back_to_settings_layout(client))`.
  4. `ask_msg = await client.ask(chat_id, prompt, timeout=600)`.
  5. Jika `not ask_msg.text` → kirim `"{emoji.cross_mark} **Gagal:** Pesan bukan teks."` + back_btn.
  6. Jika `== "/batal"` → raise UserCancelled.
  7. Jika `== "/none"` → `ctx.db.removeVars(client.me.id, "notif_chat_id")`; kirim `"{emoji.white_check_mark} **Sukses!** Notifikasi kembali ke default (owner_id)."` + back_btn.
  8. Else → `ctx.db.setVars(client.me.id, "notif_chat_id", ask_msg.text)`; kirim `"{emoji.white_check_mark} **Sukses!** Tempat notifikasi diatur ke `{ask_msg.text}`."` + back_btn.
  9. Except `(UserCancelled, TimeoutError)` → `"{emoji.cross_mark} **Proses Dibatalkan**"` + back_btn.

- **Teks prompt (verbatim)**:
  ```
  **{emoji.bell} Atur Tempat Notifikasi**

  Kirim ID chat atau @username tempat notifikasi pembayaran akan dikirim.

  Ketik `/none` untuk kembali ke default (dikirim ke owner_id).

  Ketik `/batal` untuk membatalkan.
  ```

- **DB**: `notif_chat_id` (baca thru get_notification_target di tempat lain; tulis/hapus di sini).

---

## A.6 `settings/broadcast.py` — Broadcast & Harga Broadcast Paid

### Handler 1: `set_broadcast_price`
- **Dekorator**: `@command(lambda ctx: filters.regex("^set_broadcast_price$"), handler_type="callback")`
- **Fungsi**: `async def set_broadcast_price_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `chat_id = from_user.id`; delete pesan callback.
  3. `ask_msg = await client.ask(chat_id, prompt, timeout=300)`.
  4. Jika `ask_msg.text`:
     - `== "/batal"` → raise UserCancelled.
     - `in ["/empty", "0"]` → `removeVars("broadcast_price")`; kirim `"{emoji.white_check_mark} **Sukses!** Fitur Paid Broadcast dinonaktifkan."` + back_btn.
  5. Jika `not ask_msg.text.isdigit()` → raise `ValueError("**Format Salah**")`.
  6. `stars_amount = int(text)`; `setVars("broadcast_price", stars_amount)`; kirim `"{emoji.white_check_mark} **Sukses!** Harga broadcast telah diatur menjadi `{stars_amount}` Stars."` + back_btn.
  7. Except `(UserCancelled, TimeoutError, ValueError) as e` → kirim `"{emoji.cross_mark} **Proses Dibatalkan**\n{e}"` + back_btn.

- **Teks prompt (verbatim)**:
  ```
  **{emoji.glowing_star} Atur Harga Broadcast Paid**

  Masukkan jumlah Bintang (Stars) yang harus dibayar pengguna.

  Ketik `0` atau `/empty` untuk menonaktifkan.

  Ketik `/batal` untuk membatalkan.
  ```

- **DB**: tulis `broadcast_price` (int) / hapus.

### Handler 2: `broadcast`
- **Dekorator**: `@command(lambda ctx: filters.regex("^broadcast$"), handler_type="callback")`
- **Fungsi**: `async def broadcast_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner; bukan → `answer("🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True)`.
  2. `chat_id = callback_query.message.chat.id`; `bot_id = client.me.id`.
  3. Delete pesan callback.
  4. `ask_message = await client.ask(chat_id, text=prompt, timeout=600)`; jika `ask_message.text == "/batal"` → raise UserCancelled.
  5. `broadcast_price = int(await ctx.db.getVars(bot_id, "broadcast_price") or 0)`.
  6. Jika `broadcast_price > 0 and not (ask_message.photo or ask_message.video)` → raise `ValueError("{emoji.cross_mark} **Gagal:** Paid Broadcast memerlukan media foto/video!")`.
  7. `user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []`; jika kosong → kirim `"{emoji.cross_mark} **Gagal:** Tidak ada pengguna."` (tanpa reply_markup).
  8. `progress_msg = send_message(chat_id, "{emoji.white_check_mark} Memulai siaran ke `{len(user_ids)}` pengguna...")`.
  9. `send_to_user(target_user_id)`:
     - Panggil `_send_broadcast_message(client, target_user_id, ask_message, broadcast_price)`; `success_count += 1`.
     - `except pyrogram.errors.FloodWait as e`: `await asyncio.sleep(e.value + 1)` lalu rekursif `send_to_user` lagi.
     - `except Exception`: `removeListVars(client.me.id, "user_ids", target_user_id)` (hapus user gagal dari daftar) & `fail_count += 1`.
     - Setelah tiap user: `await asyncio.sleep(0.1)`.
  10. Loop `for user_id in user_ids: if user_id != ctx.owner_id: await send_to_user(user_id)` (owner super dikecualikan).
  11. Hapus `progress_msg`; kirim hasil:
      ```
      **{emoji.loudspeaker} Siaran Selesai!**
      {emoji.white_check_mark} **Terkirim:** `{success_count}`
      {emoji.cross_mark} **Gagal:** `{fail_count}`
      ```
  12. Except `(UserCancelled, TimeoutError, ValueError) as e` → kirim `"{emoji.cross_mark} **Gagal/Batal**\n{e}"`.

- **Teks prompt (verbatim)**:
  ```
  **{emoji.loudspeaker} Kirim Pesan Broadcast**

  Silakan teruskan (forward) atau kirim pesan yang ingin disiarkan.

  Ketik `/batal` untuk membatalkan.
  ```

### Helper `_send_broadcast_message(client, target_user_id, source_message, broadcast_price=0)`
- Input: pesan sumber (dapat photo/video/text) + harga stars.
- **Alur**:
  1. `caption_or_text = source_message.caption or source_message.text`; `text_to_parse = caption_or_text.markdown if caption_or_text else ""`.
  2. `reply_markup, cleaned_text = client.ns.telegram.button.create_inline_keyboard(text_to_parse)` — parse tombol inline `| label - cbdata |`.
  3. `final_markup = reply_markup if reply_markup.inline_keyboard else (source_message.reply_markup if source_message.reply_markup else None)`.
  4. **Jika `broadcast_price > 0` dan (photo atau video)**:
     - Buat `media_list` dari `pryrogram.types.InputPaidMediaPhoto(source_message.photo.sizes[-1].file_id)` atau `InputPaidMediaVideo(source_message.video.file_id)`.
     - `await client.send_paid_media(chat_id=target_user_id, star_count=broadcast_price, media=media_list, caption=cleaned_text, reply_markup=final_markup)` → paid broadcast (media kena biaya).
  5. **Jika photo** (tanpa paid): `send_photo(chat_id, photo=photo.sizes[-1].file_id, caption=cleaned_text, reply_markup=final_markup)`.
  6. **Jika text**: `send_message(chat_id, text=cleaned_text, reply_markup=final_markup)`.
  7. **Else** (pose lain): `source_message.copy(chat_id=target_user_id, caption=cleaned_text, reply_markup=final_markup)`.

- **API pyrogram**: `send_paid_media` (Star-based media broadcast), `send_photo`, `send_message`, `Message.copy`, `create_chat_invite_link` (tidak di sini).
- **DB**: baca `broadcast_price`, baca list `user_ids`, tulis-hapus `user_ids` (hapus yang gagal).

---

## A.7 `settings/coupons.py` — Manajemen Kupon

### Helper `_back_to_coupons_layout(client)`
- Baris: `• Kembali •` → `manage_coupons` (blue).

### Handler 1: `manage_coupons`
- **Dekorator**: `@command(lambda ctx: filters.regex("^manage_coupons"), handler_type="callback")` — tanpa penjaga `$` (prefix).
- **Fungsi**: `async def manage_coupons_callback(client, callback_query)`.
- **Alur**: cek owner → edit caption/text dengan teks + layout.

- **Teks (verbatim)**:
  ```
  **{emoji.ticket_admit} Manajemen Kupon**
  Kelola kode diskon untuk VVIP Anda.
  ```

- **Layout**:
  - Baris 1: `➕ Buat Kupon Baru` → `add_coupon` (green).
  - Baris 2: `📋 Lihat Kupon` → `list_coupons_0` (blue).
  - Baris 3: `• Kembali •` → `settings` (blue).

### Handler 2: `add_coupon`
- **Dekorator**: `@command(lambda ctx: filters.regex("^add_coupon"), handler_type="callback")` — prefix.
- **Fungsi**: `async def add_coupon_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `chat_id = from_user.id`; delete callback message.
  3. `ask(text)` → `client.ask(chat_id, f"{text}\n\nKetik `/batal` untuk membatalkan.", timeout=600)`.
  4. `code = (await ask("**1/4:** Masukkan kode kupon unik (misal: `DISKONBARU`).")).text.upper()`.
  5. `type_msg = await ask("**2/4:** Pilih tipe diskon:\n1. Persentase (%)\n2. Potongan Harga Tetap")`; `discount_type = "percentage" if "1" in type_msg.text else "fixed"`.
  6. `value_prompt = "**3/4:** Masukkan nilai persentase."` jika percentage, selainnya `"**3/4:** Masukkan jumlah potongan harga."`; `discount_value = int((await ask(value_prompt)).text)`.
  7. `uses_left = int((await ask("**4/4:** Berapa kali kupon ini bisa digunakan?")).text)`.
  8. `expiry_days = int((await ask("**5/5:** Berapa hari kupon ini akan berlaku?")).text)`; `expiry_date = (datetime.now(timezone.utc) + timedelta(days=expiry_days)).isoformat()` jika `expiry_days > 0` else `None`.
  9. `coupon_data = {code, discount_type, discount_value, uses_left, expiry_date}`; `ctx.db.setListVars(client.me.id, "coupons", coupon_data)`.
  10. Kirim `"{emoji.white_check_mark} Kupon `{code}` berhasil dibuat."`.
  11. Except `(UserCancelled, TimeoutError, ValueError)` → kirim `"{emoji.cross_mark} **Proses Dibatalkan**"`.

- **DB**: list `coupons` (append objek).

### Handler 3: `list_coupons_(\d+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^list_coupons_(\\d+)"), handler_type="callback")`
- **Fungsi**: `async def list_coupons_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `page = int(callback_query.data.split("_")[2])`.
  3. `coupons = await ctx.db.getListVars(client.me.id, "coupons") or []`; `back_row = _back_to_coupons_layout(client)[0]`.
  4. Jika kosong → teks `"Tidak ada kupon yang dibuat."` + hanya tombol kembali (via `edit_message_caption` — selalu pakai caption!). return.
  5. `total_pages = len(coupons)`; `page = max(0, min(page, total_pages-1))`; `coupon = coupons[page]`.
  6. Teks detail:
     ```
     **{emoji.pencil} Detail Kupon ({page + 1}/{total_pages})**
     - Kode: `{coupon['code']}`
     - Tipe: `{coupon['discount_type']}`
     - Nilai: `{coupon['discount_value']}`
     - Sisa Penggunaan: `{coupon['uses_left']}`
     - Berlaku hingga: `{_format_expiry(coupon)}`
     ```
  7. Layout:
     - Jika `total_pages > 1`: baris pagination `«` → `list_coupons_{prev_page}` (blue), `»` → `list_coupons_{next_page}` (blue). `prev_page = (page-1+total)%total`; `next_page = (page+1)%total if page+1<total else page`.
     - Baris `🗑️ Hapus Kupon Ini` → `delete_coupon {code} {page}` (red).
     - + baris kembali.
  8. `edit_message_caption(text, reply_markup=btn)` (SELALU caption, walau pesan text — catatan: bisa error jika bukan caption; begitu pula yang asli).

- **Helper `_format_expiry(coupon)`**: jika `expiry_date` → `datetime.fromisoformat(...).strftime("%d %b %Y")`; else `"Permanent"`.

### Handler 4: `delete_coupon\s(.+)\s(\d+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^delete_coupon\\s(.+)\\s(\\d+)"), handler_type="callback")`
- **Fungsi**: `async def delete_coupon_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `_, code, page_str = callback_query.data.split()`.
  3. `coupons = getListVars("coupons") or []`; cari `c.get("code") == code`; jika ada → `removeListVars(client.me.id, "coupons", coupon_to_remove)` + `answer("Kupon berhasil dihapus.", show_alert=True)`.
  4. `new_page = int(page_str)`; ambil ulang `remaining_coupons`; jika `new_page >= len(remaining)` dan `len(remaining) > 0` → `new_page = len(remaining)-1`.
  5. Mutasi `callback_query.data = f"list_coupons_{new_page}"` lalu panggil `list_coupons_callback(client, callback_query)`.

- **DB**: list `coupons` (tulis/hapus).

---

## A.8 `settings/pricing_setup.py` — Setup/Hapus/Edit VVIP, Foto & Teks Start, Cek Status Grup

- **`ERROR_MESSAGES`**:
  - `"settings.setup_vvip.err_must_be_number"` → `"**Input Tidak Valid!** Nilai harus berupa angka."`
  - `"settings.setup_vvip.err_must_be_chat_id"` → `"**Input Tidak Valid!** Format Chat ID salah."`

### Helper `_back_layout(client)`
- Baris: `• Kembali ke Pengaturan •` → `settings` (blue).

### Helper `_reply` — caption/text pattern.

### Handler 1: `set_start_photo`
- **Dekorator**: `@command(lambda ctx: filters.regex("^set_start_photo$"), handler_type="callback")`
- **Fungsi**: `async def set_start_photo_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `chat_id = from_user.id`; delete pesan.
  3. `ask_msg = await client.ask(chat_id, "Kirim foto baru untuk menyambut user.\n\nKetik `/batal` untuk membatalkan.", timeout=120)`.
  4. Jika `ask_msg.text`:
     - `== "/batal"` → raise UserCancelled.
     - `== "/empty"` → `removeVars(client.me.id, "start_photo_id")`; kirim `"{emoji.white_check_mark} **Sukses!** Foto /start telah dihapus."` + back_btn; return.
  5. Jika `not ask_msg.photo` → kirim `"{emoji.cross_mark} **Gagal:** Pesan bukan foto."` + back_btn.
  6. `photo_id = ask_msg.photo.sizes[-1].file_id`; `setVars(client.me.id, "start_photo_id", photo_id)`; kirim `"{emoji.white_check_mark} **Sukses!** Foto /start berhasil diperbarui."` + back_btn.
  7. Except `(UserCancelled, TimeoutError)` → `"{emoji.cross_mark} **Proses Dibatalkan**"` + back_btn.

- **DB**: `start_photo_id`.

### Handler 2: `set_start_text`
- **Dekorator**: `@command(lambda ctx: filters.regex("^set_start_text$"), handler_type="callback")`
- **Fungsi**: `async def set_start_text_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner; delete pesan.
  2. `ask_text_msg = await client.ask(chat_id, prompt, timeout=600)`.
  3. Jika `not ask_text_msg.text` → `"{emoji.cross_mark} **Gagal:** Pesan bukan teks."` + back_btn.
  4. `== "/batal"` → UserCancelled.
  5. `== "/empty"` → `removeVars(client.me.id, "start_text_template")`; kirim `"{emoji.white_check_mark} **Sukses!** Teks /start telah dihapus."` + back_btn.
  6. Else: `setVars(client.me.id, "start_text_template", ask_text_msg.text.markdown)` (markdown!) → kirim `"{emoji.white_check_mark} **Sukses!** Teks /start berhasil diperbarui."` + back_btn.
  7. Except `(UserCancelled, TimeoutError)` → `"{emoji.cross_mark} **Proses Dibatalkan**"`.

- **Teks prompt (verbatim)**:
  ```
  **{emoji.writing_hand} Atur Teks Start**

  Silakan kirim teks baru untuk pesan /start. Anda dapat menggunakan variabel `{{mention}}` untuk menyapa pengguna.

  Ketik `/empty` untuk menghapus teks kustom dan kembali ke default.

  Ketik `/batal` untuk membatalkan.
  ```

- **DB**: `start_text_template` (isi = markdown text).

### Handler 3: `check_vvip_status`
- **Dekorator**: `@command(lambda ctx: filters.regex("^check_vvip_status$"), handler_type="callback")`
- **Fungsi**: `async def check_vvip_status_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner; bukan → alert `🚫 Anda tidak memiliki akses ke menu ini.`.
  2. `chat_id = callback_query.message.chat.id`; delete pesan.
  3. `status_msg = send_message(chat_id, "{emoji.hourglass} Sedang Memeriksa Status Grup...\nMohon tunggu, proses ini mungkin memakan waktu.")`.
  4. `vvip_list = getListVars(client.me.id, "list_vvip") or []`; jika kosong → `status_msg.edit("{emoji.cross_mark} Belum ada data VVIP.")`.
  5. `report_text = "{emoji.mag} Laporan Status Grup VVIP\n\n"`.
  6. Loop tiap item: `chat_id_target = item.get("chat_id_normal")`; `name = item.get("name")`; `chat = await client.get_chat(chat_id_target)`:
     - Jika `hasattr(chat, "restrictions") and chat.restrictions` → BANNED: `reason_text = f"{restriction.reason}: {restriction.text}"` (ambil `chat.restrictions[0]`); tambah:
       ```
       {emoji.folder} Nama: {name}
       {emoji.bulb} Grup: {chat.title}
       {emoji.cross_mark} STATUS: BANNED/DIBATASI
       {emoji.pencil} Alasan: {reason_text}

       ```
     - Else → `link = chat.invite_link or "N/A"`;
       ```
       {emoji.folder} Nama: {name}
       {emoji.bulb} Grup: {chat.title}
       {emoji.link} Link: {link}
       {emoji.white_check_mark} Status: Aman

       ```
     - Except → 
       ```
       {emoji.folder} Nama: {name}
       {emoji.cross_mark} Error: Tidak dapat mengakses grup (ID: {chat_id_target}). Pastikan bot adalah admin.

       ```
  7. Jika `len(report_text) > 3500` → kirim per-chunk (`client.send_message(chat_id, report_text)`), reset `report_text = ""`.
  8. Setelah loop, jika `report_text` non-kosong → kirim.
  9. `btn = build_button_grid(_back_layout(client))`; `await status_msg.delete()`; kirim `"{emoji.white_check_mark} Pemeriksaan Selesai."` + btn.

- **DB**: baca `list_vvip`.
- **API pyrogram**: `client.get_chat`, `send_message`, `status_msg.edit/delete`.

### Helper `_make_validator()`
- `validate(msg, check_func, err_msg_key)`: jika `msg.text.lower() == "/batal"` → raise UserCancelled; jika `not check_func(msg.text)` → raise `ValueError(ERROR_MESSAGES.get(err_msg_key, "**Input tidak valid.**"))`; else return `msg.text`.
- `_is_digit(t)` = `t.isdigit()`; `_is_chatid(t)` = `t.lstrip("-").isdigit()`.

### Handler 4: `setup_listvvip` (Tambahkan VVIP)
- **Dekorator**: `@command(lambda ctx: filters.regex("^setup_listvvip$"), handler_type="callback")`
- **Fungsi**: `async def setup_listvvip(client, callback_query)`.
- **Alur** (urutan prompt):
  1. Cek owner; delete pesan.
  2. `ask(text)` = `client.ask(chat_id, text + "\n\nKetik `/batal` untuk membatalkan.", timeout=600)`.
  3. **Langkah 1/8 Nama**: `vvip_data["name"] = validate(await ask("**{emoji.pencil} Langkah 1/8: Nama Kategori**\nContoh: `VVIP Bulanan`"), lambda t: True, "")`.
  4. **Langkah 2/8 Harga Normal**: `vvip_data["price"] = int(validate(await ask("**{emoji.money_bag} Langkah 2/8: Harga Normal**\nContoh: `50000`"), _is_digit, "settings.setup_vvip.err_must_be_number"))`.
  5. **Langkah 3/8 Durasi**: `vvip_data["duration"] = int(validate(await ask("**{emoji.hourglass} Langkah 3/8: Durasi Keanggotaan (Hari)**\nKirim `0` untuk akses permanen."), _is_digit, "...err_must_be_number"))`.
  6. **Langkah 4/8 Chat ID Normal**: `vvip_data["chat_id_normal"] = int(validate(await ask("**{emoji.id_card} Langkah 4/8: Chat ID Grup Normal**\nContoh: `-100123456789`."), _is_chatid, "...err_must_be_chat_id"))`.
  7. **Langkah 5/8 Harga Promo**: `vvip_data["promo_price"] = int(validate(await ask("**{emoji.party_popper} Langkah 5/8: Harga Promo**\nKirim `0` jika tidak ada harga promo."), _is_digit, "...err_must_be_number"))`.
  8. **Jika `promo_price > 0`**:
     - **Langkah 6/8**: `vvip_data["chat_id_promo"] = int(validate(await ask("**{emoji.id_card} Langkah 6/8: Chat ID Grup Promo**\nDiisi jika Harga Promo > 0."), _is_chatid, "...err_must_be_chat_id"))`.
     - **Langkah 7/8**: `promo_text_msg = client.ask(chat_id, "**{emoji.pencil} Langkah 7/8: Teks Deskripsi Promo**\nGunakan `{{name}}` dan `{{promo_price}}`.\n\nKetik `/skip` untuk menggunakan teks default.\n\nKetik `/batal` untuk membatalkan.", timeout=600)`; jika `/batal` → UserCancelled; `vvip_data["promo_text"] = "" if text.lower()==" /skip" else text`.
     - Else: `chat_id_promo = 0`, `promo_text = ""`.
  9. **Langkah 8/8** (selalu): `normal_text_msg = client.ask(chat_id, "**{emoji.pencil} Langkah 8/8: Teks Deskripsi Normal**\nGunakan `{{name}}` and `{{price}}`.\n\nKetik `/skip` untuk menggunakan teks default.\n\nKetik `/batal` untuk membatalkan.", timeout=600)`; `/batal` → UserCancelled; `vvip_data["normal_text"] = "" if /skip else text`.
  10. `ctx.db.setListVars(client.me.id, "list_vvip", vvip_data)`; kirim `"{emoji.white_check_mark} **Sukses!**\nPaket VVIP **{name}** berhasil ditambahkan."`.
  11. Except UserCancelled → `"{emoji.cross_mark} Setup paket VVIP dibatalkan."`; Except `(TimeoutError, ValueError) as e` → `"**Input Tidak Valid / Timeout**\nProses dibatalkan.\n`{e}`"`.

- **Struktur objek `list_vvip` item**: `{name, price:int, duration:int, chat_id_normal:int, promo_price:int, chat_id_promo:int, promo_text:str, normal_text:str}`.

### Helper `_build_item_selector(client, callback_query, key_attr, action, callback_prefix, emoji_id, header_emoji, header_text, body_text, empty_text)`
- `vvip_list = getListVars("list_vvip") or []; back_row = _back_layout(client)[0]`.
- Jika kosong → teks `empty_text` + hanya tombol kembali via `_reply`.
- `if not hasattr(ctx, key_attr): setattr(ctx, key_attr, {})`; `mapping = getattr(ctx, key_attr)`.
- Untuk tiap item: `item_id = uuid.uuid4().hex[:8]`; `mapping[item_id] = name`; tombol `"{action} {name}"` → `"{callback_prefix} {item_id}"`, style `"red" if action.startswith("🗑") else "blue"`.
- Baris diisi 2 tombol per baris (chunk of 2), lalu `back_row` di akhir.
- Teks: `**{header_emoji} {header_text}**\n\n{body_text}` → `_reply`.

### Handler 5: `delete_listvvip`
- **Dekorator**: `@command(lambda ctx: filters.regex("^delete_listvvip$"), handler_type="callback")`
- **Fungsi**: `async def delete_listvvip(client, callback_query)` — cek owner → panggil `_build_item_selector` dengan:
  - `key_attr="vip_list"`, `action="🗑️ Hapus"`, `callback_prefix="delete_vvip"`, `emoji_id="minus"`, `header_emoji=emoji.minus`, `header_text="Hapus Paket VVIP"`, `body_text="Pilih paket VVIP yang ingin Anda hapus."`, `empty_text="{emoji.white_check_mark} Tidak ada paket VVIP untuk dihapus."`.

### Handler 6: `delete_vvip (.+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^delete_vvip\\s(.+)"), handler_type="callback")`
- **Fungsi**: `async def confirm_delete_vvip(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `_, item_id = callback_query.data.split(" ", 1)`.
  3. Jika `not hasattr(ctx,"vip_list") or item_id not in ctx.vip_list` → `answer("Sesi tidak ditemukan atau kedaluwarsa.", show_alert=True)`, return.
  4. `name = ctx.vip_list[item_id]`; cari item di `list_vvip` berdasar nama; jika ada → `removeListVars(client.me.id, "list_vvip", item_to_remove)` + `answer("Kategori berhasil dihapus.", show_alert=True)`.
  5. `await delete_listvvip(client, callback_query)` (refresh selector).

### Handler 7: `edit_price_listvvip`
- **Dekorator**: `@command(lambda ctx: filters.regex("^edit_price_listvvip$"), handler_type="callback")`
- **Fungsi**: `async def edit_price_listvvip_callback(client, callback_query)` — panggil `_build_item_selector`:
  - `key_attr="vip_list_edit"`, `action="✏️ Edit"`, `callback_prefix="edit_vvip_price"`, `emoji_id="pencil"`, `header_emoji=emoji.pencil`, `header_text="Edit Harga VVIP"`, `body_text="Pilih paket VVIP yang ingin Anda ubah harganya."`, `empty_text="{emoji.cross_mark} Belum ada paket VVIP."`.

### Handler 8: `edit_vvip_price (.+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^edit_vvip_price\\s(.+)"), handler_type="callback")`
- **Fungsi**: `async def edit_vvip_price_callback(client, callback_query)`.
- **Alur**:
  1. Cek owner.
  2. `_, item_id = data.split(" ",1)`; jika `not hasattr(ctx,"vip_list_edit") or item_id not in ctx.vip_list_edit` → alert `"Sesi tidak ditemukan atau kedaluwarsa."`.
  3. `name = ctx.vip_list_edit[item_id]`; cari `old_item` di `list_vvip` by name; jika tidak ada → alert `"Paket VVIP tidak ditemukan."`.
  4. Delete callback message; `ask()` timeout=300.
  5. Tanya Harga Normal: prompt `"**{emoji.money_bag} Masukkan Harga Normal Baru**\nContoh: `50000`\n\nHarga sebelumnya: `{old_item.get('price', 0)}`"`; `/batal` → UserCancelled; `not isdigit()` → ValueError; `new_price = int(text)`.
  6. Tanya Harga Promo: prompt `"**{emoji.party_popper} Masukkan Harga Promo Baru**\nContoh: `25000` atau `0`.\n\nHarga sebelumnya: `{old_item.get('promo_price', 0)}`"`; validasi serupa; `new_promo = int(text)`.
  7. `removeListVars(client.me.id, "list_vvip", old_item)`; `old_item["price"] = new_price`; `old_item["promo_price"] = new_promo`; `setListVars(client.me.id, "list_vvip", old_item)`; `del ctx.vip_list_edit[item_id]`.
  8. Kirim `"{emoji.white_check_mark} **Sukses!**\nHarga paket VVIP **{name}** berhasil diubah."`.
  9. Except: UserCancelled → `"{emoji.cross_mark} Perubahan dibatalkan."`; `(TimeoutError, ValueError) as e` → `"**Input Tidak Valid / Timeout**\nProses dibatalkan.\n`{e}`"`.

- **DB**: list `list_vvip` (remove + re-add).

---

# B. DIRECTORY `payment/`

## B.1 `payment/__init__.py`
Re-export: `.verifier`, `.invoice`, `.confirm`, `.callbacks`, `.stars`.

---

## B.2 `payment/verifier.py` — Verifikasi Join Grup

- `VERIFICATION_TIMEOUT = 3600` detik.
- `LEAVING_STATUSES = [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]`.
- Tidak ada `@command` di file ini; fungsi dipanggil langsung.

### `async def verify_user_join(client, user, chat_id, link_msg)`
- **Alur**:
  1. `start_time = time()`.
  2. Loop selama belum 3600 dtk: `member = await client.get_chat_member(chat_id, user.id)`; jika `member.status not in LEAVING_STATUSES` → `is_joined = True`, log `"User {user.id} berhasil bergabung ke {chat_id}."` (green), break.
     - `except pyrogram.errors.UserNotParticipant` → `await asyncio.sleep(15)` (tunggu 15 dtk).
     - `except Exception as e` → log error & break.
  3. Setelah loop: coba `await link_msg.delete()` (abaikan error).
  4. Jika `not is_joined` → kirim ke user:
     ```
     {emoji.exclamation} **Peringatan!** Link undangan Anda telah kedaluwarsa karena Anda tidak bergabung dalam 60 menit.
     ```
- **API**: `client.get_chat_member`, `send_message`, `link_msg.delete`.

### `async def verify_user_join_multiple(client, user, invite_payloads, link_msg)`
- `invite_payloads`: list `{name, chat_id, link}`.
- **Alur**:
  1. Loop 3600 dtk: untuk tiap payload `get_chat_member(chat_id, user.id)`; jika member LEFT/BANNED atau `UserNotParticipant` → `pending_payloads.append(payload)`.
  2. Jika `pending_payloads` kosong → `link_msg.delete()` & return.
  3. `await asyncio.sleep(15)`.
  4. Setelah timeout: buat pesan `pending_lines = ["• {name}: {link}"]`; kirim ke user (protect_content=True):
     ```
     {emoji.exclamation} Anda belum join ke semua grup VIP dalam waktu 60 menit.

     Silakan join grup berikut:
     • Nama1: link1
     • Nama2: link2
     ```
     (baris ber-`\n`, pakai join list + trailing `\n`).

### `_get_all_vvip_items(vvip_list)`
- Untuk itap item `index`: `price = int(item.get("price",0) or 0)`; `chat_id_normal = item.get("chat_id_normal")`; jika `price > 0 and chat_id_normal` → append `{index, name(item.get("name", f"Paket {index+1}")), price, chat_id, duration(item.get("duration",0))}`.
- Return list.

---

## B.3 `payment/invoice.py` — Pembuatan Invoice QRIS Saweria

### `async def _ensure_saweria_available(client, user) -> bool`
- `saweria_user_id = getVars(client.me.id, "SAWERIA_USER_ID")`; jika ada → return True.
- Jika owner → kirim ke user:
  ```
  {emoji.exclamation} **Layanan Pembayaran Tidak Aktif**

  Silakan atur API Key untuk payment gateway terlebih dahulu.
  ```
  Tombol: `⚙️ Atur Kunci API` → `api_settings` (blue).
- Selainnya → kirim `"Maaf, layanan pembayaran saat ini tidak tersedia."`.
- Return False.

### `async def _build_payment(client, user, amount, product_line)`
- **Alur**:
  1. `fakeinfo = client.ns.utils.faker.generate()`; `random_message = generate_safe_saweria_message(fakeinfo.name)`; `saweria_user_id = getVars("SAWERIA_USER_ID")`.
  2. `(qr_string, transaction_id, qr_image_stream, amount_raw) = await client.services.saweria.create_payment(user_id=saweria_user_id, amount=int(amount), name=fakeinfo.name, email=fakeinfo.email, message=random_message, creator_name=client.me.username)`.
  3. `formatted_amount = f"{int(amount_raw):,}"`.
  4. Caption (verbatim):
     ```
     **{emoji.white_check_mark} Pembayaran Siap Dilakukan!**

     Silakan scan QRIS di atas untuk membayar. Setelah itu, tekan tombol **Konfirmasi Pembayaran**.

     ╭─ **Detail Tagihan**
     │
     ├─ {emoji.shopping_bags} **Produk:** {product_line}
     ├─ {emoji.gem} **Jumlah:** `Rp {formatted_amount}`
     ├─ {emoji.id_card} **Order ID:** [{transaction_id}](https://saweria.co/qris/{transaction_id})
     │
     ╰─ {emoji.down_pointing} **Jika sudah membayar, silakan klik tombol di bawah ini.**
     ```
  5. Layout: satu baris `✅ Konfirmasi Pembayaran` → `confirm_payment {transaction_id}` (green).
  6. Return `(transaction_id, amount_raw, qr_image_stream, caption, btn)`.

### `async def _create_payment_invoice(client, user, item_index, tipe, amount, coupon_code=None)`
- **Alur**:
  1. `vvip_list = getListVars("list_vvip")`; `item = vvip_list[item_index]` (IndexError → kirim `"{emoji.cross_mark} Paket VVIP tidak ditemukan."`).
  2. `if not await _ensure_saweria_available(client, user): return`.
  3. `msg = send_message(user.id, "{emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.")`.
  4. `_build_payment(client, user, amount, f"{names} ({tipe.title()})")` (produk: `nama (Normal/Promo)`).
  5. `order_data = f"{item_index}|{tipe}|{amount_raw}"`; jika `coupon_code` → `order_data += f"|{coupon_code}"`.
  6. `ctx.db.setVars(client.me.id, transaction_id, order_data)` — key = transaction id saweria.
  7. `send_photo(user.id, photo=qr_image_stream, caption=caption, reply_markup=btn)`; `msg.delete()`.
  8. Except `Exception as e` → `msg.edit("{emoji.cross_mark} **Terjadi Kesalahan**\n<pre>{e}</pre>")`.

- **Format order_data**: `<item_index>|<tipe:normal|promo>|<amount_raw>[|<coupon_code>]`.

### `async def _create_all_vvip_payment_invoice(client, user, selected_items, total_amount)`
- **Alur**:
  1. `_ensure_saweria_available`.
  2. `msg = send_message("...Sedang Memproses...")`.
  3. `_build_payment(client, user, total_amount, f"Semua VIP ({len} paket)")`.
  4. `package_indexes = ",".join(str(item.get("index")) for item in selected_items)`.
  5. `order_data = f"ALL|normal|{int(amount_raw)}|{package_indexes}"`.
  6. `setVars(client.me.id, transaction_id, order_data)` → `send_photo(...)` → `msg.delete()`.
  7. Except → `msg.edit("{emoji.cross_mark} **Terjadi Kesalahan**\n<pre>{e}</pre>")`.

- **Format order_data (bundle)**: `ALL|normal|<amount_raw>|<comma_separated_indexes>`.

- **API payment**: `client.services.saweria.create_payment` (buat QRIS Saweria). API pyrogram: `send_photo`.

---

## B.4 `payment/callbacks.py` — Callback Pembayaran (Menu Detail, Kupon, Paynow, Renew, Pay All)

- `INVITE_LINK_MINUTES = 60`; `INVITE_MEMBER_LIMIT = 1` (di confirm.py sebenarnya).
- Import: `_create_all_vvip_payment_invoice`, `_create_payment_invoice` dari `.invoice`; `_get_all_vvip_items` dari `.verifier`.

### Helper `_reply_caption_or_text(callback_query, text, btn)` — caption/text.
### Helper `_resolve_item_index(callback_query, item_id)`
- Jika `item_id.isdigit()` → `int(item_id)` (index list).
- Jika tidak digit: jika `ctx.vip_list` ada dan `item_id in ctx.vip_list` → `return ctx.vip_list[item_id]` (resolusi id→nama? note: `ctx.vip_list` maps id→nama, jadi dikembalikan nama — hati-hati, ini dipakai sebagai index). Jika tidak → `None`.

### Helper `_build_back_row(client)`
- `{text: "• Kembali ke Daftar VVIP •", callback_data: "list_vvip", style: blue}`.

### Handler 1: `pay_all_vvip`
- **Dekorator**: `@command(lambda ctx: filters.regex("^pay_all_vvip$"), handler_type="callback")` — TANPA cek owner (untuk user biasa).
- **Fungsi**: `async def pay_all_vvip_callback(client, callback_query)`.
- **Alur**:
  1. `vvip_list = getListVars("list_vvip") or []`; `selected_items = _get_all_vvip_items(vvip_list)`.
  2. Jika kosong → `answer("❌ Tidak ada paket VIP valid untuk pembelian semua VIP.", show_alert=True)`.
  3. Jika `message.photo` → `message.delete()`; else `edit_message_text("{emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.")`.
  4. `total_amount = sum(item.get("price",0) for item in selected_items)`.
  5. `await _create_all_vvip_payment_invoice(client, callback_query.from_user, selected_items, total_amount)`.

### Handler 2: `notes_(.+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^notes_(.+)"), handler_type="callback")`
- **Fungsi**: `async def notes_data(client, callback_query)`.
- **Alur**:
  1. `item_id = matches[0].group(1)`; `item_index = _resolve_item_index(...)`; jika None → alert `"Sesi kedaluwarsa, silakan muat ulang menu."`.
  2. `vvip_list = getListVars("list_vvip")`; `item = vvip_list[item_index]` (IndexError → None).
  3. Jika ada:
     - `name, price_val, normal_text = item.get(...)`; `formatted_price = f"{price_val:,}"`.
     - `desc = normal_text.format(name=name, price=formatted_price)` jika ada; default:
       ```
       ╭─ **{emoji.sparkles} Detail Paket VVIP**
       │
       ├─ {emoji.open_folder} **Nama Paket:** `{name}`
       ├─ {emoji.pencil} **Deskripsi:** Dapatkan akses instan ke konten premium dan eksklusif setelah pembayaran berhasil.
       │
       ├─ {emoji.gem} **Harga Normal:** `Rp {formatted_price}`
       │
       ╰─ Silakan klik tombol 'Bayar' di bawah untuk melanjutkan!
       ```
     - Layout:
       - Baris 1: `💸 Bayar Harga Normal` → `paynow_{item_index}_normal_{price_val}` (green).
       - Baris 2: `🎟️ Gunakan Kupon` → `apply_coupon_{item_index}_normal_{price_val}` (blue); + `back_row[0]`.
     - `_reply_caption_or_text(callback_query, desc, btn)`.
  4. Jika tidak → `"{emoji.cross_mark} Paket VVIP tidak ditemukan."` + back row.

### Handler 3: `promo_detail_(.+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^promo_detail_(.+)"), handler_type="callback")`
- **Fungsi**: `async def promo_detail(client, callback_query)`.
- **Alur** (mirip notes, utk promo):
  - Hanya tampil jika `item and item.get("promo_price",0) > 0`.
  - `desc = promo_text.format(name=name, promo_price=formatted_promo)` jika ada; default:
    ```
    ╭─ **{emoji.party_popper} Penawaran Spesial Terbatas!**
    │
    ├─ {emoji.open_folder} **Nama Paket:** `{name}`
    ├─ {emoji.pencil} **Deskripsi:** Jangan lewatkan kesempatan emas ini untuk bergabung dengan harga yang jauh lebih terjangkau!
    │
    ├─ {emoji.money_bag} **Harga Promo:** `Rp {formatted_promo}`
    │
    ╰─ Segera amankan slot Anda sebelum promo berakhir!
    ```
  - Layout:
    - Baris 1: `✅ Bayar Harga Promo` → `paynow_{item_index}_promo_{promo_price_val}` (green).
    - Baris 2: `🎟️ Gunakan Kupon` → `apply_coupon_{item_index}_promo_{promo_price_val}` (blue); + back.
  - Jika tidak valid → `"{emoji.cross_mark} Paket promo tidak ditemukan atau tidak aktif."`.

### Handler 4: `apply_coupon_(\d+)_(normal|promo)_(\d+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^apply_coupon_(\\d+)_(normal|promo)_(\\d+)"), handler_type="callback")`
- **Fungsi**: `async def apply_coupon_callback(client, callback_query)`.
- **Parameter regex**: `group(1)=item_index`, `group(2)=tipe`, `group(3)=original_amount`.
- **Alur**:
  1. `chat_id = from_user.id`; delete callback msg.
  2. `ask_msg = await client.ask(chat_id, "Silakan masukkan kode kupon Anda.\n\nKetik `/batal` untuk membatalkan.", timeout=300)`; `/batal` → UserCancelled; `coupon_code = text.upper()`.
  3. `coupons = getListVars("coupons")`; cari `c.get("code")==coupon_code`.
     - Tidak ditemukan → raise `ValueError("{emoji.cross_mark} Kode kupon tidak valid.")`.
     - `uses_left <= 0` → `ValueError("{emoji.cross_mark} Kupon ini sudah habis digunakan.")`.
     - `expiry_str` ada & `datetime.fromisoformat(expiry_str) < datetime.now(timezone.utc)` → `ValueError("{emoji.cross_mark} Kupon ini sudah kedaluwarsa.")`.
  4. Hitung diskon:
     - percentage: `final = original - original * (discount_value / 100)`.
     - fixed: `final = original - discount_value`.
     - `final_amount = max(1000, int(final))` — minimum Rp 1000.
  5. Kirim: `"{emoji.white_check_mark} Kupon `{coupon_code}` berhasil digunakan! Harga awal `Rp {original_amount:,}` menjadi `Rp {final_amount:,}`."`.
  6. `await _create_payment_invoice(client, callback_query.from_user, item_index, tipe, final_amount, coupon_code)`.
  7. Except UserCancelled → `"{emoji.cross_mark} **Proses Dibatalkan**"`; TimeoutError → `"{emoji.alarm_clock} **Waktu Habis**\nProses telah dibatalkan otomatis."`; ValueError → kirim `str(e)`; Exception → `"{emoji.cross_mark} **Terjadi Kesalahan**\n<pre>{e}</pre>"`.

- **DB**: baca `coupons`, baca `list_vvip` (via invoice).

### Handler 5: `paynow_(\d+)_(normal|promo)_(\d+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^paynow_(\\d+)_(normal|promo)_(\\d+)"), handler_type="callback")`
- **Fungsi**: `async def paynow(client, callback_query)`.
- **Alur**:
  1. Parse `item_index`, `tipe`, `amount`.
  2. Jika photo → delete; else `edit_message_text("{emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.")`.
  3. `await _create_payment_invoice(client, callback_query.from_user, item_index, tipe, amount)`.

### Handler 6: `renew_sub_(\d+)` (perpanjang)
- **Dekorator**: `@command(lambda ctx: filters.regex("^renew_sub_(\\d+)"), handler_type="callback")`
- **Fungsi**: `async def renew_subscription_callback(client, callback_query)`.
- **Alur**:
  1. `item_index = int(match.group(1))`; `item = vvip_list[item_index]` (IndexError → alert `"❌ Paket VVIP tidak ditemukan."`).
  2. Jika `item.get("promo_price",0) > 0` → set `callback_query.data = f"promo_detail_{item_index}"`, `matches = [re.match(...)]`, panggil `promo_detail`.
  3. Else → set `callback_query.data = f"notes_{item_index}"`, `matches=[re.match("notes_(\d+)",...)]`, panggil `notes_data`.

---

## B.5 `payment/confirm.py` — Konfirmasi Pembayaran & Fulfillment

Konstanta: `INVITE_LINK_MINUTES = 60`, `INVITE_MEMBER_LIMIT = 1`.

### `async def _create_one_time_invite(client, target_chat_id)`
- `expire_date_link = datetime.now() + timedelta(minutes=60)`.
- `invite_link_obj = await client.create_chat_invite_link(chat_id=target_chat_id, member_limit=1, expire_date=expire_date_link)` → return `.invite_link`.

### `_build_member_data(user, name, tipe, target_chat_id, item_found)`
- Kamus: `{user_id: user.id, vvip_name: name, join_date: datetime.now(timezone.utc).isoformat(), payment_type: tipe, chat_id_kick: target_chat_id}`.
- Jika `item_found.get("duration",0) > 0` → tambah `expiry_date = (datetime.now(timezone.utc)+timedelta(days=duration)).isoformat()`.

### `async def _record_revenue(client, user, amount_raw, item_name, tipe)`
- Kamus: `{user_id, username: user.username or user.first_name, amount, date: isoformat(utc), item_name, type: tipe}` → `setListVars(client.me.id, "vip_revenue_history", revenue_data)`.

### `async def _notify_new_income(client, user, item_label)`
- `owner_bot_id = await get_notification_target(client)`; `user_mention_str = client.ns.telegram.arg.getMention(user)`; `bot_mention_str = client.me.mention`.
- Kirim ke owner_bot_id:
  ```
  {emoji.money_bag} **Pemasukan Baru!**

  **Pengguna:** {mention}
  **Bot:** {bot_mention}
  **Kategori:** `{item_label}`
  ```

### `async def _consume_coupons(client, coupon_code)`
- `coupons = getListVars("coupons")`; untuk `c` dengan code sama → `c["uses_left"] -= 1`, break.
- `removeVars(client.me.id, "coupons")` (hapus seluruh list key), lalu re-append tiap kupon via `setListVars` (rewrite list tanpa duplikat).

### `_parse_ref(transaction_id, ref_data_str)`
- `ref_parts = ref_data_str.split("|")`.
- `is_bundle_order = (ref_parts[0] == "ALL")`.
- `tipe = ref_parts[1]`; `amount_raw = int(ref_parts[2])`; `coupon_code = None`; `bundle_indexes = []`.
- Jika bundle: `bundle_indexes = [int(i) for i in ref_parts[3].split(",") if i.strip().isdigit()]` (jika ada ref_parts[3]).
- Else: `item_index = int(ref_parts[0])`; `coupon_code = ref_parts[3] if len(ref_parts)>3 else None`.
- Return `(is_bundle_order, tipe, amount_raw, coupon_code, bundle_indexes, item_index)`. **Catatan**: `item_index` tidak dikembalikan secara eksplisit di Python return statement — lihat baris 92: `return is_bundle_order, tipe, amount_raw, coupon_code, bundle_indexes`. Namun di handler `item_index` dipanggil — jadi implementasi TS harus mensimulasikan bahwa `item_index` DIDAPAT dari `int(ref_parts[0])` saat non-bundle dan dikembalikan sebagai tuple element. (Pada file asli Python, `_parse_ref` mengembalikan 5 elemen & handler memakai `item_index` setelahnya yang jelas merupakan bug-potensial; untuk porting tulis ulang secara wajar: return juga `item_index`.)

### Handler 1: `confirm_payment\s(.+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^confirm_payment\\s(.+)"), handler_type="callback")`
- **Fungsi**: `async def manual_check_payment_callback(client, callback_query)`.
- **Alur**:
  1. `transaction_id = callback_query.data.split(" ", 1)[1]`; `user = callback_query.from_user`.
  2. `ref_data_str = await ctx.db.getVars(client.me.id, transaction_id)`.
  3. Jika tidak ada → `answer("⚠️ Invoice ini sudah tidak valid atau telah selesai.", show_alert=True)`.
  4. Parse ref (bundle/non-bundle).
  5. `is_owner_confirm = await is_bot_owner(client, user.id)`; `is_paid = is_owner_confirm or await client.services.saweria.check_paid_status(transaction_id)` (owner bisa langsung konfirm tanpa cek).
  6. Jika **bukan** paid → `answer("❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah beberapa saat.", show_alert=True)`.
  7. Jika **paid**:
     - `await callback_query.edit_message_reply_markup(None)` (hapus tombol).
     - `await ctx.db.removeVars(client.me.id, transaction_id)` (hapus ref order).
     - `vvip_list = getListVars("list_vvip")`.
     - **Bila bundle (`is_bundle_order`)**:
       - Loop tiap idx di `bundle_indexes`: `item_found = vvip_list[idx]` (IndexError → skip); `name`, `target_chat_id = chat_id_normal`; jika `not target_chat_id` → skip.
       - `link = await _create_one_time_invite(client, target_chat_id)` (gagal → log `"Gagal membuat invite link bundle untuk {target_chat_id}: {e}"`, continue).
       - `member_data = _build_member_data(user, name, "normal", target_chat_id, item_found)`; `setListVars(client.me.id, "vvip_members", member_data)` (append member per paket).
       - `purchased_names.append(name)`; `invite_payloads.append({name, chat_id: target_chat_id, link})`.
       - Jika `not invite_payloads` → `raise ValueError("Tidak ada paket VIP valid untuk pembelian semua VIP.")`.
       - `item_label = " + ".join(purchased_names)`; `_record_revenue(client, user, amount_raw, item_label, "bundle")`.
       - `link_text = "\n".join(f"• {item['name']}: {item['link']}" ...)`.
       - Kirim ke `user.id` (protect_content=True):
         ```
         {emoji.party_popper} **Pembayaran Paket Semua VIP Berhasil!**

         Berikut semua link akses VIP Anda:

         {link_text}

         {emoji.exclamation} Setiap link hanya berlaku 1 kali klik dan kedaluwarsa dalam 60 menit.
         ```
       - `await callback_query.message.delete()`; `asyncio.create_task(verify_user_join_multiple(client, user, invite_payloads, link_msg))`.
       - `_notify_new_income(client, user, "Semua VIP (Bundle)")`; return.
     - **Non-bundle**:
       - `item_found = vvip_list[item_index]` (IndexError → raise `"Kategori VVIP tidak ditemukan di database."`); `name`.
       - `is_promo = tipe == "promo"`; `target_chat_id = chat_id_promo if is_promo else chat_id_normal`; jika tidak → raise `"Chat ID untuk paket VVIP ini belum diatur oleh admin."`.
       - `link = await _create_one_time_invite(...)` (gagal → log, raise `"Gagal membuat link undangan."`).
       - `member_data = _build_member_data(user, name, tipe, target_chat_id, item_found)`.
       - Jika `coupon_code` → `_consume_coupons(client, coupon_code)`.
       - `setListVars(client.me.id, "vvip_members", member_data)`; `_record_revenue(client, user, amount_raw, name, tipe)`.
       - Kirim ke user (protect_content=True):
         ```
         {emoji.party_popper} **Pembayaran Dikonfirmasi!**

         Terima kasih, berikut adalah link akses Anda untuk paket **{name}**:

         {link}

         {emoji.exclamation} Link ini hanya berlaku untuk 1 kali klik dan akan kedaluwarsa dalam 60 menit jika tidak digunakan.
         ```
       - `callback_query.message.delete()`; `asyncio.create_task(verify_user_join(client, user, target_chat_id, link_msg))`.
       - `_notify_new_income(client, user, f"{name} ({tipe.title()})")`.
  8. Except `Exception as e` → `callback_query.answer(f"**Terjadi Kesalahan**\n{e}", show_alert=True)`.

- **DB**: baca `<transaction_id>` (ref order); tulis `vvip_members`, `vip_revenue_history`, `coupons` (via _consume). Hapus `<transaction_id>`, hapus/rebuilt `coupons`.
- **API payment**: `client.services.saweria.check_paid_status(transaction_id)`. API pyrogram: `create_chat_invite_link(chat_id, member_limit=1, expire_date)`, `send_message(protect_content=True)`, `edit_message_reply_markup`.

### Handler 2: PreCheckout
- **Dekorator**: `@command(lambda ctx: filters.PreCheckoutQuery, handler_type="pre_checkout")`
- **Fungsi**: `async def pre_checkout_handler(client, pre_checkout_query)`.
- **Alur**: `await pre_checkout_query.answer(ok=True)` — selalu menyetujui.

---

## B.6 `payment/stars.py` — Donasi Stars

### Handler: `successful_payment`
- **Dekorator**: `@command(lambda ctx: filters.successful_payment)` — handler_type default `message`.
- **Fungsi**: `async def successful_donation_handler(client, message)`.
- **Alur**:
  1. `payload = message.successful_payment.invoice_payload`; jika `not payload.startswith("donation_")` → return (abaikan non-donasi).
  2. `user = message.from_user`; `stars_donated = message.successful_payment.total_amount`; `charge_id = message.successful_payment.telegram_payment_charge_id`; `current_bot_id = client.me.id`; `super_admin_id = ctx.owner_id`.
  3. Balas ke user:
     ```
     {emoji.party_popper} **Terima Kasih Banyak, {user.first_name}!**

     Kami telah menerima donasi Anda sebesar **{stars_donated} Stars ({emoji.star})**.
     Dukungan Anda adalah bahan bakar semangat bagi kami. Semoga hari Anda menyenangkan!
     ```
  4. `owner_of_this_bot = await get_notification_target(client)`; `main_bot_client = ctx.manager.main_bot_client`.
  5. Notifikasi ke owner bot:
     - `user_mention_str = client.ns.telegram.arg.getMention(user)`; `bot_mention_str = client.me.mention`.
     - Teks:
       ```
       {emoji.sparkles} **Donasi Baru Diterima!**

       **Jumlah:** `{stars_donated}` Stars ({emoji.star})
       **Dari:** {mention} (`{user.id}`)
       **Melalui Bot:** {bot_mention}
       ```
     - `refund_key = uuid.uuid4().hex[:16]`; simpan `ctx.db.setVars(current_bot_id, f"refund_{refund_key}", {user_id: user.id, charge_id: charge_id})`.
     - `refund_callback_data = f"refund_stars_{refund_key}"`. Tombol: `🔙 Kembalikan Donasi` → `refund_stars_{refund_key}` (red).
     - `await client.send_message(chat_id=owner_of_this_bot, text=notification_text, reply_markup=refund_btn)`.
  6. `except pyrogram.errors.UserIsBlocked`: jika `main_bot_client` dan `owner_of_this_bot != super_admin_id` → kirim via main bot ke save:
     ```
     {emoji.exclamation} **Notifikasi Gagal Terkirim**

     Notifikasi donasi sebesar `{stars_donated}` Stars dari {mention} gagal dikirim ke owner bot `{client.me.first_name}` karena bot diblokir olehnya.
     ```
  7. `except Exception as e`: `ctx.log.print(f"Gagal mengirim notifikasi donasi: {e}")`.

- **DB**: tulis `refund_{key}` → `{user_id, charge_id}`.

---

# C. DIRECTORY `allbots/`

- Base: `from .. import *` → import semua (termasuk `asyncio`, `datetime`, `timezone`, `timedelta`, `pyrogram`, `ctx`, `command`, `filters`).
- Semua handler allbots hanya untuk super admin: `callback_query.from_user.id != ctx.owner_id` → return (tidak ada pesan).

## C.1 `allbots/__init__.py`
Re-export `.delete`, `.detail`, `.duration`, `.list`.

## C.2 `allbots/helpers.py` — Penyusun halaman daftar semua bot

- `_page_cache: dict[int, dict]` (cache halaman). `ITEMS_PER_PAGE = 25`.

### `_resolve_owner_text(client, owner_id)`
- Jika `not owner_id` → `"Tidak diketahui"`.
- Cek `_user_cache` (Tempat `admin.cache._user_cache`); jika ada → `arg.getMention(cached)`.
- Else `client.get_users(owner_id)`; `_user_cache.set(owner_id, user)`; return mention.
- Except → `f"ID <code>{owner_id}</code>"`.

### `_prefetch_owners(client, owner_ids)`
- Kumpulkan owner id yang belum di-cache; `asyncio.gather(*[client.get_users(oid)...], return_exceptions=True)`; set ke `_user_cache` yang sukses.

### `_bot_username_status(client, bot_id)`
- `ctx.manager.running_bots.get(bot_id)`; jika ada & `is_connected`: return `@username` atau `first_name`; jika tidak → `"Offline"`; exception → `"Error"`.

### `_days_left_text(client, bot_id)`
- `exp_date_str = getVars(bot_id, "bot_expiration_date")`; jika tak ada → `"N/A"`; else `(datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days` (int).

### `_build_page(client, page)`
- `all_bots = await ctx.db.getBots(is_token=True)`; kosong → `{"empty": True}`.
- `total_pages = ceil(len/25)`; `page = (page + total_pages) % total_pages`; slice `[page*25 : (page+1)*25]`.
- Untuk tiap bot: `bot_id = int(bot_data["name"])`; `owner_ids[bot_id] = getVars(bot_id, "owner_id")`; `_prefetch_owners`.
- Teks baris (HTML parse, `\n` join):
  ```
  <b>{emoji.open_folder} Daftar Semua Bot ({page + 1}/{total_pages})</b>

  <b>{index:2}:</b> {bot_username} (<code>{bot_id}</code>)
   ├ {emoji.bust_in_silhouette} Owner: {owner_text}
   ├ {emoji.hourglass} Aktif: <code>{days_left}</code> hari lagi
  ```
- Tombol: tiap bot tombol `str(index)` → `allbots_detail_{bot_id}_{page}`, 5 tombol per baris.
- Jika `total_pages > 1`: baris `« Prev` → `allbots_{prev_page}`; `Next »` → `allbots_{next_page}`.
- Baris akhir: `Tutup Panel` → `close_panel` (red).
- Return dict `{empty, page, total_pages, text, layout, bot_rows}`.

### `send_allbots_list(client, message_or_query, page, force_refresh=False)`
- If `force_refresh`: `_page_cache.pop(page, None)`.
- Jika `page not in _page_cache` → `_page_cache[page] = await _build_page(client, page)`.
- Jika `cached["empty"]` → teks `"Belum ada bot yang dibuat oleh pengguna manapun."`; jika Message → `message_or_query.reply_text(text)`; jika CallbackQuery → `answer(text, show_alert=True)`.
- Else `btn = build_button_grid(cached["layout"])`; jika Message → `reply_text(cached["text"], reply_markup=btn, parse_mode=ParseMode.HTML)`; jika CallbackQuery → `edit_message_text(...)`.

### `invalidate_page_cache(page=None)`
- `None` → `_page_cache.clear()`; else pop page.

## C.3 `allbots/list.py`

### Handler 1: `/allbots` (superadmin)
- **Dekorator**: `@command(lambda ctx: filters.command("allbots") & filters.user(ctx.owner_id))` — handler_type default message.
- **Fungsi**: `async def allbots_command_handler(client, message)`.
- **Alur**:
  1. `invalidate_page_cache()` (clear semua).
  2. `msg_process = await message.reply(f"{emoji.repeat} Sedang memproses mengumpulkan bot")`.
  3. `await send_allbots_list(client, message, 0, force_refresh=True)`.
  4. `await msg_process.delete()`.

### Handler 2: `allbots_(-?\d+)` (paginasi)
- **Dekorator**: `@command(lambda ctx: filters.regex("^allbots_(\\-?\\d+)"), handler_type="callback")`
- **Fungsi**: `async def allbots_pagination_callback(client, callback_query)`.
- Cek `from_user.id != ctx.owner_id` → return.
- `page = int(callback_query.data.split("_")[1])`; `await send_allbots_list(client, callback_query, page)`.

## C.4 `allbots/detail.py`

### `_build_detail_text(client, bot_id)`
- `bot_name = f"Bot ID {bot_id}"`; `bot_username = "Offline"`. Jika running & connected → `bot_name = me.first_name`; `bot_username = me.username or "Tidak Ada"`.
- `owner_id = getVars(bot_id, "owner_id")`; `owner_text = _resolve_owner_text`.
- `exp_date_str = getVars(bot_id, "bot_expiration_date")`; `days_left = ...days else "N/A"`.
- Teks:
  ```
  **{emoji.toolbox} Kelola Bot Spesifik**

  • **Nama Bot:** {bot_name}
  • **ID Bot:** `{bot_id}`
  • **Username Bot:** @{bot_username}
  • **Pemilik:** {owner_text}
  • **Sisa Aktif:** `{days_left}` hari
  ```

### `_build_detail_layout(client, bot_id, page)`
- Baris 1: `🗑️ Hapus Bot` → `allbots_confirm_delete_{bot_id}_{page}` (red).
- Baris 2: `🗓️ Kelola Masa Aktif` → `allbots_duration_{bot_id}_{page}` (blue).
- Baris 3: `🔙 Kembali ke Daftar` → `allbots_back_{page}` (blue).

### Handler 1: `allbots_detail_(\d+)_(\d+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^allbots_detail_(\\d+)_(\\d+)"), handler_type="callback")`
- **Fungsi**: `async def allbots_detail_callback(client, callback_query)`.
- `bot_id = matches[1]`; `page = matches[2]`; `edit_message_text(text, reply_markup=build(detail_layout))`.

### Handler 2: `allbots_back_(\d+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^allbots_back_(\\d+)"), handler_type="callback")`
- **Fungsi**: `async def allbots_back_callback(client, callback_query)`.
- `page`; `await send_allbots_list(client, callback_query, page)` (pakai cache).

## C.5 `allbots/delete.py`

### Handler 1: `allbots_confirm_delete_(\d+)_(\d+)`
- **Fungsi**: `async def allbots_confirm_delete_callback(client, callback_query)`.
- Layout konfirmasi:
  - Baris 1: `✅ Ya, Hapus` → `allbots_do_delete_{bot_id}_{page}` (red); `❌ Tidak` → `allbots_back_{page}` (green).
- Teks:
  ```
  **{emoji.warning} Konfirmasi Penghapusan**

  Anda yakin ingin menghapus bot dengan ID `{bot_id}` secara permanen?
  ```

### Handler 2: `allbots_do_delete_(\d+)_(\d+)`
- **Fungsi**: `async def allbots_do_delete_callback(client, callback_query)`.
- **Alur**:
  1. `edit_message_text(f"{emoji.hourglass} Menghapus bot...")`.
  2. `owner_id_to_invalidate = getVars(bot_id, "owner_id")`.
  3. `await ctx.manager.stop_bot(bot_id)`; `await asyncio.sleep(1)`.
  4. `await ctx.db.removeBot(bot_id)`; `await ctx.db.removeAllVars(bot_id)` — hapus SEMUA data bot.
  5. Jika owner → `_user_cache.invalidate(owner_id_to_invalidate)`.
  6. `invalidate_page_cache(page)`; `await send_allbots_list(client, callback_query, page, force_refresh=True)`; `answer("✅ Bot berhasil dihapus.", show_alert=True)`.
  7. Except → `answer("❌Gagal menghapus bot: {e}", show_alert=True)`; `send_allbots_list(client, callback_query, 0, force_refresh=True)`.

## C.6 `allbots/duration.py`

### Helper `_expiry_delta_layout(client, bot_id, page, sign, days)`
- `callback_prefix = "allbots_do_extend"` jika sign `+`, else `"allbots_do_reduce"`.
- `style = green jika + else red`; emoji plus/minus.
- Return dict `{text: f"{sign}{days} hari", callback_data: f"{callback_prefix}_{bot_id}_{days}_{page}", style, emoji}`.

### Handler 1: `allbots_duration_(\d+)_(\d+)`
- **Fungsi**: `async def allbots_duration_callback(client, callback_query)`.
- Layout:
  - Baris 1: `➕ Tambah Masa Aktif` → `allbots_extend_{bot_id}_{page}` (green).
  - Baris 2: `➖ Kurangi Masa Aktif` → `allbots_reduce_{bot_id}_{page}` (red).
  - Baris 3: `• Kembali •` → `allbots_back_{page}` (blue).
- Teks: `**{emoji.calendar} Kelola Masa Aktif untuk Bot `{bot_id}`**`.

### Handler 2: `allbots_extend_(\d+)_(\d+)`
- **Fungsi**: `async def allbots_extend_callback(client, callback_query)`.
- Tombol = `[_expiry_delta_layout(..,"+",d) for d in [7,30,90]]` (satu baris: `+7 hari`, `+30 hari`, `+90 hari`); baris 2: `• Kembali •` → `allbots_duration_{bot_id}_{page}`.
- Teks: `Pilih durasi untuk ditambahkan ke Bot `{bot_id}`:`.

### Handler 3: `allbots_do_extend_(\d+)_(\d+)_(\d+)`
- `bot_id`, `days`, `page`.
- `current_expiry_str = getVars(bot_id, "bot_expiration_date")`; `start_date = now(utc)`; jika ada & `current_expiry > now` → `start_date = current_expiry` (extend dari tanggal kadaluarsa, bukan sekarang).
- `setVars(bot_id, "bot_expiration_date", (start_date + timedelta(days)).isoformat())`.
- `answer(f"{days} hari berhasil ditambahkan ke bot {bot_id}.", show_alert=True)`.
- `invalidate_page_cache(page)`; `send_allbots_list(..., page, force_refresh=True)`.

### Handler 4: `allbots_reduce_(\d+)_(\d+)`
- Sama pola extend tapi label `-`, callback `allbots_do_reduce`, teks `Pilih durasi untuk dikurangi dari Bot `{bot_id}`:`.

### Handler 5: `allbots_do_reduce_(\d+)_(\d+)_(\d+)`
- `bot_id`, `days`, `page`.
- Jika `not current_expiry_str` → `answer("Bot ini tidak memiliki tanggal kedaluwarsa untuk dikurangi.", show_alert=True)`; return.
- `new_expiry_date = fromisoformat(current) - timedelta(days)`; `setVars(bot_id, "bot_expiration_date", new.isoformat())`.
- `answer(f"Masa aktif bot {bot_id} berhasil dikurangi {days} hari.", show_alert=True)`.
- `invalidate_page_cache(page)`; `send_allbots_list(..., force_refresh=True)`.

---

# D. DIRECTORY `send_gift/`

## D.1 `send_gift/_send_gift.py` — Kirim Hadiah Telegram (Star Gift)

### `async def send_star_gift_raw(client, user_id, gift_id)`
- **API pyrogram RAW (MTProto)**:
  1. `peer = await client.resolve_peer(user_id)`.
  2. `invoice = types.InputInvoiceStarGift(peer=peer, gift_id=int(gift_id))`.
  3. `payment_form = await client.invoke(functions.payments.GetPaymentForm(invoice=invoice))`.
  4. `form_id = payment_form.form_id`.
  5. `result = await client.invoke(functions.payments.SendStarsForm(form_id=form_id, invoice=invoice))`.
  6. return result.

### `async def _require_owner(client, callback_query)`
- Jika bukan owner → `answer("🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True)`, return False; else True.

### `async def _send_gift_detail(client, message, gift)`
- `price = gift.star_count`; `emoji = "❓️"`; jika `gift.sticker.emoji` → `emoji = f"{gift.sticker.emoji} "`.
- Caption (HTML):
  ```
  <b>{emoji.gift} Info Hadiah</b>

  <b>{emoji.id_card} ID:</b> <code>{gift.id}</code>
  <b>{emoji.money_bag} Harga:</b> <code>{price} Stars</code>
  <b>{emoji.performing_arts} Emoji:</b> {emoji}
  ```
- Layout:
  - Baris 1: `🎁 Kirim ke Teman` → `gift_send_ask_{gift.id}` (blue).
  - Baris 2: `👤 Klaim Sendiri` → `gift_claim_self_{gift.id}` (green).
- Jika `gift.sticker.thumbs` → download thumb terakhir (`client.download_media(thumb.file_id)`), `send_photo(message.chat.id, photo=file_path, caption=caption, reply_markup=markup)`, return.
- Else `send_message(... text=caption, reply_markup=markup)`.
- Except → tetap `send_message(...)` fallback.
- `finally`: hapus file temp jika ada (`aiofiles.os.remove`).

### Handler 1: `/gift` (private, owner)
- **Dekorator**: `@command(lambda ctx: filters.command("gift") & filters.private)` — message.
- **Fungsi**: `async def send_gift_handler(client, message)`.
- **Alur**:
  1. Cek owner.
  2. Resolusi target: jika `message.reply_to_message` → `user_id_target = reply_to.from_user.id`; `gift_id_arg = message.command[1]` (jika ada). Else jika `len(command) > 2` → coba `client.get_users(command[1])` → `user_id_target`, `gift_id_arg = command[2]`.
  3. Jika `not user_id_target` → reply:
     ```
     {emoji.cross_mark} **Target tidak ditemukan.**
     Balas pesan pengguna atau gunakan format:
     `/gift [username] [gift_id]`
     ```
  4. Jika `not gift_id_arg or not isdigit` → reply:
     ```
     {emoji.cross_mark} **ID Hadiah tidak valid.**
     Gunakan `/listgift` untuk melihat ID.
     ```
  5. `gift_id = int(gift_id_arg)`; `status_msg = reply(f"{emoji.repeat} Memproses pengiriman hadiah...")`.
  6. `available_gifts = await client.get_available_gifts()`; `target_gift = next(g for g in available_gifts if g.id == gift_id, None)`; tidak ada → `status_msg.edit("{emoji.cross_mark} Gift ID `{gift_id}` tidak ditemukan atau tidak tersedia.")`.
  7. `target_user = await client.get_users(user_id_target)`; `mention = arg.getMention(target_user)`; edit `"{emoji.gift} Mengirim hadiah **Star** (ID: `{gift_id}`) ke **{mention}**..."`.
  8. `await send_star_gift_raw(client, target_user.id, gift_id)`; edit `"{emoji.white_check_mark} Berhasil mengirim hadiah ke **{mention}**!"`.
  9. Except → `message.reply_text("{emoji.cross_mark} Gagal mengirim hadiah: `{e}`")`.

- **API pyrogram**: `client.get_available_gifts()`, `client.get_users`, RAW functions.

### Handler 2: `/listgift` (private, owner)
- **Dekorator**: `@command(lambda ctx: filters.command("listgift") & filters.private)`.
- **Fungsi**: `async def list_gift_handler(client, message)`.
- **Alur**:
  1. Cek owner.
  2. `status_msg = reply(f"{emoji.repeat} Mengambil daftar hadiah...")`.
  3. `gifts = await client.get_available_gifts()`; kosong → `status_msg.edit("{emoji.exclamation} Tidak ada hadiah yang tersedia saat ini.")`.
  4. Untuk tiap gift `if not gift.is_sold_out`: `await _send_gift_detail(client, message, gift)`; `await asyncio.sleep(1.5)`.
  5. `await status_msg.delete()`.
  6. Except → `status_msg.edit("{emoji.cross_mark} Gagal mengirim hadiah: `{e}`")`.

### Handler 3: `gift_claim_self_(\d+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^gift_claim_self_(\\d+)"), handler_type="callback")`
- **Fungsi**: `async def claim_self_gift_callback(client, callback_query)`.
- **Alur**:
  1. `_require_owner`.
  2. `gift_id = int(callback_query.data.split("_")[3])`; `user_id = from_user.id`.
  3. `edit_message_reply_markup(None)`.
  4. `await send_star_gift_raw(client, user_id, gift_id)`.
  5. `edit_message_caption("{emoji.white_check_mark} Berhasil mengklaim hadiah (ID: {gift_id}) untuk diri sendiri!")`.
  6. Except → `answer("❌ Gagal klaim: {e}", show_alert=True)`.

### Handler 4: `gift_send_ask_(\d+)`
- **Dekorator**: `@command(lambda ctx: filters.regex("^gift_send_ask_(\\d+)"), handler_type="callback")`
- **Fungsi**: `async def ask_send_gift_callback(client, callback_query)`.
- **Alur**:
  1. `_require_owner`.
  2. `gift_id = int(data.split("_")[3])`; `chat_id = message.chat.id`.
  3. `edit_message_reply_markup(None)`.
  4. Prompt:
     ```
     **{emoji.bust_in_silhouette} Kirim Hadiah**

     Silakan kirim **User ID** atau **Username** (@username) tujuan penerima hadiah.

     Ketik `/batal` untuk membatalkan.
     ```
  5. `ask_msg = await client.ask(chat_id, prompt, timeout=60)`; jika `/batal` → kirim `"{emoji.cross_mark} Pengiriman dibatalkan."`, return.
  6. `processing_msg = send_message(chat_id, "{emoji.repeat} Mencari pengguna `{target_input}`...")`.
  7. `target_user = await client.get_users(target_input)`; gagal → edit `"{emoji.cross_mark} Pengguna tidak ditemukan. Pastikan username/ID benar."`, return.
  8. Edit `"{emoji.gift} Mengirim hadiah **Star** (ID: `{gift_id}`) ke **{target_user.first_name}**..."`.
  9. `await send_star_gift_raw(client, target_user.id, gift_id)`; edit `"{emoji.white_check_mark} Berhasil mengirim hadiah ke **{target_user.first_name}**!"`.
  10. Except TimeoutError → `"{emoji.alarm_clock} Waktu habis. Silakan ulangi proses."`; Except `Exception as e` → `"{emoji.cross_mark} Gagal mengirim hadiah: `{e}`"`.

---

# E. RINGKASAN CROSS-CUTTING

## E.1 Daftar KEY DB yang dipakai (prefix `client.me.id`, kecuali allbots memakai `bot_id` dari daftar)
| Key | Tipe | Konteks |
|---|---|---|
| `SAWERIA_USER_ID` | scalar | API settings; dipakai invoice & services |
| `notif_chat_id` | scalar | Notification target |
| `owner_id` | scalar | otentikasi per-bot (is_bot_owner, get_notification_target) |
| `start_photo_id` | scalar | set_start_photo |
| `start_text_template` | scalar (markdown) | set_start_text |
| `broadcast_price` | scalar (int) | broadcast paid |
| `list_vvip` | list of objects `{name, price, duration, chat_id_normal, promo_price, chat_id_promo, promo_text, normal_text}` | pricing/payment |
| `coupons` | list of objects `{code, discount_type, discount_value, uses_left, expiry_date}` | coupons |
| `vip_revenue_history` | list of objects `{user_id, username, amount, date, item_name, type}` | revenue |
| `vvip_members` | list of objects `{user_id, vvip_name, join_date, payment_type, chat_id_kick, [expiry_date]}` | verify/confirm |
| `user_ids` | list of user ids | broadcast & new-user tracking |
| `<transaction_id>` | scalar string order_data | invoice ref |
| `refund_{key}` | object `{user_id, charge_id}` | stars refund |
| `bot_expiration_date` (key bot_id) | scalar ISO datetime | allbots duration |
| `owner_id` (key bot_id) | scalar | allbots |

## E.2 Format `order_data` (ref invoice)
- Tunggal: `<item_index>|<tipe:normal|promo>|<amount>|<coupon_code(opsional)>`
- Bundle: `ALL|normal|<amount>|<idx1,idx2,...>`

## E.3 Diskon kupon
- `percentage`: `amount - amount*(value/100)`; `fixed`: `amount - value`; dipaksa `max(1000, ...)`.

## E.4 Peta callback_data (dinamis)
- `confirm_payment {transaction_id}`
- `paynow_{idx}_{normal|promo}_{amount}`
- `promo_detail_{idx}` / `notes_{idx}`
- `apply_coupon_{idx}_{normal|promo}_{amount}`
- `renew_sub_{idx}`
- `delete_coupon {code} {page}` / `list_coupons_{page}`
- `delete_vvip {uuid8}` / `edit_vvip_price {uuid8}` (uuid pernah disimpan di `ctx.vip_list` / `ctx.vip_list_edit`)
- `set_api {SAWERIA}` / `del_api_confirm` / `do_del_api` / `api_settings`
- `allbots_detail_{bot_id}_{page}` / `allbots_back_{page}` / `allbots_confirm_delete_{bot_id}_{page}` / `allbots_do_delete_{bot_id}_{page}` / `allbots_duration_{bot_id}_{page}` / `allbots_extend_{bot_id}_{page}` / `allbots_reduce_{bot_id}_{page}` / `allbots_do_{extend|reduce}_{bot_id}_{days}_{page}` / `allbots_{page}`
- `gift_claim_self_{gift_id}` / `gift_send_ask_{gift_id}`
- `refund_stars_{refund_key}` (dipakai handler lain)
- Statis: `settings`, `start`, `vip_revenue_menu`, `show_revenue_{daily|weekly|monthly}`, `broadcast`, `set_broadcast_price`, `manage_coupons`, `add_coupon`, `setup_listvvip`, `delete_listvvip`, `edit_price_listvvip`, `set_start_photo`, `set_start_text`, `check_vvip_status`, `set_notif_chat`, `list_members_0`, `total_users_count`, `check_active_menu_init`, `stats_0`, `list_vvip`, `pay_all_vvip`, `close_panel`.