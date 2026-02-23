from . import *

def generate_safe_saweria_message(user_name):
    sapaan_pembuka = [
        "Halo", "Hi", "Hello", "Hoi", "Woi", "Uy", "P", "Ping", "Tes", "Cek",
        "Spada", "Punten", "Permisi", "Kulonuwun", "Sampurasun", "Horas",
        "Assalamualaikum", "Salam", "Greetings", "Hola", "Aloha", "Bonjour",
        "Pagi", "Siang", "Sore", "Malam", "Met pagi", "Met siang", "Met malam",
        "Oy", "Euy", "Misi", "Paket", "Shalom", "Om swastiastu", "Wilujeng",
        "Sugeng", "Tabik", "Hehe", "Wkwk", "Yoo", "Hellow", "Alow", "Lapor",
        "Izin", "Numpang", "Excuse me", "Konbanwa", "Ohayo", "Moshi moshi"
    ]

    panggilan_akrab = [
        "Bang", "Mas", "Kak", "Min", "Om", "Pak", "Bu", "Sis", "Gan", "Agan",
        "Bro", "Bray", "Cuy", "Sob", "Sobat", "Kawan", "Teman", "Lur", "Dulur",
        "Ndang", "Ngab", "Pack", "Mank", "Bestie", "Suhu", "Sepuh", "Mastah",
        "Idola", "Panutan", "Legend", "Boss", "Bosque", "Juragan", "Sultan",
        "Nder", "Bre", "Bli", "Uda", "Cici", "Koko", "Abang", "Akang", "Aa",
        "Teteh", "Mbak", "Neng", "Uni", "Mamank", "Admin", "Mimin", "Momod",
        "Lord", "King", "Queen", "Paman", "Bibi", "Datuk", "Sensei", "Senpai",
        "Coach", "Kapten", "Komandan", "Chief", "Head", "Leader", "Master"
    ]

    kata_kerja_memberi = [
        "Traktir", "Ngasih", "Kirim", "Bagi", "Support", "Dukung", "Nyawer",
        "Titip", "Sumbang", "Share", "Gift", "Tanda mata", "Apresiasi",
        "Buat", "Untuk", "Kasih", "Sedekah", "Jajanin", "Nambahin", "Bantu",
        "Donasi", "Cemplungin", "Lempar", "Sisihin", "Nyalurin", "Topup",
        "Isi", "Suntik", "Ngedukung", "Nyumbang", "Nraktir", "Sawer",
        "Cendolin", "Ngegift", "Drop", "Transfer energi", "Nitip", "Nambah",
        "Nyisihin", "Sedekahin", "Infaq", "Sodaqoh", "Berbagi", "Menyapa",
        "Mampir", "Lewat", "Setor", "Deposit", "Simpan", "Tabung", "Invest"
    ]

    objek_gabungan = [
        "kopi", "kopi hitam", "kopi susu", "teh manis", "es teh", "boba",
        "gorengan", "bakwan", "tahu isi", "seblak", "nasgor", "mie ayam",
        "bakso", "sate", "martabak", "terang bulan", "cemilan", "kerupuk",
        "cilok", "cimol", "batagor", "siomay", "roti bakar", "pisang goreng",
        "indomie", "soto", "rawon", "jus", "susu", "air putih", "mineral",
        "cireng", "lumpia", "risol", "kue", "donat", "pizza", "burger",
        "ayam geprek", "pecel lele", "nasi padang", "ketoprak", "gado gado",
        "uang rokok", "bensin", "kuota", "pulsa", "listrik", "token",
        "jajan", "dana", "saldo", "modal", "amunisi", "energi", "gizi",
        "vitamin", "suplemen", "uang kaget", "receh", "kembalian", "sangu",
        "thr", "angpao", "uang jajan", "kas", "tabungan", "celengan",
        "uang kopi", "uang bensin", "uang makan", "uang saku", "nafkah",
        "uang parkir", "uang kas", "uang keamanan", "uang lelah", "tip",
        "kopi kenangan", "janji jiwa", "starbucks", "mixue", "chatime",
        "es krim", "coklat", "permen", "kuaci", "kacang", "rokok sebatang",
        "surya", "sampoerna", "magnum", "garam", "gula", "beras", "sembako",
        "takjil", "bukaan", "sahur", "makan siang", "makan malam", "sarapan",
        "mie instan", "telur", "minyak", "sabun", "odol", "shampoo", "paket",
        "bingkisan", "kado", "hadiah", "oleh oleh", "buah tangan", "souvenir"
    ]

    kata_sifat_doa = [
        "semangat", "sukses", "sehat", "lancar", "berkah", "mantap", "keren",
        "gacor", "menyala", "lanjutkan", "konsisten", "bahagia", "jos", "top",
        "gokil", "cool", "nice", "good luck", "best", "terbaik", "juara",
        "legend", "panutan", "idola", "produktif", "kreatif", "maju", "jaya",
        "abadi", "gandoss", "markotop", "savage", "gg", "ggwp", "op", "hoki",
        "cuan", "profit", "stonks", "sejahtera", "sentosa", "damai", "awet",
        "langgeng", "barokah", "manjur", "paten", "yahud", "asik", "seru",
        "rame", "laris", "manis", "berlimpah", "kaya", "makmur", "santuy",
        "kalem", "rileks", "fokus", "rajin", "tekun", "giat", "hebat", "kuat",
        "tangguh", "sabar", "ikhlas", "tawakal", "istiqomah", "bersyukur"
    ]

    ucapan_terima_kasih = [
        "makasih", "terima kasih", "thanks", "thx", "tq", "suwun", "hatur nuhun",
        "sakalangkong", "maacih", "tengkyu", "arigato", "thank you", "big thanks",
        "cheers", "peace", "salim", "sungkem", "thank u", "ty", "kamsia",
        "xie xie", "gracias", "danke", "matur nuwun", "tararengkyu", "sankyu",
        "syukron", "jazakallah", "thankies", "tysm", "nuwun", "aman", "siap",
        "oke", "sip", "yoi", "mantul", "ashiap", "woke", "ok", "kamsahamnida"
    ]

    partikel_pelengkap = [
        "ya", "nih", "tuh", "dong", "banget", "terus", "selalu", "dikit",
        "lumayan", "buat", "biar", "agar", "supaya", "saja", "aja", "doang",
        "cuma", "hanya", "sekadar", "ala kadarnya", "seikhlasnya", "kecil kecilan",
        "tipis tipis", "iseng", "gabut", "daripada luang", "sambil lewat",
        "mah", "teh", "rek", "cok", "gan", "lur", "bos", "lah", "kah", "deh",
        "kok", "kan", "yuk", "kuy", "skuy", "gas", "gaskeun", "sikat", "atuh",
        "euy", "sih", "pun", "juga", "lagi", "mulu", "kali", "tah", "leh"
    ]

    emojis_list = [
        "☕", "🍵", "🥤", "🧋", "🍱", "🍜", "🍝", "🍟", "🍕", "🌭", "🥪", "🌮", "🌯",
        "🍩", "🍪", "🎂", "🍰", "🧁", "🍫", "🍬", "🍭", "🍮", "🍯", "🍼", "🥛",
        "🚀", "🔥", "✨", "⭐", "🌟", "💫", "💥", "💯", "💢", "💤", "💨", "💦",
        "🙏", "👍", "👌", "✌️", "🤞", "🤟", "🤘", "🤙", "👋", "👏", "🙌", "👐",
        "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❣️", "💕",
        "😎", "🤩", "🥳", "🤗", "🤔", "🫡", "🫠", "🥹", "😊", "😇", "🙂", "🙃",
        "💸", "💵", "💴", "💶", "💷", "💰", "💳", "💎", "⚖️", "🧱", "🔧", "🔨",
        "🎉", "🎊", "🎈", "🎁", "🎀", "🧧", "🏮", "🍀", "🍄", "💐", "🌸", "🌹",
        "🌚", "🌝", "🌞", "🧊", "🧂", "🍿", "🥓", "🥩", "🍗", "🍖", "🧀", "🥞",
        "🍇", "🍈", "🍉", "🍊", "🍋", "🍌", "🍍", "🥭", "🍎", "🍏", "🍐", "🍑"
    ]

    pola_kalimat = random.randint(1, 10)
    parts = []

    if pola_kalimat == 1:
        parts.append(random.choice(kata_kerja_memberi))
        parts.append(random.choice(objek_gabungan))
        parts.append(random.choice(panggilan_akrab))
    elif pola_kalimat == 2:
        parts.append(random.choice(sapaan_pembuka))
        parts.append(random.choice(kata_kerja_memberi))
        parts.append(random.choice(objek_gabungan))
        parts.append(random.choice(partikel_pelengkap))
    elif pola_kalimat == 3:
        parts.append(random.choice(kata_sifat_doa))
        parts.append(random.choice(partikel_pelengkap))
        parts.append(random.choice(panggilan_akrab))
        parts.append(user_name)
    elif pola_kalimat == 4:
        parts.append(random.choice(kata_kerja_memberi))
        parts.append(random.choice(objek_gabungan))
        parts.append(random.choice(ucapan_terima_kasih))
    elif pola_kalimat == 5:
        parts.append(random.choice(sapaan_pembuka))
        parts.append(random.choice(objek_gabungan))
        parts.append(random.choice(kata_kerja_memberi))
        parts.append(user_name)
    elif pola_kalimat == 6:
        parts.append(random.choice(kata_kerja_memberi))
        parts.append(random.choice(kata_sifat_doa))
        parts.append(random.choice(emojis_list))
    elif pola_kalimat == 7:
        parts.append(random.choice(partikel_pelengkap))
        parts.append(random.choice(ucapan_terima_kasih))
        parts.append(random.choice(panggilan_akrab))
    elif pola_kalimat == 8:
        parts.append(random.choice(panggilan_akrab))
        parts.append(random.choice(ucapan_terima_kasih))
        parts.append(random.choice(kata_sifat_doa))
    elif pola_kalimat == 9:
        parts.append(random.choice(objek_gabungan))
        parts.append(random.choice(objek_gabungan))
        parts.append(random.choice(panggilan_akrab))
    else:
        parts.append(random.choice(kata_kerja_memberi))
        parts.append(random.choice(objek_gabungan))
        parts.append(random.choice(emojis_list))

    if random.random() > 0.3:
        parts.append(random.choice(emojis_list))
    
    if random.random() > 0.6:
        parts.insert(0, random.choice(emojis_list))

    final_message = " ".join(parts)

    casing_style = random.randint(1, 5)
    if casing_style == 1:
        final_message = final_message.lower()
    elif casing_style == 2:
        final_message = final_message.capitalize()
    elif casing_style == 3:
        final_message = final_message.title()
    elif casing_style == 4:
        final_message = final_message.upper()

    unique_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(4, 6)))
    
    return f"{final_message} ({unique_code})"


async def verify_user_join(client, user, chat_id, link_msg):
    lang = await ctx.L.create(ctx.db, user.id)
    verification_timeout = 3600
    start_time = time()
    is_joined = False

    while time() - start_time < verification_timeout:
        try:
            member = await client.get_chat_member(chat_id, user.id)
            if member.status not in [pyrogram.enums.ChatMemberStatus.LEFT, pyrogram.enums.ChatMemberStatus.BANNED]:
                is_joined = True
                ctx.log.print(f"{ctx.log.GREEN}User {user.id} berhasil diverifikasi bergabung ke {chat_id} dari bot {client.me.username}.")
                break
        except pyrogram.errors.UserNotParticipant:
            await asyncio.sleep(15)
        except Exception as e:
            ctx.log.print(f"{ctx.log.RED}Error saat verifikasi join {user.id} ke {chat_id}: {e}")
            break

    try:
        await link_msg.delete()
    except Exception:
        pass

    if not is_joined:
        ctx.log.print(f"{ctx.log.YELLOW}User {user.id} tidak bergabung ke {chat_id} dalam waktu yang ditentukan.")
        await client.send_message(user.id, lang.get("payment.check.link_expired"))


async def verify_user_join_multiple(client, user, invite_payloads, link_msg):
    lang = await ctx.L.create(ctx.db, user.id)
    verification_timeout = 3600
    start_time = time()

    while time() - start_time < verification_timeout:
        pending_payloads = []
        for payload in invite_payloads:
            chat_id = payload.get("chat_id")
            try:
                member = await client.get_chat_member(chat_id, user.id)
                if member.status in [pyrogram.enums.ChatMemberStatus.LEFT, pyrogram.enums.ChatMemberStatus.BANNED]:
                    pending_payloads.append(payload)
            except pyrogram.errors.UserNotParticipant:
                pending_payloads.append(payload)
            except Exception as e:
                ctx.log.print(f"{ctx.log.RED}Error saat verifikasi multi join {user.id} ke {chat_id}: {e}")
                pending_payloads.append(payload)

        if not pending_payloads:
            try:
                await link_msg.delete()
            except Exception:
                pass
            ctx.log.print(f"{ctx.log.GREEN}User {user.id} berhasil bergabung ke semua paket VVIP dari bot {client.me.username}.")
            return

        await asyncio.sleep(15)

    pending_lines = []
    for item in pending_payloads:
        pending_lines.append(f"• {item.get('name')}: {item.get('link')}")

    try:
        await client.send_message(
            user.id,
            lang.get("payment.check.pending_join_multi", pending_links="\n".join(pending_lines)),
            protect_content=True,
        )
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal mengirim notifikasi pending join multi {user.id}: {e}")


def _get_all_vvip_items(vvip_list):
    selected_items = []
    for index, item in enumerate(vvip_list):
        price = int(item.get("price", 0) or 0)
        chat_id_normal = item.get("chat_id_normal")
        if price > 0 and chat_id_normal:
            selected_items.append(
                {
                    "index": index,
                    "name": item.get("name", f"Paket {index + 1}"),
                    "price": price,
                    "chat_id": chat_id_normal,
                    "duration": item.get("duration", 0),
                }
            )
    return selected_items


async def _create_payment_invoice(client, user, item_index, tipe, amount, coupon_code=None):
    lang = await ctx.L.create(ctx.db, user.id)

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    try:
        item = vvip_list[item_index]
        names = item.get("name")
    except IndexError:
        return await client.send_message(user.id, lang.get("payment.notes.not_found"))

    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = lang.get("payment.pay.service_inactive_panel")
            layout = [[{"text": lang.get("payment.pay.setup_api_button"), "callback_data": "api_settings"}]]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(user.id, text, reply_markup=btn)
        else:
            await client.send_message(user.id, lang.get("payment.pay.service_inactive_alert"))
        return

    msg = await client.send_message(user.id, lang.get("general.processing"))

    try:
        fakeinfo = client.ns.utils.faker.generate()

        random_message = generate_safe_saweria_message(
            user_name=user.first_name or "User"
        )

        qr_string, transaction_id, qr_image_stream, amount_raw = await client.services.saweria.create_payment(
            user_id=saweria_user_id,
            amount=int(amount),
            name=user.first_name or "User",
            email=fakeinfo.email,
            message=random_message,
            creator_name=client.me.username,
        )

        order_data = f"{item_index}|{tipe}|{amount_raw}"
        if coupon_code:
            order_data += f"|{coupon_code}"

        await ctx.db.setVars(client.me.id, transaction_id, order_data)

        caption = lang.get(
            "payment.pay.invoice_full",
            name=names,
            type=tipe.title(),
            amount=f"{int(amount_raw):,}",
            id=f"[{transaction_id}](https://saweria.co/qris/{transaction_id})",
        )
        layout = [
            [{"text": lang.get("payment.check.confirm_button"), "callback_data": f"confirm_payment {transaction_id}"}]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await client.send_photo(user.id, photo=qr_image_stream, caption=caption, reply_markup=btn)
        await msg.delete()
        ctx.log.print(f"{ctx.log.CYAN}User {user.id} membuat pembayaran untuk {names} dari bot {client.me.username}.")
    except Exception as e:
        await msg.edit(lang.get("general.error", e=e))


async def _create_all_vvip_payment_invoice(client, user, selected_items, total_amount):
    lang = await ctx.L.create(ctx.db, user.id)
    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = lang.get("payment.pay.service_inactive_panel")
            layout = [[{"text": lang.get("payment.pay.setup_api_button"), "callback_data": "api_settings"}]]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(user.id, text, reply_markup=btn)
        else:
            await client.send_message(user.id, lang.get("payment.pay.service_inactive_alert"))
        return

    msg = await client.send_message(user.id, lang.get("general.processing"))

    try:
        fakeinfo = client.ns.utils.faker.generate()
        random_message = generate_safe_saweria_message(user_name=user.first_name or "User")
        qr_string, transaction_id, qr_image_stream, amount_raw = await client.services.saweria.create_payment(
            user_id=saweria_user_id,
            amount=int(total_amount),
            name=user.first_name or "User",
            email=fakeinfo.email,
            message=random_message,
            creator_name=client.me.username,
        )

        package_indexes = ",".join(str(item.get("index")) for item in selected_items)
        order_data = f"ALL|normal|{int(amount_raw)}|{package_indexes}"
        await ctx.db.setVars(client.me.id, transaction_id, order_data)

        package_names = ", ".join(item.get("name") for item in selected_items)
        caption = lang.get(
            "payment.pay.invoice_full",
            name=lang.get("payment.pay.all_vvip_product_name", total=len(selected_items), names=package_names),
            type="Bundle",
            amount=f"{int(amount_raw):,}",
            id=f"[{transaction_id}](https://saweria.co/qris/{transaction_id})",
        )
        layout = [
            [{"text": lang.get("payment.check.confirm_button"), "callback_data": f"confirm_payment {transaction_id}"}]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await client.send_photo(user.id, photo=qr_image_stream, caption=caption, reply_markup=btn)
        await msg.delete()
        ctx.log.print(
            f"{ctx.log.CYAN}User {user.id} membuat pembayaran bundling semua VVIP ({len(selected_items)} paket) dari bot {client.me.username}."
        )
    except Exception as e:
        await msg.edit(lang.get("general.error", e=e))


@command(lambda ctx: filters.regex(r"^confirm_payment\s(.+)"), handler_type="callback")
async def manual_check_payment_callback(client, callback_query):
    transaction_id = callback_query.data.split(" ", 1)[1]
    user = callback_query.from_user
    lang = callback_query.lang

    ref_data_str = await ctx.db.getVars(client.me.id, transaction_id)
    if not ref_data_str:
        return await callback_query.edit_message_caption(lang.get("payment.check.expired_or_completed"))

    ref_parts = ref_data_str.split("|")
    is_bundle_order = ref_parts[0] == "ALL"
    tipe = ref_parts[1]
    amount_raw = int(ref_parts[2])

    coupon_code = None
    bundle_indexes = []
    if is_bundle_order:
        bundle_indexes = [int(i) for i in ref_parts[3].split(",") if i.strip().isdigit()] if len(ref_parts) > 3 else []
    else:
        item_index = int(ref_parts[0])
        coupon_code = ref_parts[3] if len(ref_parts) > 3 else None

    try:
        is_paid = await client.services.saweria.check_paid_status(transaction_id)

        if is_paid:
            await callback_query.edit_message_reply_markup(None)
            await ctx.db.removeVars(client.me.id, transaction_id)

            vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

            if is_bundle_order:
                invite_payloads = []
                purchased_names = []
                for idx in bundle_indexes:
                    try:
                        item_found = vvip_list[idx]
                    except IndexError:
                        continue

                    name = item_found.get("name")
                    target_chat_id = item_found.get("chat_id_normal")
                    if not target_chat_id:
                        continue

                    try:
                        expire_date_link = datetime.now() + timedelta(minutes=60)
                        invite_link_obj = await client.create_chat_invite_link(
                            chat_id=target_chat_id, member_limit=1, expire_date=expire_date_link
                        )
                        link = invite_link_obj.invite_link
                    except Exception as e:
                        ctx.log.print(f"{ctx.log.RED}Gagal membuat invite link bundle untuk {target_chat_id}: {e}")
                        continue

                    member_data = {
                        "user_id": user.id,
                        "vvip_name": name,
                        "join_date": datetime.now(timezone.utc).isoformat(),
                        "payment_type": "normal",
                        "chat_id_kick": target_chat_id,
                    }
                    duration = item_found.get("duration", 0)
                    if duration > 0:
                        expiry_date = datetime.now(timezone.utc) + timedelta(days=duration)
                        member_data["expiry_date"] = expiry_date.isoformat()
                    await ctx.db.setListVars(client.me.id, "vvip_members", member_data)

                    purchased_names.append(name)
                    invite_payloads.append({"name": name, "chat_id": target_chat_id, "link": link})

                if not invite_payloads:
                    raise ValueError(lang.get("payment.check.bundle_empty_or_invalid"))

                revenue_data = {
                    "user_id": user.id,
                    "username": user.username or user.first_name,
                    "amount": amount_raw,
                    "date": datetime.now(timezone.utc).isoformat(),
                    "item_name": " + ".join(purchased_names),
                    "type": "bundle",
                }
                await ctx.db.setListVars(client.me.id, "vip_revenue_history", revenue_data)

                link_text = "\n".join([f"• {item.get('name')}: {item.get('link')}" for item in invite_payloads])
                link_msg = await client.send_message(
                    user.id,
                    lang.get("payment.check.success_customer_bundle", links=link_text),
                    protect_content=True,
                )
                await callback_query.message.delete()
                asyncio.create_task(verify_user_join_multiple(client, user, invite_payloads, link_msg))

                owner_bot_id = await ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id
                owner_lang = await ctx.L.create(ctx.db, owner_bot_id)
                await client.send_message(
                    owner_bot_id,
                    owner_lang.get(
                        "payment.check.success_owner_notif",
                        mention=client.ns.telegram.arg.getMention(user),
                        bot_mention=client.me.mention,
                        name=lang.get("payment.check.all_vvip_label"),
                        type="Bundle",
                    ),
                )
                ctx.log.print(
                    f"{ctx.log.CYAN}User {user.id} telah mengkonfirmasi pembayaran bundle semua VVIP dari bot {client.me.username}."
                )
                return

            try:
                item_found = vvip_list[item_index]
                name = item_found.get("name")
            except IndexError:
                raise ValueError(lang.get("payment.check.category_missing", name=f"index {item_index}"))

            is_promo = tipe == "promo"
            target_chat_id = item_found.get("chat_id_promo") if is_promo else item_found.get("chat_id_normal")

            if not target_chat_id:
                raise ValueError("Chat ID untuk paket VVIP ini belum diatur oleh admin.")

            try:
                expire_date_link = datetime.now() + timedelta(minutes=60)
                invite_link_obj = await client.create_chat_invite_link(
                    chat_id=target_chat_id, member_limit=1, expire_date=expire_date_link
                )
                link = invite_link_obj.invite_link
            except Exception as e:
                ctx.log.print(f"{ctx.log.RED}Gagal membuat invite link untuk {target_chat_id}: {e}")
                raise Exception(
                    "Gagal membuat link undangan. Pastikan bot adalah admin di grup tujuan dengan hak 'Invite Users'."
                )

            member_data = {
                "user_id": user.id,
                "vvip_name": name,
                "join_date": datetime.now(timezone.utc).isoformat(),
                "payment_type": tipe,
                "chat_id_kick": target_chat_id,
            }

            duration = item_found.get("duration", 0)
            if duration > 0:
                expiry_date = datetime.now(timezone.utc) + timedelta(days=duration)
                member_data["expiry_date"] = expiry_date.isoformat()

            if coupon_code:
                coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
                for c in coupons:
                    if c.get("code") == coupon_code:
                        c["uses_left"] = c.get("uses_left", 1) - 1
                        break
                await ctx.db.removeVars(client.me.id, "coupons")
                for c in coupons:
                    await ctx.db.setListVars(client.me.id, "coupons", c)

            await ctx.db.setListVars(client.me.id, "vvip_members", member_data)

            revenue_data = {
                "user_id": user.id,
                "username": user.username or user.first_name,
                "amount": amount_raw,
                "date": datetime.now(timezone.utc).isoformat(),
                "item_name": name,
                "type": tipe
            }
            await ctx.db.setListVars(client.me.id, "vip_revenue_history", revenue_data)

            link_msg = await client.send_message(
                user.id,
                lang.get("payment.check.success_customer_full", name=name, link=link),
                protect_content=True,
            )
            await callback_query.message.delete()
            asyncio.create_task(verify_user_join(client, user, target_chat_id, link_msg))

            owner_bot_id = await ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id
            owner_lang = await ctx.L.create(ctx.db, owner_bot_id)
            await client.send_message(
                owner_bot_id,
                owner_lang.get(
                    "payment.check.success_owner_notif",
                    mention=client.ns.telegram.arg.getMention(user),
                    bot_mention=client.me.mention,
                    name=name,
                    type=tipe.title(),
                ),
            )
            ctx.log.print(f"{ctx.log.CYAN}User {user.id} telah mengkonfirmasi pembayaran {name} dari bot {client.me.username}.")
        else:
            await callback_query.answer(lang.get("payment.check.not_paid"), show_alert=True)

    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Error manual-check {user.id} ({client.me.username}) {transaction_id}: {e}")
        await callback_query.answer(lang.get("general.error", e=e), show_alert=True)


@command(lambda ctx: filters.regex(r"^pay_all_vvip$"), handler_type="callback")
async def pay_all_vvip_callback(client, callback_query):
    lang = callback_query.lang
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    selected_items = _get_all_vvip_items(vvip_list)

    if not selected_items:
        return await callback_query.answer(lang.get("payment.check.bundle_empty_or_invalid"), show_alert=True)

    total_amount = sum(item.get("price", 0) for item in selected_items)

    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text(lang.get("general.processing"))

    await _create_all_vvip_payment_invoice(client, callback_query.from_user, selected_items, total_amount)

@command(lambda ctx: filters.regex(r"^notes_(\d+)"), handler_type="callback")
async def notes_data(client, callback_query):
    lang = callback_query.lang
    item_index = int(callback_query.matches[0].group(1))
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

    layout = [[{"text": lang.get("general.back_to_vvip_list"), "callback_data": "list_vvip"}]]

    try:
        item = vvip_list[item_index]
    except IndexError:
        item = None

    if item:
        name = item.get("name")
        price_val = item.get("price", 0)
        normal_text = item.get("normal_text", "")

        desc = (
            normal_text.format(name=name, price=f"{price_val:,}")
            if normal_text
            else lang.get("payment.defaults.notes_text", name=name, price=f"{price_val:,}")
        )

        layout = [
            [
                {
                    "text": lang.get("payment.notes.pay_button"),
                    "callback_data": f"paynow_{item_index}_normal_{price_val}",
                }
            ],
            [
                {
                    "text": lang.get("coupons.use_button"),
                    "callback_data": f"apply_coupon_{item_index}_normal_{price_val}",
                },
                {"text": lang.get("general.back_to_vvip_list"), "callback_data": "list_vvip"},
            ],
        ]

        btn = client.ns.telegram.button.build_button_grid(layout)

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(desc, reply_markup=btn)
        return await callback_query.edit_message_text(desc, reply_markup=btn)

    text = lang.get("payment.notes.not_found")
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^promo_detail_(\d+)"), handler_type="callback")
async def promo_detail(client, callback_query):
    lang = callback_query.lang
    item_index = int(callback_query.matches[0].group(1))
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

    layout = [[{"text": lang.get("general.back_to_vvip_list"), "callback_data": "list_vvip"}]]

    try:
        item = vvip_list[item_index]
    except IndexError:
        item = None

    if item and item.get("promo_price", 0) > 0:
        name = item.get("name")
        promo_price_val = item.get("promo_price", 0)
        promo_text = item.get("promo_text", "")

        desc = (
            promo_text.format(name=name, promo_price=f"{promo_price_val:,}")
            if promo_text
            else lang.get("payment.defaults.promo_text", name=name, promo_price=f"{promo_price_val:,}")
        )

        layout = [
            [
                {
                    "text": lang.get("payment.promo.pay_button"),
                    "callback_data": f"paynow_{item_index}_promo_{promo_price_val}",
                }
            ],
            [
                {
                    "text": lang.get("coupons.use_button"),
                    "callback_data": f"apply_coupon_{item_index}_promo_{promo_price_val}",
                },
                {"text": lang.get("general.back_to_vvip_list"), "callback_data": "list_vvip"},
            ],
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(desc, reply_markup=btn)
        return await callback_query.edit_message_text(desc, reply_markup=btn)

    text = lang.get("payment.promo.not_found")
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^apply_coupon_(\d+)_(normal|promo)_(\d+)"), handler_type="callback")
async def apply_coupon_callback(client, callback_query):
    lang = callback_query.lang
    chat_id = callback_query.from_user.id

    match = callback_query.matches[0]
    item_index = int(match.group(1))
    tipe = match.group(2)
    original_amount = int(match.group(3))

    await callback_query.message.delete()

    try:
        ask_msg = await client.ask(chat_id, lang.get("coupons.prompt"), timeout=300)
        if ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        coupon_code = ask_msg.text.upper()
        coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
        coupon = next((c for c in coupons if c.get("code") == coupon_code), None)

        if not coupon:
            raise ValueError(lang.get("coupons.invalid"))

        if coupon.get("uses_left", 1) <= 0:
            raise ValueError(lang.get("coupons.limit_reached"))

        expiry_str = coupon.get("expiry_date")
        if expiry_str and datetime.fromisoformat(expiry_str) < datetime.now(timezone.utc):
            raise ValueError(lang.get("coupons.expired"))

        discount_type = coupon["discount_type"]
        discount_value = coupon["discount_value"]

        if discount_type == "percentage":
            final_amount = original_amount - (original_amount * (discount_value / 100))
        else:
            final_amount = original_amount - discount_value

        final_amount = max(1000, int(final_amount))

        await client.send_message(
            chat_id,
            lang.get(
                "coupons.success_applied", code=coupon_code, original=f"{original_amount:,}", final=f"{final_amount:,}"
            ),
        )

        await _create_payment_invoice(client, callback_query.from_user, item_index, tipe, final_amount, coupon_code)

    except listen.UserCancelled:
        await client.send_message(chat_id, lang.get("general.cancelled"))
    except asyncio.TimeoutError:
        await client.send_message(chat_id, lang.get("general.timeout"))
    except ValueError as e:
        await client.send_message(chat_id, str(e))
    except Exception as e:
        await client.send_message(chat_id, lang.get("general.error", e=e))


@command(lambda ctx: filters.regex(r"^paynow_(\d+)_(normal|promo)_(\d+)"), handler_type="callback")
async def paynow(client, callback_query):
    match = callback_query.matches[0]
    item_index = int(match.group(1))
    tipe = match.group(2)
    amount = int(match.group(3))

    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text(callback_query.lang.get("general.processing"))

    await _create_payment_invoice(client, callback_query.from_user, item_index, tipe, amount)


@command(lambda ctx: filters.PreCheckoutQuery, handler_type="pre_checkout")
async def pre_checkout_handler(client, pre_checkout_query):
    await pre_checkout_query.answer(ok=True)


@command(lambda ctx: filters.successful_payment)
async def successful_donation_handler(client, message):
    if not message.successful_payment.invoice_payload.startswith("donation_"):
        return

    user = message.from_user
    lang = message.lang
    stars_donated = message.successful_payment.total_amount
    charge_id = message.successful_payment.telegram_payment_charge_id
    current_bot_id = client.me.id
    super_admin_id = ctx.owner_id

    await client.send_message(
        chat_id=user.id,
        text=lang.get("payment.donation.success_msg", name=user.first_name, stars=stars_donated),
    )

    owner_of_this_bot = await ctx.db.getVars(current_bot_id, "owner_id") or super_admin_id
    owner_lang = await ctx.L.create(ctx.db, owner_of_this_bot)

    main_bot_client = ctx.manager.main_bot_client

    try:
        notification_text = owner_lang.get(
            "payment.donation.owner_notif",
            stars=stars_donated,
            mention=client.ns.telegram.arg.getMention(user),
            id=user.id,
            bot_mention=client.me.mention,
        )

        refund_key = uuid.uuid4().hex[:16]
        refund_data = {"user_id": user.id, "charge_id": charge_id}
        await ctx.db.setVars(current_bot_id, f"refund_{refund_key}", refund_data)

        refund_callback_data = f"refund_stars_{refund_key}"
        layout = [[{"text": owner_lang.get("payment.donation.refund_button"), "callback_data": refund_callback_data}]]
        refund_btn = client.ns.telegram.button.build_button_grid(layout)

        await client.send_message(chat_id=owner_of_this_bot, text=notification_text, reply_markup=refund_btn)

    except pyrogram.errors.UserIsBlocked:
        ctx.log.warning(f"Gagal kirim notif donasi, Owner {owner_of_this_bot} memblokir bot {current_bot_id}")
        if main_bot_client and owner_of_this_bot != super_admin_id:
            super_admin_lang = await ctx.L.create(ctx.db, super_admin_id)
            await main_bot_client.send_message(
                super_admin_id,
                super_admin_lang.get(
                    "payment.donation.owner_blocked_notif",
                    stars=stars_donated,
                    mention=client.ns.telegram.arg.getMention(user),
                    bot_name=client.me.first_name,
                ),
            )
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal mengirim notifikasi donasi: {e}")

    ctx.log.print(
        f"{ctx.log.GREEN}Donasi {stars_donated} XTR diterima dari {user.id} ({user.first_name}) melalui bot {current_bot_id}"
    )


@command(lambda ctx: filters.regex(r"^renew_sub_(\d+)"), handler_type="callback")
async def renew_subscription_callback(client, callback_query):
    lang = callback_query.lang
    item_index = int(callback_query.matches[0].group(1))

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    try:
        item = vvip_list[item_index]
    except IndexError:
        return await callback_query.answer(lang.get("payment.notes.not_found"), show_alert=True)

    if item.get("promo_price", 0) > 0:
        callback_query.data = f"promo_detail_{item_index}"
        callback_query.matches = [re.match(r"promo_detail_(\d+)", callback_query.data)]
        await promo_detail(client, callback_query)
    else:
        callback_query.data = f"notes_{item_index}"
        callback_query.matches = [re.match(r"notes_(\d+)", callback_query.data)]
        await notes_data(client, callback_query)
