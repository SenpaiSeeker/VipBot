import asyncio

from helpers.saweria_message_generator import generate_safe_saweria_message

from .. import command, ctx, is_bot_owner


async def _ensure_saweria_available(client, user) -> bool:
    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    if saweria_user_id:
        return True
    if await is_bot_owner(client, user.id):
        text = (
            f"{client.ns.emoji.exclamation} **Layanan Pembayaran Tidak Aktif**\n\n"
            "Silakan atur API Key untuk payment gateway terlebih dahulu."
        )
        layout = [
            [
                {
                    "text": "⚙️ Atur Kunci API",
                    "callback_data": "api_settings",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("toolbox"),
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(user.id, text, reply_markup=btn)
    else:
        await client.send_message(
            user.id,
            "Maaf, layanan pembayaran saat ini tidak tersedia.",
        )
    return False


async def _build_payment(client, user, amount, product_line):
    fakeinfo = client.ns.utils.faker.generate()
    random_message = generate_safe_saweria_message(fakeinfo.name)
    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")

    (
        qr_string,
        transaction_id,
        qr_image_stream,
        amount_raw,
    ) = await client.services.saweria.create_payment(
        user_id=saweria_user_id,
        amount=int(amount),
        name=fakeinfo.name,
        email=fakeinfo.email,
        message=random_message,
        creator_name=client.me.username,
    )

    formatted_amount = f"{int(amount_raw):,}"
    caption = (
        f"**{client.ns.emoji.white_check_mark} Pembayaran Siap Dilakukan!**\n\n"
        "Silakan scan QRIS di atas untuk membayar. Setelah itu, "
        "tekan tombol **Konfirmasi Pembayaran**.\n\n"
        "╭─ **Detail Tagihan**\n"
        "│\n"
        f"├─ {client.ns.emoji.shopping_bags} **Produk:** {product_line}\n"
        f"├─ {client.ns.emoji.gem} **Jumlah:** `Rp {formatted_amount}`\n"
        f"├─ {client.ns.emoji.id_card} **Order ID:** [{transaction_id}](https://saweria.co/qris/{transaction_id})\n"
        "│\n"
        f"╰─ {client.ns.emoji.down_pointing} **Jika sudah membayar, silakan klik tombol di bawah ini.**\n"
    )
    layout = [
        [
            {
                "text": "✅ Konfirmasi Pembayaran",
                "callback_data": f"confirm_payment {transaction_id}",
                "style": "green",
                "emoji": client.ns.emoji.id("white_check_mark"),
            }
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)
    return transaction_id, amount_raw, qr_image_stream, caption, btn


async def _create_payment_invoice(client, user, item_index, tipe, amount, coupon_code=None):
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    try:
        item = vvip_list[item_index]
        names = item.get("name")
    except IndexError:
        return await client.send_message(
            user.id,
            f"{client.ns.emoji.cross_mark} Paket VVIP tidak ditemukan.",
        )

    if not await _ensure_saweria_available(client, user):
        return

    msg = await client.send_message(
        user.id,
        f"{client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.",
    )
    try:
        transaction_id, amount_raw, qr_image_stream, caption, btn = await _build_payment(
            client, user, amount, f"{names} ({tipe.title()})"
        )
        order_data = f"{item_index}|{tipe}|{amount_raw}"
        if coupon_code:
            order_data += f"|{coupon_code}"
        await ctx.db.setVars(client.me.id, transaction_id, order_data)

        await client.send_photo(
            user.id,
            photo=qr_image_stream,
            caption=caption,
            reply_markup=btn,
        )
        await msg.delete()
    except Exception as e:
        await msg.edit(
            f"{client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>{e}</pre>"
        )


async def _create_all_vvip_payment_invoice(client, user, selected_items, total_amount):
    if not await _ensure_saweria_available(client, user):
        return

    msg = await client.send_message(
        user.id,
        f"{client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.",
    )
    try:
        total_len = len(selected_items)
        transaction_id, amount_raw, qr_image_stream, caption, btn = await _build_payment(
            client, user, total_amount, f"Semua VIP ({total_len} paket)"
        )
        package_indexes = ",".join((str(item.get("index")) for item in selected_items))
        order_data = f"ALL|normal|{int(amount_raw)}|{package_indexes}"
        await ctx.db.setVars(client.me.id, transaction_id, order_data)

        await client.send_photo(
            user.id,
            photo=qr_image_stream,
            caption=caption,
            reply_markup=btn,
        )
        await msg.delete()
    except Exception as e:
        await msg.edit(
            f"{client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>{e}</pre>"
        )