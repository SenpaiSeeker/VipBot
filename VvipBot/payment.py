import base64

from . import *


async def verify_user_join(client, user, chat_id, link_msg):
    lang = ctx.L(ctx.db, user.id)
    verification_timeout = 600
    start_time = time()
    is_joined = False

    while time() - start_time < verification_timeout:
        try:
            await client.get_chat_member(chat_id, user.id)
            is_joined = True
            ctx.log.print(f"{ctx.log.GREEN}User {user.id} berhasil diverifikasi bergabung ke {chat_id}.")
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


async def _create_payment_invoice(client, user, names, tipe, amount, coupon_code=None):
    lang = ctx.L(ctx.db, user.id)
    saweria_service = getattr(client, "services", None) and client.services.saweria

    if not saweria_service:
        if await is_bot_owner(client, user.id):
            text = lang.get("payment.pay.service_inactive_panel")
            btn_text = f"| {lang.get('payment.pay.setup_api_button')} - api_settings |"
            btn, txt = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")
            await client.send_message(user.id, txt, reply_markup=btn)
        else:
            await client.send_message(user.id, lang.get("payment.pay.service_inactive_alert"))
        return

    msg = await client.send_message(user.id, lang.get("general.processing"))

    try:
        saweria_user_id = ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
        if not saweria_user_id:
            raise Exception("Konfigurasi Saweria (User ID) tidak ditemukan di bot ini oleh admin.")

        fakeinfo = client.ns.utils.faker.generate()
        pay = await saweria_service.create_payment(
            user_id=saweria_user_id,
            amount=int(amount),
            name=f"user_id: {user.id}",
            email=fakeinfo.email,
            message=f"Pembelian {names} ({tipe}) via @{client.me.username}",
        )

        if not (hasattr(pay, "result") and hasattr(pay.result, "status") and pay.result.status is True):
            error_msg = (
                pay.result.msg if hasattr(pay, "result") and hasattr(pay.result, "msg") else "Unknown Saweria API error"
            )
            raise Exception(f"API payment gateway mengembalikan error: {error_msg}")

        result = pay.result.data
        payment_id = result.id
        order_id = str(uuid.uuid4())

        order_data = f"{payment_id}|{names}|{tipe}"
        if coupon_code:
            order_data += f"|{coupon_code}"

        ctx.db.setVars(client.me.id, order_id, order_data)

        qr_image_base64 = result.qr_image.split(",", 1)[1]
        qr_bytes = base64.b64decode(qr_image_base64)

        jakarta_tz = ZoneInfo("Asia/Jakarta")
        try:
            expired_dt_naive = datetime.strptime(result.expired_at, "%d/%m/%Y %H:%M:%S")
            expired_dt_utc = expired_dt_naive.replace(tzinfo=timezone.utc)
            expired_dt_jakarta = expired_dt_utc.astimezone(jakarta_tz)
            expire_str = expired_dt_jakarta.strftime("%H:%M:%S %Z")
        except (ValueError, TypeError):
            expire_str = "15 menit"

        if qr_bytes:
            caption = lang.get(
                "payment.pay.invoice_full",
                name=names,
                type=tipe.title(),
                amount=f"{int(result.amount_raw):,}",
                id=order_id,
                expire_time=expire_str,
            )
            btn_text = f"| {lang.get('payment.check.confirm_button')} - confirm_payment {order_id} |"
            btn, _ = client.ns.telegram.button.create_inline_keyboard(btn_text)

            await client.send_photo(user.id, photo=BytesIO(qr_bytes), caption=caption, reply_markup=btn)
        else:
            raise Exception(lang.get("payment.pay.qr_fail"))
        await msg.delete()
    except Exception as e:
        await msg.edit(lang.get("general.error", e=e))


@command(lambda ctx: filters.regex(r"^confirm_payment\s(.+)"), handler_type="callback")
async def manual_check_payment_callback(client, callback_query):
    order_id = callback_query.data.split(" ", 1)[1]
    user = callback_query.from_user
    lang = callback_query.lang

    saweria_service = getattr(client, "services", None) and client.services.saweria
    if not saweria_service:
        return await callback_query.answer(lang.get("payment.pay.service_inactive_alert"), show_alert=True)

    ref_data_str = ctx.db.getVars(client.me.id, order_id)
    if not ref_data_str:
        return await callback_query.edit_message_caption(lang.get("payment.check.expired_or_completed"))

    ref_parts = ref_data_str.split("|")
    payment_id = ref_parts[0]
    name = ref_parts[1]
    tipe = ref_parts[2]
    coupon_code = ref_parts[3] if len(ref_parts) > 3 else None

    saweria_user_id = ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    if not saweria_user_id:
        return await callback_query.answer(
            lang.get("general.error", e="SAWERIA_USER_ID not configured."), show_alert=True
        )

    try:
        pay_check = await saweria_service.check_payment(user_id=saweria_user_id, payment_id=payment_id)

        if hasattr(pay_check, "result") and getattr(pay_check.result, "status", False) is True:
            await callback_query.edit_message_reply_markup(None)

            ctx.db.removeVars(client.me.id, order_id)

            vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
            item_found = next((item for item in vvip_list if item.get("name") == name), None)
            if not item_found:
                raise ValueError(lang.get("payment.check.category_missing", name=name))

            is_promo = tipe == "promo"
            target_chat_id = item_found.get("chat_id_promo") if is_promo else item_found.get("chat_id_normal")

            if not target_chat_id:
                raise ValueError("Chat ID untuk paket VVIP ini belum diatur oleh admin.")

            try:
                expire_date_link = datetime.now() + timedelta(hours=2)
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
                coupons = ctx.db.getListVars(client.me.id, "coupons") or []
                for c in coupons:
                    if c.get("code") == coupon_code:
                        c["uses_left"] = c.get("uses_left", 1) - 1
                        break
                ctx.db.removeVars(client.me.id, "coupons")
                for c in coupons:
                    ctx.db.setListVars(client.me.id, "coupons", c)

            ctx.db.setListVars(client.me.id, "vvip_members", member_data)

            link_msg = await client.send_message(
                user.id,
                lang.get("payment.check.success_customer_full", name=name, link=link),
                protect_content=True,
            )
            await callback_query.message.delete()
            asyncio.create_task(verify_user_join(client, user, target_chat_id, link_msg))

            owner_bot_id = ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id
            owner_lang = Language(ctx.db, owner_bot_id)
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
        else:
            await callback_query.answer(lang.get("payment.check.not_paid"), show_alert=True)

    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Error manual-check {order_id}: {e}")
        await callback_query.answer(lang.get("general.error", e=e), show_alert=True)


@command(lambda ctx: filters.regex(r"^notes\s(.+)"), handler_type="callback")
async def notes_data(client, callback_query):
    lang = callback_query.lang
    name = callback_query.data.split(" ", 1)[1]
    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
    item = next((v for v in vvip_list if v.get("name") == name), None)

    back_btn_text = f"| {lang.get('general.back_to_vvip_list')} - list_vvip |"

    if item:
        price_val = item.get("price", 0)
        normal_text = item.get("normal_text", "")

        desc = (
            normal_text.format(name=name, price=f"{price_val:,}")
            if normal_text
            else lang.get("payment.defaults.notes_text", name=name, price=f"{price_val:,}")
        )

        btn_text = (
            f"| {lang.get('payment.notes.pay_button')} - paynow {name} normal {price_val} |\n"
            f"| {lang.get('coupons.use_button')} - apply_coupon {name} normal {price_val} | | {back_btn_text};same |"
        )

        btn, txt = client.ns.telegram.button.create_inline_keyboard(f"{desc}\n\n{btn_text}")

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(txt, reply_markup=btn)
        return await callback_query.edit_message_text(txt, reply_markup=btn)

    text = lang.get("payment.notes.not_found")
    btn, txt = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{back_btn_text}")
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^promo_detail\s(.+)"), handler_type="callback")
async def promo_detail(client, callback_query):
    lang = callback_query.lang
    name = callback_query.data.split(" ", 1)[1]
    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
    item = next((v for v in vvip_list if v.get("name") == name), None)

    back_btn_text = f"| {lang.get('general.back_to_vvip_list')} - list_vvip |"

    if item and item.get("promo_price", 0) > 0:
        promo_price_val = item.get("promo_price", 0)
        promo_text = item.get("promo_text", "")

        desc = (
            promo_text.format(name=name, promo_price=f"{promo_price_val:,}")
            if promo_text
            else lang.get("payment.defaults.promo_text", name=name, promo_price=f"{promo_price_val:,}")
        )

        btn_text = (
            f"| {lang.get('payment.promo.pay_button')} - paynow {name} promo {promo_price_val} |\n"
            f"| {lang.get('coupons.use_button')} - apply_coupon {name} promo {promo_price_val} | | {back_btn_text};same |"
        )
        btn, txt = client.ns.telegram.button.create_inline_keyboard(f"{desc}\n\n{btn_text}")

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(txt, reply_markup=btn)
        return await callback_query.edit_message_text(txt, reply_markup=btn)

    text = lang.get("payment.promo.not_found")
    btn, txt = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{back_btn_text}")
    if callback_query.message.photo:
        await callback_query.edit_message_caption(txt, reply_markup=btn)
    else:
        await callback_query.edit_message_text(txt, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^apply_coupon\s(.+?)\s(normal|promo)\s(\d+)"), handler_type="callback")
async def apply_coupon_callback(client, callback_query):
    lang = callback_query.lang
    chat_id = callback_query.from_user.id

    match = callback_query.matches[0]
    name = match.group(1).strip()
    tipe = match.group(2)
    original_amount = int(match.group(3))

    await callback_query.message.delete()

    try:
        ask_msg = await client.ask(chat_id, lang.get("coupons.prompt"), timeout=300)
        if ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        coupon_code = ask_msg.text.upper()
        coupons = ctx.db.getListVars(client.me.id, "coupons") or []
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

        final_amount = max(0, int(final_amount))

        await client.send_message(
            chat_id,
            lang.get(
                "coupons.success_applied", code=coupon_code, original=f"{original_amount:,}", final=f"{final_amount:,}"
            ),
        )

        await _create_payment_invoice(client, callback_query.from_user, name, tipe, final_amount, coupon_code)

    except listen.UserCancelled:
        await client.send_message(chat_id, lang.get("general.cancelled"))
    except asyncio.TimeoutError:
        await client.send_message(chat_id, lang.get("general.timeout"))
    except ValueError as e:
        await client.send_message(chat_id, str(e))
    except Exception as e:
        await client.send_message(chat_id, lang.get("general.error", e=e))


@command(lambda ctx: filters.regex(r"^paynow\s(.+)"), handler_type="callback")
async def paynow(client, callback_query):
    parts = callback_query.data.split()
    name_parts = []
    tipe = None
    amount = None

    i = 1
    while i < len(parts):
        if parts[i] in ["normal", "promo"]:
            tipe = parts[i]
            amount = int(parts[i + 1])
            break
        name_parts.append(parts[i])
        i += 1
    name = " ".join(name_parts)

    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text(callback_query.lang.get("general.processing"))

    await _create_payment_invoice(client, callback_query.from_user, name, tipe, amount)


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

    owner_of_this_bot = ctx.db.getVars(current_bot_id, "owner_id") or super_admin_id
    owner_lang = Language(ctx.db, owner_of_this_bot)

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
        ctx.db.setVars(current_bot_id, f"refund_{refund_key}", refund_data)

        refund_callback_data = f"refund_stars_{refund_key}"
        refund_button_text = f"| {owner_lang.get('payment.donation.refund_button')} - {refund_callback_data} |"
        refund_btn, _ = client.ns.telegram.button.create_inline_keyboard(refund_button_text)

        await client.send_message(chat_id=owner_of_this_bot, text=notification_text, reply_markup=refund_btn)

    except pyrogram.errors.UserIsBlocked:
        ctx.log.warning(f"Gagal kirim notif donasi, Owner {owner_of_this_bot} memblokir bot {current_bot_id}")
        if main_bot_client and owner_of_this_bot != super_admin_id:
            super_admin_lang = Language(ctx.db, super_admin_id)
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


@command(lambda ctx: filters.regex(r"^renew_sub\s(.+)"), handler_type="callback")
async def renew_subscription_callback(client, callback_query):
    lang = callback_query.lang
    name = callback_query.data.split(" ", 1)[1]

    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
    item = next((v for v in vvip_list if v.get("name") == name), None)

    if not item:
        return await callback_query.answer(lang.get("payment.notes.not_found"), show_alert=True)

    if item.get("promo_price", 0) > 0:
        callback_query.data = f"promo_detail {name}"
        await promo_detail(client, callback_query)
    else:
        callback_query.data = f"notes {name}"
        await notes_data(client, callback_query)
