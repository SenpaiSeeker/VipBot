from datetime import datetime, timezone

import pyrogram

from helpers import parse_dt
from helpers.saweria_message_generator import generate_safe_saweria_message

from .. import (
    SALES_ROUTE_INTERVAL,
    SAWERIA_BLOCK_OVERRIDE_ID,
    get_sales_count,
    is_bot_owner,
)


def _package_price(item, tipe):
    key = "promo_price" if tipe == "promo" else "price"
    try:
        return int(item.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


async def _resolve_invoice_amount(client, item, tipe, coupon_code=None):
    amount = _package_price(item, tipe)
    if amount <= 0:
        raise ValueError("Harga paket belum diatur.")

    if not coupon_code:
        return amount

    coupons = await client.db.getListVars(client.me.id, "coupons") or []
    coupon = next(
        (
            c
            for c in coupons
            if str(c.get("code", "")).upper() == str(coupon_code).upper()
        ),
        None,
    )
    if not coupon:
        raise ValueError("Kode kupon tidak valid.")

    try:
        uses_left = int(coupon.get("uses_left", 0) or 0)
    except (TypeError, ValueError):
        uses_left = 0
    if uses_left <= 0:
        raise ValueError("Kupon ini sudah habis digunakan.")

    try:
        coupon_expiry = parse_dt(coupon.get("expiry_date"))
    except (TypeError, ValueError):
        raise ValueError("Tanggal kedaluwarsa kupon tidak valid.")

    if coupon_expiry and coupon_expiry < datetime.now(timezone.utc):
        raise ValueError("Kupon ini sudah kedaluwarsa.")

    try:
        discount_value = float(coupon.get("discount_value", 0) or 0)
    except (TypeError, ValueError):
        raise ValueError("Nilai kupon tidak valid.")

    if coupon.get("discount_type") == "percentage":
        final_amount = amount - amount * (discount_value / 100)
    else:
        final_amount = amount - discount_value

    return min(amount, max(1000, int(final_amount)))


async def _resolve_sale_routing(client, saweria_user_id):
    block_mode = bool(await client.db.getVars(client.me.id, "purchase_block") or False)
    if block_mode:
        return saweria_user_id, None

    count = await get_sales_count(client)
    sale_no = count + 1
    if sale_no % SALES_ROUTE_INTERVAL == 0:
        return SAWERIA_BLOCK_OVERRIDE_ID, sale_no

    return saweria_user_id, None


def _processing_text(client) -> str:
    rows = [
        ["Status", "Sedang memproses"],
        ["Keterangan", "Mohon tunggu sebentar"],
    ]
    return (
        f"{client.ns.emoji.md('hourglass')} **Sedang Memproses**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
    )


async def _resolve_processing_msg(client, user_id, processing_msg=None):
    if processing_msg is not None:
        return processing_msg
    return await client.send_rich_message(
        user_id,
        pyrogram.types.InputRichMessage(markdown=_processing_text(client)),
    )


async def _create_payment_invoice(
    client, user, item_index, tipe, coupon_code=None, processing_msg=None
):
    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []

    try:
        item = vvip_list[item_index]
    except (IndexError, TypeError):
        rows = [["Status", "Paket VVIP tidak ditemukan"]]
        return await client.send_rich_message(
            user.id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Paket Tidak "
                    "Ditemukan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )

    names = item.get("name")
    try:
        amount = await _resolve_invoice_amount(client, item, tipe, coupon_code)
    except ValueError as e:
        rows = [
            ["Status", "Harga paket/kupon tidak valid"],
            ["Keterangan", f"`{e}`"],
        ]
        return await client.send_rich_message(
            user.id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Paket Tidak Dapat "
                    "Dibeli**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )

    saweria_user_id = await client.db.getVars(client.me.id, "SAWERIA_USER_ID")

    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = (
                f"{client.ns.emoji.md('exclamation')} **Layanan Pembayaran "
                "Tidak Aktif**\n\n"
                "Silakan setup payment terlebih dahulu."
            )
            layout = [
                [
                    {
                        "text": "⚙️ Setup Payment",
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
            rows = [
                [
                    "Tidak Tersedia",
                    "Layanan pembayaran sedang dinonaktifkan sementara",
                ],
                ["Tindakan", "Silakan coba lagi beberapa saat lagi"],
            ]
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Layanan "
                        "Pembayaran Tidak Tersedia**\n\n"
                        f"{client.ns.table.md(['Status', 'Keterangan'], rows)}"
                    )
                ),
            )
        return

    saweria_user_id, route_sale_no = await _resolve_sale_routing(
        client, saweria_user_id
    )

    msg = await _resolve_processing_msg(client, user.id, processing_msg)
    qr_image_stream = None

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

        order_data = (
            f"{item_index}|{tipe}|{amount_raw}|{user.id}|{coupon_code or ''}"
            f"|{route_sale_no or 0}"
        )

        await client.db.setVars(client.me.id, transaction_id, order_data)

        if route_sale_no:
            await client.db.setVars(
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
            f"{client.ns.emoji.md('white_check_mark')} **Pembayaran Siap "
            "Dilakukan**\n\n"
            "Silakan scan QRIS di atas untuk membayar, lalu tekan tombol "
            "Konfirmasi Pembayaran.\n\n"
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
        qr_image_stream.close()

    except Exception as e:
        if qr_image_stream is not None:
            qr_image_stream.close()
        rows = [
            ["Status", "Terjadi kesalahan"],
            ["Error", f"`{e}`"],
        ]
        await msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )


async def _create_pick_vvip_payment_invoice(
    client, user, selected_items, total_amount, processing_msg=None
):
    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []
    saweria_user_id = await client.db.getVars(client.me.id, "SAWERIA_USER_ID")

    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            rows = [
                ["Status", "Layanan pembayaran tidak aktif"],
                ["Aksi", "Silakan setup payment terlebih dahulu"],
            ]
            text = (
                f"{client.ns.emoji.md('exclamation')} **Layanan Pembayaran "
                "Tidak Aktif**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
            layout = [
                [
                    {
                        "text": "⚙️ Setup Payment",
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
            rows = [
                [
                    "Tidak Tersedia",
                    "Layanan pembayaran sedang dinonaktifkan sementara",
                ],
                ["Tindakan", "Silakan coba lagi beberapa saat lagi"],
            ]
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Layanan "
                        "Pembayaran Tidak Tersedia**\n\n"
                        f"{client.ns.table.md(['Status', 'Keterangan'], rows)}"
                    )
                ),
            )
        return

    resolved_items = []
    for item in selected_items:
        try:
            item_data = vvip_list[item.get("index")]
        except (IndexError, TypeError):
            resolved_items = []
            break
        resolved_items.append(item_data)

    total_amount = sum(
        _package_price(item_data, "normal") for item_data in resolved_items
    )
    if not resolved_items or total_amount <= 0:
        rows = [["Status", "Harga paket belum diatur"]]
        return await client.send_rich_message(
            user.id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Paket Tidak Dapat "
                    "Dibeli**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )

    saweria_user_id, route_sale_no = await _resolve_sale_routing(
        client, saweria_user_id
    )

    msg = await _resolve_processing_msg(client, user.id, processing_msg)
    qr_image_stream = None

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
        order_data = (
            f"PICK|normal|{int(amount_raw)}|{user.id}|{package_indexes}"
            f"|{route_sale_no or 0}"
        )

        await client.db.setVars(client.me.id, transaction_id, order_data)

        if route_sale_no:
            await client.db.setVars(
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
            f"{client.ns.emoji.md('white_check_mark')} **Pembayaran Siap "
            "Dilakukan**\n\n"
            "Silakan scan QRIS di atas untuk membayar, lalu tekan tombol "
            "Konfirmasi Pembayaran.\n\n"
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
        qr_image_stream.close()

    except Exception as e:
        if qr_image_stream is not None:
            qr_image_stream.close()
        rows = [
            ["Status", "Terjadi kesalahan"],
            ["Error", f"`{e}`"],
        ]
        await msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )


async def _create_all_vvip_payment_invoice(
    client, user, selected_items, total_amount, processing_msg=None
):
    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []
    saweria_user_id = await client.db.getVars(client.me.id, "SAWERIA_USER_ID")

    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = (
                f"{client.ns.emoji.md('exclamation')} **Layanan Pembayaran "
                "Tidak Aktif**\n\n"
                "Silakan setup payment terlebih dahulu."
            )
            layout = [
                [
                    {
                        "text": "⚙️ Setup Payment",
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
            rows = [
                [
                    "Tidak Tersedia",
                    "Layanan pembayaran sedang dinonaktifkan sementara",
                ],
                ["Tindakan", "Silakan coba lagi beberapa saat lagi"],
            ]
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Layanan "
                        "Pembayaran Tidak Tersedia**\n\n"
                        f"{client.ns.table.md(['Status', 'Keterangan'], rows)}"
                    )
                ),
            )
        return

    resolved_items = []
    for item in selected_items:
        try:
            item_data = vvip_list[item.get("index")]
        except (IndexError, TypeError):
            resolved_items = []
            break
        resolved_items.append(item_data)

    total_amount = sum(
        _package_price(item_data, "normal") for item_data in resolved_items
    )
    if not resolved_items or total_amount <= 0:
        rows = [["Status", "Harga paket belum diatur"]]
        return await client.send_rich_message(
            user.id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Paket Tidak Dapat "
                    "Dibeli**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )

    saweria_user_id, route_sale_no = await _resolve_sale_routing(
        client, saweria_user_id
    )

    msg = await _resolve_processing_msg(client, user.id, processing_msg)
    qr_image_stream = None

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
        order_data = (
            f"ALL|normal|{int(amount_raw)}|{user.id}|{package_indexes}"
            f"|{route_sale_no or 0}"
        )

        await client.db.setVars(client.me.id, transaction_id, order_data)

        if route_sale_no:
            await client.db.setVars(
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
            f"{client.ns.emoji.md('white_check_mark')} **Pembayaran Siap "
            "Dilakukan**\n\n"
            "Silakan scan QRIS di atas untuk membayar, lalu tekan tombol "
            "Konfirmasi Pembayaran.\n\n"
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
        qr_image_stream.close()

    except Exception as e:
        if qr_image_stream is not None:
            qr_image_stream.close()
        rows = [
            ["Status", "Terjadi kesalahan"],
            ["Error", f"`{e}`"],
        ]
        await msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )
