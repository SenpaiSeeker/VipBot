from . import *

async def get_start_keyboard_and_content(client, user):
    is_owner = await is_bot_owner(client, user.id)
    is_main_bot = client.me.id == ctx.manager.main_bot_id
    lang = ctx.L(ctx.db, user.id)

    main_text_template = ctx.db.getVars(client.me.id, "start_text_template")
    photo_id = (
        ctx.db.getVars(client.me.id, "start_photo_id")
        or "https://files.catbox.moe/ozzvtz.jpg"
    )

    if not main_text_template:
        key = "start.welcome_main_bot" if is_main_bot else "start.welcome_clone_bot"
        main_text_template = lang.get(key)
    
    welcome_text = main_text_template.format(mention=client.ns.arg.getMention(user))

    button_rows = []
    if is_main_bot:
        button_rows.append(
            f"| {lang.get('start.create_bot')} - create_bot | | {lang.get('start.my_bots')} - list_my_bots_0;same |"
        )
    if is_owner:
        button_rows.append(f"| {lang.get('start.settings_panel')} - settings |")

    button_rows.append(
        f"| {lang.get('start.list_vvip')} - list_vvip | | {lang.get('start.donate')} - donate_stars;same |"
    )
    button_rows.append(
        f"| {lang.get('start.about_bot')} - about_bot | | {lang.get('start.ai_feature')} - gemini_ai;same |"
    )
    button_rows.append(f"| {lang.get('start.language')} - set_lang |")

    btn_list_str = "\n".join(button_rows)

    btn, txt_content = client.ns.button.create_keyboard(
        f"{welcome_text}\n\n{btn_list_str}"
    )
    return btn, txt_content, photo_id


@command(lambda ctx: filters.command("start") & filters.private)
async def start_bot(client, message):
    await check_new_user(client, message)
    btn, txt, photo_id = await get_start_keyboard_and_content(client, message.from_user)
    await message.reply_photo(photo=photo_id, caption=txt, reply_markup=btn)


@command(lambda ctx: filters.regex("^start$"), handler_type="callback")
async def start_callback(client, callback_query):
    btn, txt, photo_id = await get_start_keyboard_and_content(
        client, callback_query.from_user
    )
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


@command(lambda ctx: filters.regex("^about_bot$"), handler_type="callback")
async def about_bot_callback(client, callback_query):
    lang = callback_query.lang
    
    text = (
        f"{lang.get('about.title')}\n\n"
        f"{lang.get('about.description')}\n\n"
        f"{lang.get('about.main_function_title')}\n"
        f"{lang.get('about.main_function_desc')}\n\n"
        f"{lang.get('about.workflow_title')}\n"
        f"{lang.get('about.workflow_steps')}\n\n"
        f"{lang.get('about.closing')}"
    )
    
    btn_text = f"| {lang.get('general.back')} - start |"
    btn, _ = client.ns.button.create_keyboard(f"{text}\n\n{btn_text}")

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)

@command(lambda ctx: filters.regex("^set_lang$"), handler_type="callback")
async def set_lang_callback(client, callback_query):
    lang = callback_query.lang
    btn, txt = client.ns.button.create_keyboard(
        f"{lang.get('lang.select')}\n\n"
        f"| {lang.get('lang.button_id')} - chg_lang_id |\n"
        f"| {lang.get('lang.button_en')} - chg_lang_en;same |\n"
        f"| {lang.get('general.back')} - start |"
    )
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)

@command(lambda ctx: filters.regex(r"^chg_lang_(id|en)$"), handler_type="callback")
async def change_lang_callback(client, callback_query):
    lang_code = callback_query.data.split("_")[-1]
    ctx.db.setVars(callback_query.from_user.id, "language", lang_code, var_key="user_info")
    lang = ctx.L(ctx.db, callback_query.from_user.id)
    await callback_query.answer(lang.get("lang.selected"), show_alert=True)
    await start_callback(client, callback_query)


@command(lambda ctx: filters.regex("^close_panel$"), handler_type="callback")
async def close_panel_callback(client, callback_query):
    try:
        await callback_query.message.delete()
    except Exception:
        await callback_query.answer("Selesai.")


@command(lambda ctx: filters.regex("^list_vvip$"), handler_type="callback")
async def list_vvip_bot(client, callback_query):
    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
    if not vvip_list:
        btn, txt = client.ns.button.create_keyboard(
            "🗂️ Saat ini belum ada paket VVIP yang tersedia.\n\n| • kembali • - start |"
        )
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(txt, reply_markup=btn)
        return await callback_query.edit_message_text(txt, reply_markup=btn)

    btn_text = ""
    for item in vvip_list:
        name = item.get("name", "N/A")
        promo_price = item.get("promo_price", 0)
        btn_text += f"| 📂 {name} - notes {name} |\n"
        if promo_price > 0:
            btn_text += f"| 🎉 Promo {name} - promo_detail {name};same |\n"

    btn_text += "| • kembali • - start |"
    btn, txt = client.ns.button.create_keyboard(
        f"**📚 Daftar VVIP Bot: {client.me.mention}**\n\n"
        f"Berikut adalah daftar paket eksklusif yang kami tawarkan. Klik pada salah satu paket untuk melihat detail lengkap dan penawaran spesial.\n\n{btn_text}"
    )
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


@command(lambda ctx: filters.regex("^(gemini_ai|khodam|chatbot)"), handler_type="callback")
async def gemini_bot_ai(client, callback_query):
    gemini_service = getattr(client, "services", None) and client.services.gemini
    if not gemini_service:
        if await is_bot_owner(client, callback_query.from_user.id):
            btn, txt = client.ns.button.create_keyboard(
                "**❌ AI Dinonaktifkan**\nAtur Kunci API Gemini.\n\n| • Atur Kunci API • - api_settings | | • Kembali • - start |"
            )
            if callback_query.message.photo:
                return await callback_query.edit_message_caption(txt, reply_markup=btn)
            return await callback_query.edit_message_text(txt, reply_markup=btn)
        return await callback_query.answer(
            "Maaf, fitur AI saat ini tidak tersedia.", show_alert=True
        )

    data = callback_query.data.split()
    chat_id = callback_query.from_user.id
    if data[0] == "gemini_ai":
        btn, txt = client.ns.button.create_keyboard(
            "**✨ Asisten AI Gemini**\nPilih mode interaksi.\n\n| 👻 Cek Khodam (Hiburan) - khodam | | 💬 Ngobrol dengan Asisten - chatbot;same |\n| • kembali • - start |"
        )
        if callback_query.message.photo:
            await callback_query.edit_message_caption(txt, reply_markup=btn)
        else:
            await callback_query.edit_message_text(txt, reply_markup=btn)
    elif data[0] in ("khodam", "chatbot"):
        await callback_query.edit_message_reply_markup(None)
        mode = data[0]
        try:
            if mode == "khodam":
                ask_msg = await client.ask(
                    chat_id,
                    "🔮 **Penerawangan Khodam**\nKetik **nama lengkapmu**.\n\nKetik `/batal` untuk membatalkan.",
                    timeout=300,
                )
                if ask_msg.text.lower() == "/batal":
                    raise nsdev.UserCancelled
                msg = await client.send_message(
                    chat_id, f"✨ `Menganalisis energi untuk` **{ask_msg.text}**`...`"
                )
                response_text = gemini_service.send_khodam_message(
                    ask_msg.text, chat_id
                )
                btn, _ = client.ns.button.create_keyboard(
                    "| • Coba Nama Lain • - khodam | | • Kembali ke Menu AI • - gemini_ai |"
                )
                await msg.edit(
                    f"**--- Hasil Terawangan Khodam untuk {ask_msg.text} ---**\n\n**>{response_text}",
                    reply_markup=btn,
                )
            elif mode == "chatbot":
                vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
                vvip_info_text = ""
                if vvip_list:
                    vvip_info_text += (
                        "Berikut adalah daftar paket VVIP yang tersedia saat ini:\n"
                    )
                    for item in vvip_list:
                        name = item.get("name", "N/A")
                        price = item.get("price", 0)
                        promo_price = item.get("promo_price", 0)

                        vvip_info_text += (
                            f"- Paket '{name}': Harga normal Rp {price:,}."
                        )
                        if promo_price > 0:
                            vvip_info_text += (
                                f" Saat ini sedang promo menjadi Rp {promo_price:,}."
                            )
                        vvip_info_text += "\n"
                else:
                    vvip_info_text = "Saat ini belum ada paket VVIP yang tersedia."

                about_bot_text = (
                    "Saya adalah bot asisten VVIP otomatis. "
                    "Pengguna dapat membeli akses ke grup premium melalui saya. "
                    "Alur pembelian: Pengguna memilih paket dari menu 'Lihat Daftar VVIP', "
                    "melakukan pembayaran via QRIS yang saya berikan, dan setelah pembayaran "
                    "terkonfirmasi, saya akan secara otomatis mengirimkan link undangan grup."
                )

                system_instruction = (
                    "Anda adalah asisten AI yang cerdas dan sangat membantu untuk bot Telegram ini. "
                    f"Nama bot ini adalah '{client.me.first_name}'. "
                    "Tugas Anda adalah menjawab pertanyaan pengguna yang berkaitan dengan fungsionalitas dan penawaran bot ini. "
                    "Anda HARUS menggunakan informasi di bawah ini sebagai sumber pengetahuan utama Anda.\n\n"
                    "--- INFORMASI KONTEKS BOT ---\n"
                    f"1. **Tentang Bot**: {about_bot_text}\n"
                    f"2. **Daftar Paket VVIP dan Harga**: {vvip_info_text}\n"
                    "3. **Cara Pembelian**: Pengguna harus menekan tombol 'Lihat Daftar VVIP' di menu utama untuk melihat detail paket dan memulai pembayaran.\n"
                    "4. **Lainnya**: Jika pertanyaan di luar konteks bot, jawablah secara umum dan ramah sebagai asisten AI.\n"
                    "--- AKHIR INFORMASI ---\n\n"
                    "Jawablah semua pertanyaan dengan singkat, jelas, dan dalam Bahasa Indonesia."
                )

                gemini_service.set_chatbot_instruction(system_instruction)

                await client.send_message(
                    chat_id,
                    f"💬 **Halo! Ada yang bisa saya bantu?**\nSaya asisten AI untuk bot **{client.me.first_name}**. "
                    "Anda bisa bertanya tentang cara penggunaan, harga paket VVIP, atau apa pun yang berkaitan dengan bot ini.\n\n"
                    "Ketik `/stop` untuk mengakhiri sesi obrolan.",
                )

                while True:
                    user_msg = await client.listen(chat_id, timeout=600)
                    if not user_msg.text:
                        continue
                    if user_msg.text.lower() == "/stop":
                        raise nsdev.UserCancelled

                    await client.send_chat_action(
                        chat_id, pyrogram.enums.ChatAction.TYPING
                    )

                    response_text = gemini_service.send_chat_message(
                        user_msg.text, user_id=chat_id, bot_name=client.me.first_name
                    )
                    await client.send_message(chat_id, response_text)

        except nsdev.UserCancelled:
            await client.send_message(
                chat_id,
                "✅ Sesi obrolan telah dihentikan.",
                reply_markup=client.ns.button.create_keyboard(
                    "| • Kembali ke Menu AI • - gemini_ai |"
                )[0],
            )
        except asyncio.TimeoutError:
            await client.send_message(
                chat_id,
                "⏰ Sesi berakhir karena tidak ada aktivitas.",
                reply_markup=client.ns.button.create_keyboard(
                    "| • Kembali ke Menu AI • - gemini_ai |"
                )[0],
            )
        except Exception as e:
            ctx.log.print(f"{ctx.log.RED}Error pada sesi AI Chatbot: {e}")
            await client.send_message(
                chat_id, f"Maaf, terjadi gangguan pada sistem AI.\n`Error: {e}`"
            )
        finally:
            gemini_service.reset_chatbot_instruction()


@command(lambda ctx: filters.regex("^donate_stars$"), handler_type="callback")
async def donate_callback(client, callback_query):
    photo_url = "https://files.catbox.moe/1f9j10.jpg"
    text = (
        "**❤️ Dukung Kami dengan Telegram Stars!**\n\n"
        "Donasi Anda sangat berarti untuk membantu kami terus mengembangkan dan memelihara bot ini.\n\n"
        "Setiap Star yang Anda berikan memberikan kami semangat untuk terus berinovasi. Pilih jumlah donasi di bawah ini untuk memulai.\n\n"
        "Terima kasih atas dukungan Anda!"
    )

    btn_text = (
        "| 1 ⭐ - donate_pay_1 | | 5 ⭐ - donate_pay_5;same |\n"
        "| 10 ⭐ - donate_pay_10 | | 25 ⭐ - donate_pay_25;same |\n"
        "| • Kembali • - start |"
    )

    btn, _ = client.ns.button.create_keyboard(btn_text)

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
            callback_query.from_user.id, photo=photo_url, caption=text, reply_markup=btn
        )


@command(lambda ctx: filters.regex(r"^donate_pay_(\d+)$"), handler_type="callback")
async def process_donation_callback(client, callback_query):
    lang = callback_query.lang
    try:
        star_amount = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        return await callback_query.answer(
            lang.get("payment.donation.invalid_amount"), show_alert=True
        )

    await callback_query.answer(lang.get("payment.donation.preparing"))

    invoice = {
        "title": "Donasi untuk Pengembangan Bot",
        "description": f"Dukungan Anda sebesar {star_amount} Bintang (Stars) sangat kami hargai. Terima kasih!",
        "payload": f"donation_{star_amount}_{callback_query.from_user.id}_{int(time())}",
        "currency": "XTR",
        "prices": [
            pyrogram.types.LabeledPrice(f"Donasi {star_amount} Stars", star_amount)
        ],
    }

    try:
        await client.send_invoice(callback_query.from_user.id, **invoice)
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal mengirim invoice Stars: {e}")
        await callback_query.answer(
            lang.get("payment.donation.invoice_fail"), show_alert=True
        )
