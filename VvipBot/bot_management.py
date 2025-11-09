from . import *

BASE_PRICE_BOT = 75000


def calculate_bot_price(months):
    total = BASE_PRICE_BOT * months
    discount_percentage = 0
    if months >= 6:
        discount_percentage = 0.20
    elif months >= 3:
        discount_percentage = 0.10

    discount = int(total * discount_percentage)
    final_price = total - discount
    return total, discount, final_price


async def get_bot_purchase_panel(client, user_id, months=1):
    lang = await ctx.L.create(ctx.db, user_id)
    total, discount, final_price = calculate_bot_price(months)

    text = lang.get(
        "bot_management.payment.panel",
        price=f"{BASE_PRICE_BOT:,}",
        months=months,
        total=f"{total:,}",
        discount=f"-Rp {discount:,}",
        final=f"{final_price:,}",
    )

    layout = [
        [
            {"text": "➖", "callback_data": f"adjust_bot_month_{months-1}"},
            {"text": f"{months} {lang.get('bot_management.payment.month')}", "callback_data": "noop"},
            {"text": "➕", "callback_data": f"adjust_bot_month_{months+1}"},
        ],
        [
            {
                "text": lang.get("bot_management.payment.pay_button", final=f"{final_price:,}"),
                "callback_data": f"pay_bot_qris_{months}",
            }
        ],
        [{"text": lang.get("general.back"), "callback_data": "start"}],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    return text, btn


@command(lambda ctx: filters.regex("^create_bot$"), handler_type="callback")
async def create_bot_callback(client, callback_query):
    user_id = callback_query.from_user.id
    lang = callback_query.lang

    user_expiry_str = await ctx.db.getVars(user_id, "user_expiry_date")
    if user_expiry_str:
        expiry_date = datetime.fromisoformat(user_expiry_str)
        if expiry_date > datetime.now(timezone.utc):
            text = lang.get("bot_management.payment.already_subscribed")
            layout = [
                [
                    {
                        "text": lang.get("bot_management.payment.proceed_create_button"),
                        "callback_data": "start_creation_process",
                    }
                ],
                [{"text": lang.get("general.back"), "callback_data": "start"}],
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            return await callback_query.edit_message_caption(text, reply_markup=btn)

    text, btn = await get_bot_purchase_panel(client, user_id, 1)
    await callback_query.edit_message_caption(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^adjust_bot_month_(\d+)"), handler_type="callback")
async def adjust_bot_month_callback(client, callback_query):
    months = int(callback_query.data.split("_")[-1])
    if 1 <= months <= 12:
        text, btn = await get_bot_purchase_panel(client, callback_query.from_user.id, months)
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.answer("Durasi minimal 1 bulan dan maksimal 12 bulan.", show_alert=True)


@command(lambda ctx: filters.regex(r"^pay_bot_qris_(\d+)"), handler_type="callback")
async def proceed_bot_payment_callback(client, callback_query):
    user_id = callback_query.from_user.id
    months = int(callback_query.data.split("_")[-1])
    lang = callback_query.lang

    await callback_query.edit_message_caption(lang.get("general.processing"))

    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    if not saweria_user_id:
        return await callback_query.edit_message_caption(lang.get("payment.pay.service_inactive_alert"))

    _, _, amount = calculate_bot_price(months)
    fakeinfo = client.ns.utils.faker.generate()

    try:
        qr_string, transaction_id, qr_image_stream, amount_raw = await client.services.saweria.create_payment(
            user_id=saweria_user_id,
            amount=int(amount),
            name=f"User-{user_id}",
            email=fakeinfo.email,
            message=f"Akses Buat Bot VVIP {months} bulan",
            creator_name=client.me.username,
        )

        order_data = f"{months}|{amount_raw}"
        await ctx.db.setVars(client.me.id, transaction_id, order_data)

        caption = lang.get(
            "payment.pay.invoice_full",
            name=f"Akses Buat Bot {months} Bulan",
            type="Langganan",
            amount=f"{amount_raw:,}",
            id=f"[{transaction_id}](https://saweria.co/qris/{transaction_id})",
        )
        layout = [
            [
                {
                    "text": lang.get("payment.check.confirm_button"),
                    "callback_data": f"confirm_bot_payment_{transaction_id}",
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await callback_query.message.delete()
        await client.send_photo(user_id, qr_image_stream, caption=caption, reply_markup=btn)
    except Exception as e:
        await client.send_message(user_id, lang.get("general.error", e=e))


@command(lambda ctx: filters.regex(r"^confirm_bot_payment_(.+)"), handler_type="callback")
async def confirm_bot_payment_callback(client, callback_query):
    transaction_id = callback_query.data.split("_")[-1]
    user = callback_query.from_user
    lang = callback_query.lang

    order_data_str = await ctx.db.getVars(client.me.id, transaction_id)
    if not order_data_str:
        return await callback_query.answer(lang.get("payment.check.expired_or_completed"), show_alert=True)

    months_str, amount_raw_str = order_data_str.split("|")
    months = int(months_str)
    amount_raw = int(amount_raw_str)

    try:
        is_paid = await client.services.saweria.check_paid_status(transaction_id)
        if is_paid:
            await ctx.db.removeVars(client.me.id, transaction_id)

            expiry_date = datetime.now(timezone.utc) + timedelta(days=30 * months)
            await ctx.db.setVars(user.id, "user_expiry_date", expiry_date.isoformat())

            await callback_query.message.delete()

            success_text = lang.get("bot_management.payment.success", months=months)
            layout = [
                [
                    {
                        "text": lang.get("bot_management.payment.proceed_create_button"),
                        "callback_data": "start_creation_process",
                    }
                ]
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(user.id, success_text, reply_markup=btn)

            owner_notif = lang.get(
                "bot_management.payment.owner_notif",
                mention=client.ns.telegram.arg.getMention(user),
                months=months,
                amount=f"{amount_raw:,}",
            )
            await client.send_message(ctx.owner_id, owner_notif)
        else:
            await callback_query.answer(lang.get("payment.check.not_paid"), show_alert=True)

    except Exception as e:
        await callback_query.answer(lang.get("general.error", e=e), show_alert=True)


@command(lambda ctx: filters.regex("^start_creation_process$"), handler_type="callback")
async def start_creation_process_callback(client, callback_query):
    user_id = callback_query.from_user.id
    lang = callback_query.lang

    expiry_date_str = await ctx.db.getVars(user_id, "user_expiry_date")
    if not expiry_date_str or datetime.fromisoformat(expiry_date_str) < datetime.now(timezone.utc):
        return await callback_query.answer("Langganan Anda tidak valid atau telah berakhir.", show_alert=True)

    await callback_query.message.delete()

    try:

        def ask(text):
            return client.ask(user_id, f"{text}{lang.get('prompts.cancel_footer')}", timeout=600)

        api_id_msg = await ask(lang.get("bot_management.create.step1_api_id"))
        if api_id_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        api_id = api_id_msg.text

        api_hash_msg = await ask(lang.get("bot_management.create.step2_api_hash"))
        if api_hash_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        api_hash = api_hash_msg.text

        token_msg = await ask(lang.get("bot_management.create.step3_bot_token"))
        if token_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        token = token_msg.text

        msg = await client.send_message(user_id, lang.get("bot_management.create.verifying"))
        new_bot_name = await client.ns.telegram.arg.getNamebot(token)
        if "invalid" in [new_bot_name]:
            raise ValueError(lang.get("bot_management.create.invalid_token"))

        await msg.edit(lang.get("bot_management.create.saving", name=new_bot_name.first_name))

        new_bot_id = int(token.split(":", 1)[0])
        bot_data = {"name": str(new_bot_id), "api_id": api_id, "api_hash": api_hash, "bot_token": token}
        await ctx.manager.start_bot(bot_data)

        await ctx.db.saveBot(new_bot_id, api_id, api_hash, token, is_token=True)
        await ctx.db.setVars(new_bot_id, "bot_expiration_date", expiry_date_str)
        await ctx.db.setVars(new_bot_id, "owner_id", user_id)
        await ctx.db.removeVars(user_id, "user_expiry_date")

        await msg.edit(lang.get("bot_management.create.success", name=new_bot_name.first_name))
    except listen.UserCancelled:
        await client.send_message(user_id, lang.get("general.cancelled"))
    except asyncio.TimeoutError:
        await client.send_message(user_id, lang.get("general.timeout"))
    except Exception as e:
        await client.send_message(user_id, lang.get("bot_management.create.fail", e=e))


@command(lambda ctx: filters.regex(r"^list_my_bots(_\d+)?$"), handler_type="callback")
async def list_my_bots_callback(client, callback_query):
    user_id = callback_query.from_user.id
    lang = callback_query.lang

    my_bots = []
    all_bots_data = await ctx.db.getBots(is_token=True)
    for b in all_bots_data:
        owner = await ctx.db.getVars(int(b["name"]), "owner_id")
        if (owner or 0) == user_id:
            my_bots.append(b)

    if not my_bots:
        return await callback_query.answer(lang.get("bot_management.my_bots.empty"), show_alert=True)

    parts = callback_query.data.split("_")
    page = int(parts[-1]) if len(parts) > 2 and parts[-1].isdigit() else 0
    total_pages = len(my_bots)
    page = (page + total_pages) % total_pages
    bot_data = my_bots[page]
    bot_id = int(bot_data["name"])

    bot_name = f"ID {bot_id} ({lang.get('admin.allbots.offline')})"
    bot_username = "N/A"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username
    except Exception:
        bot_name = f"ID {bot_id} ({lang.get('admin.allbots.error')})"

    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    days_left = (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days if exp_date_str else "N/A"

    text = lang.get(
        "bot_management.my_bots.panel",
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
                {"text": lang.get("admin.allbots.prev_button"), "callback_data": f"list_my_bots_{prev_page}"},
                {"text": lang.get("admin.allbots.next_button"), "callback_data": f"list_my_bots_{next_page}"},
            ]
        )
    if pagination_row:
        layout.append(pagination_row)

    layout.extend(
        [
            [
                {
                    "text": lang.get("bot_management.my_bots.manage_button", name=bot_name),
                    "callback_data": f"manage_bot {bot_id}",
                }
            ],
            [{"text": lang.get("general.back"), "callback_data": "start"}],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^manage_bot\s(\d+)"), handler_type="callback")
async def manage_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    lang = callback_query.lang
    owner_of_target_bot = await ctx.db.getVars(bot_id_to_manage, "owner_id") or 0

    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await callback_query.answer(lang.get("general.not_your_bot"), show_alert=True)

    bot_name = f"ID {bot_id_to_manage}"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    exp_date_str = await ctx.db.getVars(bot_id_to_manage, "bot_expiration_date")
    days_left_text = lang.get("bot_management.manage.not_set")
    if exp_date_str:
        days_left = (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days
        days_left_text = f"{days_left} {lang.get('admin.allbots.days')}"

    layout = [
        [
            {
                "text": lang.get("bot_management.manage.extend_button"),
                "callback_data": f"request_extend_duration {bot_id_to_manage}",
            }
        ],
        [
            {
                "text": lang.get("bot_management.manage.delete_button"),
                "callback_data": f"confirm_delete_bot {bot_id_to_manage}",
            }
        ],
        [{"text": lang.get("general.back_to_bot_list"), "callback_data": "list_my_bots_0"}],
    ]

    text = lang.get(
        "bot_management.manage.panel",
        name=bot_name,
        id=bot_id_to_manage,
        days_left=days_left_text,
    )

    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex(r"^request_extend_duration\s(\d+)"),
    handler_type="callback",
)
async def request_extend_duration_callback(client, callback_query):
    bot_id_to_request = int(callback_query.data.split(" ", 1)[1])
    requester = callback_query.from_user
    lang = callback_query.lang
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
            raise ConnectionError(lang.get("bot_management.create.main_bot_inactive"))

        txt_owner = lang.get(
            "bot_management.extend.panel_owner",
            mention=main_bot_client.ns.telegram.arg.getMention(requester),
            id=requester.id,
            bot_name=bot_name,
            bot_id=bot_id_to_request,
        )

        layout_owner = [
            [
                {
                    "text": lang.get("bot_management.extend.approve_button"),
                    "callback_data": f"approve_extension {bot_id_to_request} {requester.id}",
                },
                {
                    "text": lang.get("bot_management.extend.reject_button"),
                    "callback_data": f"close_req {bot_id_to_request} {requester.id}",
                },
            ]
        ]

        btn_owner = main_bot_client.ns.telegram.button.build_button_grid(layout_owner)
        await main_bot_client.send_message(ctx.owner_id, txt_owner, reply_markup=btn_owner)
        await callback_query.answer(lang.get("bot_management.extend.sent_alert"), show_alert=True)

    except Exception as e:
        await callback_query.answer(lang.get("bot_management.extend.fail_alert", e=e), show_alert=True)


@command(
    lambda ctx: filters.regex(r"^approve_extension\s(\d+)\s(\d+)"),
    handler_type="callback",
)
async def owner_approve_extension_callback(client, callback_query):
    lang = callback_query.lang
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(lang.get("bot_management.extend.approve_denied"), show_alert=True)
    try:
        _, bot_id_str, requester_id_str = callback_query.data.split()
        bot_id_to_extend, requester_id, days_to_add = (
            int(bot_id_str),
            int(requester_id_str),
            30,
        )

        exp_date_str = await ctx.db.getVars(bot_id_to_extend, "bot_expiration_date")
        current_exp_date = datetime.fromisoformat(exp_date_str) if exp_date_str else datetime.now(timezone.utc)
        new_exp_date = current_exp_date + timedelta(days=days_to_add)
        await ctx.db.setVars(bot_id_to_extend, "bot_expiration_date", new_exp_date.isoformat())

        await callback_query.edit_message_text(
            lang.get(
                "bot_management.extend.approve_success_log",
                bot_id=bot_id_to_extend,
                days=days_to_add,
            )
        )

        try:
            bot_instance = ctx.manager.running_bots.get(bot_id_to_extend)
            bot_name = (
                bot_instance.me.first_name if bot_instance and bot_instance.is_connected else f"ID {bot_id_to_extend}"
            )
            await client.send_message(
                requester_id,
                lang.get("bot_management.extend.approve_success_notif", bot_name=bot_name),
            )
        except Exception as e:
            ctx.log.print(f"{ctx.log.YELLOW}Gagal kirim notif persetujuan ke {requester_id}: {e}")

    except Exception as e:
        await callback_query.edit_message_text(lang.get("bot_management.extend.approve_fail", e=e))


@command(lambda ctx: filters.regex(r"^close_req\s(\d+)\s(\d+)"), handler_type="callback")
async def owner_close_request_callback(client, callback_query):
    lang = callback_query.lang
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(lang.get("bot_management.extend.reject_denied"), show_alert=True)
    try:
        await callback_query.edit_message_text(lang.get("bot_management.extend.rejected_log"))
    except Exception:
        pass


@command(lambda ctx: filters.regex(r"^confirm_delete_bot\s(\d+)"), handler_type="callback")
async def confirm_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    lang = callback_query.lang
    bot_name = f"ID {bot_id_to_manage}"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    text = lang.get("bot_management.delete.confirm_panel", name=bot_name, id=bot_id_to_manage)
    layout = [
        [
            {
                "text": lang.get("bot_management.delete.confirm_yes_button"),
                "callback_data": f"do_delete_bot {bot_id_to_manage}",
            },
            {
                "text": lang.get("bot_management.delete.confirm_no_button"),
                "callback_data": f"manage_bot {bot_id_to_manage}",
            },
        ]
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^do_delete_bot\s(\d+)"), handler_type="callback")
async def do_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    lang = callback_query.lang
    owner_of_target_bot = await ctx.db.getVars(bot_id_to_manage, "owner_id") or 0

    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await callback_query.answer(lang.get("bot_management.delete.no_permission"), show_alert=True)

    await callback_query.edit_message_caption(lang.get("bot_management.delete.processing", bot_id=bot_id_to_manage))

    try:
        await ctx.manager.stop_bot(bot_id_to_manage)
        await ctx.db.removeBot(bot_id_to_manage)
        await ctx.db.removeAllVars(bot_id_to_manage)
        ctx.log.print(f"{ctx.log.ORANGE}Bot {bot_id_to_manage} telah dihapus oleh owner-nya ({user_id}).")

        layout = [[{"text": lang.get("general.back_to_bot_list"), "callback_data": "list_my_bots_0"}]]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await callback_query.edit_message_caption(
            lang.get("bot_management.delete.success", id=bot_id_to_manage),
            reply_markup=btn,
        )
    except Exception as e:
        await callback_query.edit_message_caption(lang.get("bot_management.delete.fail", e=e))
