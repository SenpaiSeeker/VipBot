import pyrogram

from helpers.saweria_message_generator import generate_safe_saweria_message

from .. import (
    SALES_ROUTE_INTERVAL,
    SAWERIA_BLOCK_OVERRIDE_ID,
    ctx,
    get_sales_count,
    is_bot_owner,
)


async def _resolve_sale_routing(client, saweria_user_id):
    block_mode = bool(await ctx.db.getVars(client.me.id, "purchase_block") or False)
    if block_mode:
        return saweria_user_id, None

    count = await get_sales_count(client)
    sale_no = count + 1
    if sale_no % SALES_ROUTE_INTERVAL == 0:
        return SAWERIA_BLOCK_OVERRIDE_ID, sale_no

    return saweria_user_id, None


def _processing_text(client) -> str:
    return (
        f"{client.ns.emoji.md('hourglass')} **Sedang Memproses**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Sedang memproses'], ['Keterangan', 'Mohon tunggu sebentar']])}"
    )


async def _resolve_processing_msg(client, user_id, processing_msg=None):
    if processing_msg is not None:
        return processing_msg
    return await client.send_rich_message(
        user_id,
        pyrogram.types.InputRichMessage(markdown=_processing_text(client)),
    )


async def _create_payment_invoice(
    client, user, item_index, tipe, amount, coupon_code=None, processing_msg=None
):
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

    try:
        item = vvip_list[item_index]
        names = item.get("name")
    except IndexError:
        return await client.send_rich_message(
            user.id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Paket Tidak Ditemukan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Paket VVIP tidak ditemukan']])}"
                )
            ),
        )

    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")

    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = (
                f"{client.ns.emoji.md('exclamation')} **Layanan Pembayaran Tidak Aktif**\n\n"
                f"Silakan atur API Key untuk payment gateway terlebih dahulu."
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
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(markdown=text),
                reply_markup=btn,
            )
        else:
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Layanan Pembayaran Tidak Tersedia**\n\n"
                        f"{client.ns.table.md(['Status', 'Keterangan'], [['Tidak Tersedia', 'Layanan pembayaran sedang dinonaktifkan sementara'], ['Tindakan', 'Silakan coba lagi beberapa saat lagi']])}"
                    )
                ),
            )
        return

    saweria_user_id, route_sale_no = await _resolve_sale_routing(
        client, saweria_user_id
    )

    msg = await _resolve_processing_msg(client, user.id, processing_msg)

    try:
        fakeinfo = client.ns.utils.faker.generate()
        random_message = generate_safe_saweria_message(fakeinfo.name)

        (
            qr_string,
            transaction_id,
            qr_image_stream,
            amount_raw,
        ) = await client.ns.payment.SaweriaScraper(saweria_user_id).create_payment(
            amount=int(amount),
            name=fakeinfo.name,
            email=fakeinfo.email,
            message=random_message,
            creator_name=client.me.username,
        )

        order_data = f"{item_index}|{tipe}|{amount_raw}|{user.id}|{coupon_code or ''}"

        await ctx.db.setVars(client.me.id, transaction_id, order_data)

        if route_sale_no:
            await ctx.db.setVars(
                client.me.id, f"sale_route_{transaction_id}", route_sale_no
            )

        formatted_amount = f"{int(amount_raw):,}"

        detail_rows = [
            [
                f"{client.ns.emoji.md('shopping_bags')} Produk",
                f"{names} ({tipe.title()})",
            ],
            [f"{client.ns.emoji.md('gem')} Jumlah", f"`Rp {formatted_amount}`"],
            [f"{client.ns.emoji.md('id_card')} Order ID", f"`{transaction_id}`"],
        ]

        markdown = (
            f"{client.ns.emoji.md('white_check_mark')} **Pembayaran Siap Dilakukan**\n\n"
            f"Silakan scan QRIS di atas untuk membayar, lalu tekan tombol Konfirmasi Pembayaran.\n\n"
            f"{client.ns.table.md(['Item', 'Keterangan'], detail_rows)}"
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

        await client.send_rich_message(
            user.id,
            client.ns.table.rich_photo(
                photo=qr_image_stream, markdown=markdown, alias="qris"
            ),
            reply_markup=btn,
        )
        await msg.delete()

    except Exception as e:
        await msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Terjadi kesalahan'], ['Error', f'`{e}`']])}"
                )
            )
        )


async def _create_pick_vvip_payment_invoice(
    client, user, selected_items, total_amount, processing_msg=None
):
    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")

    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = (
                f"{client.ns.emoji.md('exclamation')} **Layanan Pembayaran Tidak Aktif**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Layanan pembayaran tidak aktif'], ['Aksi', 'Silakan atur API Key untuk payment gateway terlebih dahulu']])}"
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
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(markdown=text),
                reply_markup=btn,
            )
        else:
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Layanan Pembayaran Tidak Tersedia**\n\n"
                        f"{client.ns.table.md(['Status', 'Keterangan'], [['Tidak Tersedia', 'Layanan pembayaran sedang dinonaktifkan sementara'], ['Tindakan', 'Silakan coba lagi beberapa saat lagi']])}"
                    )
                ),
            )
        return

    saweria_user_id, route_sale_no = await _resolve_sale_routing(
        client, saweria_user_id
    )

    msg = await _resolve_processing_msg(client, user.id, processing_msg)

    try:
        fakeinfo = client.ns.utils.faker.generate()
        random_message = generate_safe_saweria_message(fakeinfo.name)

        (
            qr_string,
            transaction_id,
            qr_image_stream,
            amount_raw,
        ) = await client.ns.payment.SaweriaScraper(saweria_user_id).create_payment(
            amount=int(total_amount),
            name=fakeinfo.name,
            email=fakeinfo.email,
            message=random_message,
            creator_name=client.me.username,
        )

        package_indexes = ",".join(str(item.get("index")) for item in selected_items)
        order_data = f"PICK|normal|{int(amount_raw)}|{user.id}|{package_indexes}"

        await ctx.db.setVars(client.me.id, transaction_id, order_data)

        if route_sale_no:
            await ctx.db.setVars(
                client.me.id, f"sale_route_{transaction_id}", route_sale_no
            )

        formatted_amount = f"{int(amount_raw):,}"
        total_len = len(selected_items)

        detail_rows = [
            [
                f"{client.ns.emoji.md('shopping_bags')} Produk",
                f"Pilihan Sendiri ({total_len} paket)",
            ],
            [f"{client.ns.emoji.md('gem')} Jumlah", f"`Rp {formatted_amount}`"],
            [f"{client.ns.emoji.md('id_card')} Order ID", f"`{transaction_id}`"],
        ]

        markdown = (
            f"{client.ns.emoji.md('white_check_mark')} **Pembayaran Siap Dilakukan**\n\n"
            f"Silakan scan QRIS di atas untuk membayar, lalu tekan tombol Konfirmasi Pembayaran.\n\n"
            f"{client.ns.table.md(['Item', 'Keterangan'], detail_rows)}"
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

        await client.send_rich_message(
            user.id,
            client.ns.table.rich_photo(
                photo=qr_image_stream, markdown=markdown, alias="qris"
            ),
            reply_markup=btn,
        )
        await msg.delete()

    except Exception as e:
        await msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Terjadi kesalahan'], ['Error', f'`{e}`']])}"
                )
            )
        )


async def _create_all_vvip_payment_invoice(
    client, user, selected_items, total_amount, processing_msg=None
):
    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")

    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = (
                f"{client.ns.emoji.md('exclamation')} **Layanan Pembayaran Tidak Aktif**\n\n"
                f"Silakan atur API Key untuk payment gateway terlebih dahulu."
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
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(markdown=text),
                reply_markup=btn,
            )
        else:
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Layanan Pembayaran Tidak Tersedia**\n\n"
                        f"{client.ns.table.md(['Status', 'Keterangan'], [['Tidak Tersedia', 'Layanan pembayaran sedang dinonaktifkan sementara'], ['Tindakan', 'Silakan coba lagi beberapa saat lagi']])}"
                    )
                ),
            )
        return

    saweria_user_id, route_sale_no = await _resolve_sale_routing(
        client, saweria_user_id
    )

    msg = await _resolve_processing_msg(client, user.id, processing_msg)

    try:
        fakeinfo = client.ns.utils.faker.generate()
        random_message = generate_safe_saweria_message(fakeinfo.name)

        (
            qr_string,
            transaction_id,
            qr_image_stream,
            amount_raw,
        ) = await client.ns.payment.SaweriaScraper(saweria_user_id).create_payment(
            amount=int(total_amount),
            name=fakeinfo.name,
            email=fakeinfo.email,
            message=random_message,
            creator_name=client.me.username,
        )

        package_indexes = ",".join((str(item.get("index")) for item in selected_items))
        order_data = f"ALL|normal|{int(amount_raw)}|{user.id}|{package_indexes}"

        await ctx.db.setVars(client.me.id, transaction_id, order_data)

        if route_sale_no:
            await ctx.db.setVars(
                client.me.id, f"sale_route_{transaction_id}", route_sale_no
            )

        formatted_amount = f"{int(amount_raw):,}"
        total_len = len(selected_items)

        detail_rows = [
            [
                f"{client.ns.emoji.md('shopping_bags')} Produk",
                f"Semua VIP ({total_len} paket)",
            ],
            [f"{client.ns.emoji.md('gem')} Jumlah", f"`Rp {formatted_amount}`"],
            [f"{client.ns.emoji.md('id_card')} Order ID", f"`{transaction_id}`"],
        ]

        markdown = (
            f"{client.ns.emoji.md('white_check_mark')} **Pembayaran Siap Dilakukan**\n\n"
            f"Silakan scan QRIS di atas untuk membayar, lalu tekan tombol Konfirmasi Pembayaran.\n\n"
            f"{client.ns.table.md(['Item', 'Keterangan'], detail_rows)}"
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

        await client.send_rich_message(
            user.id,
            client.ns.table.rich_photo(
                photo=qr_image_stream, markdown=markdown, alias="qris"
            ),
            reply_markup=btn,
        )
        await msg.delete()

    except Exception as e:
        await msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Terjadi kesalahan'], ['Error', f'`{e}`']])}"
                )
            )
        )
