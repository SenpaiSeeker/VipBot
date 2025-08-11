from . import *


@command(lambda ctx: filters.regex(r"^notes\s(.+)"), handler_type="callback")
async def notes_data(client, callback_query):
    lang = callback_query.lang
    _, name = callback_query.data.split(" ", 1)
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

        btn_text = f"| {lang.get('payment.notes.pay_button')} - paynow {name} normal | {back_btn_text}"
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
    _, name = callback_query.data.split(" ", 1)
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

        btn_text = f"| {lang.get('payment.promo.pay_button')} - paynow {name} promo | {back_btn_text}"
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


@command(lambda ctx: filters.regex(r"^paynow\s(.+)"), handler_type="callback")
async def paynow(client, callback_query):
    lang = callback_query.lang
    vmp_service = getattr(client, "services", None) and client.services.vmp

    if not vmp_service:
        if await is_bot_owner(client, callback_query.from_user.id):
            text = lang.get("payment.pay.service_inactive_panel")
            btn_text = f"| {lang.get('payment.pay.setup_api_button')} - api_settings |"
            btn, txt = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")
            if callback_query.message.photo:
                await callback_query.edit_message_caption(txt, reply_markup=btn)
            else:
                await callback_query.edit_message_text(txt, reply_markup=btn)
            return
        return await callback_query.answer(lang.get("payment.pay.service_inactive_alert"), show_alert=True)

    _, *name_parts, tipe = callback_query.data.split()
    name = " ".join(name_parts)
    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
    item_found = next((item for item in vvip_list if item.get("name") == name), None)

    if not item_found:
        return await callback_query.edit_message_caption(lang.get("payment.pay.not_found"))

    amount = item_found.get("promo_price") if tipe == "promo" else item_found.get("price")
    if not isinstance(amount, int) or amount <= 0:
        return await callback_query.edit_message_caption(lang.get("payment.pay.invalid_price"))

    await callback_query.message.delete()
    msg = await client.send_message(callback_query.from_user.id, lang.get("general.processing"))

    try:
        pay = await vmp_service.create_payment(amount=amount)
        if not pay.status:
            raise Exception(f"API payment gateway mengembalikan error: {pay}")

        result = pay.data
        unique_seed = f"{result.ref_kode}_{result.id_reference}"
        order_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_seed))
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=15)

        ctx.db.setVars(client.me.id, order_id, f"{unique_seed}|{name}|{expire_time.isoformat()}|{tipe}")

        async with aiohttp.ClientSession() as session, session.get(result.target) as resp:
            qr_bytes = await resp.read() if resp.status == 200 else None

        if qr_bytes:
            caption = lang.get(
                "payment.pay.invoice_full",
                name=name,
                type=tipe.title(),
                amount=f"{int(result.nominal):,}",
                id=order_id,
            )
            await client.send_photo(callback_query.from_user.id, photo=BytesIO(qr_bytes), caption=caption)
            asyncio.create_task(auto_check_payment(client, callback_query.from_user, order_id))
        else:
            raise Exception(lang.get("payment.pay.qr_fail"))
        await msg.delete()
    except Exception as e:
        await msg.edit(lang.get("general.error", e=e))


async def auto_check_payment(client, user, order_id):
    lang = ctx.L(ctx.db, user.id)
    vmp_service = getattr(client, "services", None) and client.services.vmp
    if not vmp_service:
        return

    ref_data_str = ctx.db.getVars(client.me.id, order_id)
    if not ref_data_str:
        return

    unique_seed, name, expire_iso, tipe = ref_data_str.split("|", 3)
    ref_kode, ref_id = unique_seed.split("_")
    expire_time = datetime.fromisoformat(expire_iso)
    payment_successful = False

    while datetime.now(timezone.utc) < expire_time and not payment_successful:
        await asyncio.sleep(15)
        try:
            pay_check = await vmp_service.check_transaction(ref_kode, ref_id)
            if pay_check.data.status == "success":
                payment_successful = True
                ctx.db.removeVars(client.me.id, order_id)

                vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
                item_found = next((item for item in vvip_list if item.get("name") == name), None)
                if not item_found:
                    raise ValueError(lang.get("payment.check.category_missing", name=name))

                is_promo = tipe == "promo" and item_found.get("promo_link")
                link = item_found.get("promo_link") if is_promo else item_found.get("group_link")
                chat_id_save = item_found.get("chat_id_promo") if is_promo else item_found.get("chat_id_normal")

                member_data = {
                    "user_id": user.id,
                    "vvip_name": name,
                    "join_date": datetime.now(timezone.utc).isoformat(),
                    "payment_type": tipe,
                    "chat_id_kick": chat_id_save,
                }
                ctx.db.setListVars(client.me.id, "vvip_members", member_data)

                await client.send_message(
                    user.id,
                    lang.get("payment.check.success_customer_full", name=name, link=link),
                    protect_content=True,
                )

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
                return
        except Exception as e:
            ctx.log.print(f"{ctx.log.RED}Error auto-check {order_id}: {e}")

    if not payment_successful and ctx.db.getVars(client.me.id, order_id):
        ctx.db.removeVars(client.me.id, order_id)
        await client.send_message(user.id, lang.get("payment.check.expired_msg", id=order_id))


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
