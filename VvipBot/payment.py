from . import *

def generate_safe_saweria_message(user_name):
    greetings = [
        "Halo", "Hi", "Pagi", "Siang", "Sore", "Malam", "Uy", 
        "Woi", "Ping", "Tes", "Cek", "Hello", "Hey", "Yo", "Misi"
    ]
    
    intents = [
        "Support", "Dukungan", "Traktir", "Buat", "Kasih", "Titip", 
        "Share", "Gift", "Kirim", "Ngasih", "Bantu", "Sumbang",
        "Tanda mata", "Apresiasi", "Sawer tipis", "Uang"
    ]
    
    objects = [
        "kopi", "cendol", "gorengan", "jajan", "rokok", "teh", 
        "susu", "energi", "bensin", "kuota", "cemilan", "nasgor",
        "bakso", "mie ayam", "es teh", "dana", "saldo", "kue"
    ]
    
    closers = [
        "makasih", "thanks", "thx", "tq", "suwun", "mantap", 
        "sukses", "sehat selalu", "lanjutkan", "keren", "semangat",
        "berkah", "good luck", "nice", "jos", "gass", "lanjut"
    ]
    
    emojis = [
        "☕", "🍵", "🍪", "🍕", "🍔", "🍟", "🌭", "🍿", "🍩",
        "🙏", "👍", "👌", "💪", "🔥", "✨", "❤️", "😎", "🤩",
        "🥳", "🤗", "🙌", "👏", "🤝", "🌟", "💫", "🍀"
    ]

    structure = random.randint(1, 5)
    parts = []
    
    if structure == 1:
        parts = [random.choice(intents), random.choice(objects), "bang"]
    elif structure == 2:
        parts = [random.choice(greetings), random.choice(intents), "ya"]
    elif structure == 3:
        parts = [random.choice(intents), random.choice(objects), random.choice(closers)]
    elif structure == 4:
        parts = [random.choice(intents), "terus", user_name]
    else:
        parts = ["Iseng", "aja", random.choice(closers)]

    if random.random() > 0.3:
        parts.append(random.choice(emojis))

    unique_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    parts.append(f"({unique_code})")

    return " ".join(parts)

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


@command(lambda ctx: filters.regex(r"^confirm_payment\s(.+)"), handler_type="callback")
async def manual_check_payment_callback(client, callback_query):
    transaction_id = callback_query.data.split(" ", 1)[1]
    user = callback_query.from_user
    lang = callback_query.lang

    ref_data_str = await ctx.db.getVars(client.me.id, transaction_id)
    if not ref_data_str:
        return await callback_query.edit_message_caption(lang.get("payment.check.expired_or_completed"))

    ref_parts = ref_data_str.split("|")
    item_index = int(ref_parts[0])
    tipe = ref_parts[1]
    amount_raw = int(ref_parts[2])
    coupon_code = ref_parts[3] if len(ref_parts) > 3 else None

    try:
        is_paid = await client.services.saweria.check_paid_status(transaction_id)

        if is_paid:
            await callback_query.edit_message_reply_markup(None)
            await ctx.db.removeVars(client.me.id, transaction_id)

            vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
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
