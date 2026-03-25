from . import *


async def get_start_keyboard_and_content(client, user, lang):
    is_owner = await is_bot_owner(client, user.id)
    is_main_bot = client.me.id == ctx.manager.main_bot_id

    main_text_template = await ctx.db.getVars(client.me.id, "start_text_template")
    photo_id = await ctx.db.getVars(client.me.id, "start_photo_id") or "https://files.catbox.moe/ozzvtz.jpg"

    if not main_text_template:
        key = "start.welcome_main_bot" if is_main_bot else "start.welcome_clone_bot"
        main_text_template = lang.get(key)

    welcome_text = main_text_template.format(mention=client.ns.telegram.arg.getMention(user))

    layout = []

    if is_main_bot:
        layout.append(
            [
                {"text": lang.get("start.create_bot"), "callback_data": "create_bot"},
                {"text": lang.get("start.my_bots"), "callback_data": "list_my_bots_0"},
            ]
        )
    if is_owner:
        layout.append([{"text": lang.get("start.settings_panel"), "callback_data": "settings"}])

    layout.extend(
        [
            [
                {"text": lang.get("start.list_vvip"), "callback_data": "list_vvip"},
                {"text": lang.get("start.donate"), "callback_data": "donate_stars"},
            ],
            [{"text": lang.get("start.about_bot"), "callback_data": "about_bot"}],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)
    return btn, welcome_text, photo_id


@command(lambda ctx: filters.command("start") & filters.private)
@check_new_user
async def start_bot(client, message):
    btn, txt, photo_id = await get_start_keyboard_and_content(client, message.from_user, message.texts)
    await message.reply_photo(photo=photo_id, caption=txt, reply_markup=btn)


@command(lambda ctx: filters.regex("^start$"), handler_type="callback")
async def start_callback(client, callback_query):
    btn, txt, photo_id = await get_start_keyboard_and_content(client, callback_query.from_user, callback_query.texts)
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
    lang = callback_query.texts
    text = lang.get("about.panel")
    layout = [[{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}]]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^close_panel$"), handler_type="callback")
async def close_panel_callback(client, callback_query):
    try:
        await callback_query.message.delete()
    except Exception:
        await callback_query.answer("Done.")


@command(lambda ctx: filters.regex("^list_vvip$"), handler_type="callback")
async def list_vvip_bot(client, callback_query):
    lang = callback_query.texts
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

    layout = []

    if not vvip_list:
        text = lang.get("vvip_list.empty")
        layout.append([{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}])
        btn = client.ns.telegram.button.build_button_grid(layout)
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)

    for index, item in enumerate(vvip_list):
        name = item.get("name", "N/A")
        promo_price = item.get("promo_price", 0)

        button_row = [{"text": lang.get("vvip_list.button_package", name=name), "callback_data": f"notes_{index}"}]

        if promo_price > 0:
            button_row.append(
                {"text": lang.get("vvip_list.button_promo", name=name), "callback_data": f"promo_detail_{index}"}
            )

        layout.append(button_row)

    layout.append([{"text": lang.get("vvip_list.button_take_all_vip"), "callback_data": "pay_all_vvip"}])
    layout.append([{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}])

    btn = client.ns.telegram.button.build_button_grid(layout)
    text = lang.get("vvip_list.panel", mention=client.me.mention)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex("^donate_stars$"), handler_type="callback")
async def donate_callback(client, callback_query):
    lang = callback_query.texts
    photo_url = "https://files.catbox.moe/1f9j10.jpg"
    text = lang.get("donation.panel")
    layout = [
        [{"text": "25 ⭐", "callback_data": "donate_pay_25"}, {"text": "50 ⭐", "callback_data": "donate_pay_50"}],
        [{"text": "75 ⭐", "callback_data": "donate_pay_75"}, {"text": "100 ⭐", "callback_data": "donate_pay_100"}],
        [{"text": lang.get("general.back_to_main_menu"), "callback_data": "start"}],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        if callback_query.message.photo:
            await callback_query.edit_message_caption(caption=text, reply_markup=btn)
        else:
            await callback_query.message.delete()
            await client.send_photo(callback_query.from_user.id, photo=photo_url, caption=text, reply_markup=btn)
    except Exception:
        await callback_query.message.delete()
        await client.send_photo(callback_query.from_user.id, photo=photo_url, caption=text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^donate_pay_(\d+)$"), handler_type="callback")
async def process_donation_callback(client, callback_query):
    lang = callback_query.texts
    try:
        star_amount = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        return await callback_query.answer(lang.get("payment.donation.invalid_amount"), show_alert=True)

    await callback_query.answer(lang.get("payment.donation.preparing"))

    invoice = {
        "title": lang.get("payment.donation.invoice_title"),
        "description": lang.get("payment.donation.invoice_desc", stars=star_amount),
        "payload": f"donation_{star_amount}_{callback_query.from_user.id}_{int(time())}",
        "currency": "XTR",
        "prices": [pyrogram.types.LabeledPrice(f"Donasi {star_amount} Stars", star_amount)],
    }

    try:
        await client.send_invoice(callback_query.from_user.id, **invoice)
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal mengirim invoice Stars: {e}")
        await callback_query.answer(lang.get("payment.donation.invoice_fail"), show_alert=True)
