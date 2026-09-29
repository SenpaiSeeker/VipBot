import asyncio
import re
from datetime import datetime, timezone

from pyrogram import filters

from helpers import parse_dt

from .. import (
    LIST_VVIP_ICON_BUY_ALL_KEY,
    command,
    ctx,
    get_list_vvip_icons,
    listen,
    render_list_vvip_icon_html,
)
from .invoice import _create_all_vvip_payment_invoice, _create_payment_invoice
from .verifier import _get_all_vvip_items


@command(
    lambda ctx: filters.regex("^pay_all_vvip$"),
    handler_type="callback",
)
async def pay_all_vvip_callback(client, callback_query):
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    selected_items = _get_all_vvip_items(vvip_list)

    if not selected_items:
        return await callback_query.answer(
            "❌ Tidak ada paket VIP valid untuk pembelian semua VIP.",
            show_alert=True,
        )

    total_amount = sum((item.get("price", 0) for item in selected_items))
    icons = await get_list_vvip_icons(client)

    package_lines = []
    for item in selected_items:
        name = item.get("name", "Paket")
        price = item.get("price", 0)
        icon_html = render_list_vvip_icon_html(client, icons, name)
        package_lines.append(f"{icon_html} **{name}** — `Rp {int(price):,}`")
    packages_text = "\n".join(package_lines)

    text = (
        f"{render_list_vvip_icon_html(client, icons, LIST_VVIP_ICON_BUY_ALL_KEY, kind='buy_all')} "
        f"**Ringkasan Ambil Semua VIP**\n\n"
        f"{packages_text}\n\n"
        f"{client.ns.emoji.money_bag} **Total:** `Rp {int(total_amount):,}` "
        f"({len(selected_items)} paket)"
    )

    layout = [
        [
            {
                "text": "💳 Lakukan Pembayaran",
                "callback_data": "pay_all_vvip_confirm",
                "style": "green",
                "emoji": client.ns.emoji.id("white_check_mark"),
            }
        ],
        [
            {
                "text": "• Kembali ke Daftar VVIP •",
                "callback_data": "list_vvip",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^pay_all_vvip_confirm$"),
    handler_type="callback",
)
async def pay_all_vvip_confirm_callback(client, callback_query):
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    selected_items = _get_all_vvip_items(vvip_list)

    if not selected_items:
        return await callback_query.answer(
            "❌ Tidak ada paket VIP valid untuk pembelian semua VIP.",
            show_alert=True,
        )

    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text(
            f"{client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar."
        )

    total_amount = sum((item.get("price", 0) for item in selected_items))

    await _create_all_vvip_payment_invoice(
        client,
        callback_query.from_user,
        selected_items,
        total_amount,
    )


@command(
    lambda ctx: filters.regex("^notes_(.+)"),
    handler_type="callback",
)
async def notes_data(client, callback_query):
    item_id = callback_query.matches[0].group(1)

    if item_id.isdigit():
        item_index = int(item_id)
    else:
        if not hasattr(ctx, "vip_list") or item_id not in ctx.vip_list:
            return await callback_query.answer(
                "Sesi kedaluwarsa, silakan muat ulang menu.",
                show_alert=True,
            )
        item_index = ctx.vip_list[item_id]

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

    layout = [
        [
            {
                "text": "• Kembali ke Daftar VVIP •",
                "callback_data": "list_vvip",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]

    try:
        item = vvip_list[item_index]
    except IndexError:
        item = None

    if item:
        name = item.get("name")
        price_val = item.get("price", 0)
        normal_text = item.get("normal_text", "")
        formatted_price = f"{price_val:,}"

        desc = (
            normal_text.replace("{name}", name).replace("{price}", formatted_price)
            if normal_text
            else (
                f"╭─ **{client.ns.emoji.sparkles} Detail Paket VVIP**\n"
                f"│\n"
                f"├─ {client.ns.emoji.open_folder} **Nama Paket:** `{name}`\n"
                f"├─ {client.ns.emoji.pencil} **Deskripsi:** Dapatkan akses instan ke konten premium dan eksklusif setelah pembayaran berhasil.\n"
                f"│\n"
                f"├─ {client.ns.emoji.gem} **Harga Normal:** `Rp {formatted_price}`\n"
                f"│\n"
                f"╰─ Silakan klik tombol 'Bayar' di bawah untuk melanjutkan!\n"
            )
        )

        layout = [
            [
                {
                    "text": "💸 Bayar Harga Normal",
                    "callback_data": f"paynow_{item_index}_normal_{price_val}",
                    "style": "green",
                    "emoji": client.ns.emoji.id("gem"),
                }
            ],
            [
                {
                    "text": "🎟️ Gunakan Kupon",
                    "callback_data": f"apply_coupon_{item_index}_normal_{price_val}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("ticket_admit"),
                },
                {
                    "text": "• Kembali ke Daftar VVIP •",
                    "callback_data": "list_vvip",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                },
            ],
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(desc, reply_markup=btn)
        return await callback_query.edit_message_text(desc, reply_markup=btn)

    text = f"{client.ns.emoji.cross_mark} Paket VVIP tidak ditemukan."
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^promo_detail_(.+)"),
    handler_type="callback",
)
async def promo_detail(client, callback_query):
    item_id = callback_query.matches[0].group(1)

    if item_id.isdigit():
        item_index = int(item_id)
    else:
        if not hasattr(ctx, "vip_list") or item_id not in ctx.vip_list:
            return await callback_query.answer(
                "Sesi kedaluwarsa, silakan muat ulang menu.",
                show_alert=True,
            )
        item_index = ctx.vip_list[item_id]

    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

    layout = [
        [
            {
                "text": "• Kembali ke Daftar VVIP •",
                "callback_data": "list_vvip",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]

    try:
        item = vvip_list[item_index]
    except IndexError:
        item = None

    if item and item.get("promo_price", 0) > 0:
        name = item.get("name")
        promo_price_val = item.get("promo_price", 0)
        promo_text = item.get("promo_text", "")
        formatted_promo = f"{promo_price_val:,}"

        desc = (
            promo_text.replace("{name}", name).replace(
                "{promo_price}", formatted_promo
            )
            if promo_text
            else (
                f"╭─ **{client.ns.emoji.party_popper} Penawaran Spesial Terbatas!**\n"
                f"│\n"
                f"├─ {client.ns.emoji.open_folder} **Nama Paket:** `{name}`\n"
                f"├─ {client.ns.emoji.pencil} **Deskripsi:** Jangan lewatkan kesempatan emas ini untuk bergabung dengan harga yang jauh lebih terjangkau!\n"
                f"│\n"
                f"├─ {client.ns.emoji.money_bag} **Harga Promo:** `Rp {formatted_promo}`\n"
                f"│\n"
                f"╰─ Segera amankan slot Anda sebelum promo berakhir!\n"
            )
        )

        layout = [
            [
                {
                    "text": "✅ Bayar Harga Promo",
                    "callback_data": f"paynow_{item_index}_promo_{promo_price_val}",
                    "style": "green",
                    "emoji": client.ns.emoji.id("white_check_mark"),
                }
            ],
            [
                {
                    "text": "🎟️ Gunakan Kupon",
                    "callback_data": f"apply_coupon_{item_index}_promo_{promo_price_val}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("ticket_admit"),
                },
                {
                    "text": "• Kembali ke Daftar VVIP •",
                    "callback_data": "list_vvip",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                },
            ],
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        if callback_query.message.photo:
            return await callback_query.edit_message_caption(desc, reply_markup=btn)
        return await callback_query.edit_message_text(desc, reply_markup=btn)

    text = f"{client.ns.emoji.cross_mark} Paket promo tidak ditemukan atau tidak aktif."
    btn = client.ns.telegram.button.build_button_grid(layout)

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^apply_coupon_(\\d+)_(normal|promo)_(\\d+)"),
    handler_type="callback",
)
async def apply_coupon_callback(client, callback_query):
    chat_id = callback_query.from_user.id
    match = callback_query.matches[0]
    item_index = int(match.group(1))
    tipe = match.group(2)
    original_amount = int(match.group(3))
    await callback_query.message.delete()

    try:
        ask_msg = await client.ask(
            chat_id,
            "Silakan masukkan kode kupon Anda.\n\nKetik `/batal` untuk membatalkan.",
            timeout=300,
        )

        if ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        coupon_code = ask_msg.text.upper()
        coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
        coupon = next(
            (c for c in coupons if c.get("code") == coupon_code),
            None,
        )

        if not coupon:
            raise ValueError(f"{client.ns.emoji.cross_mark} Kode kupon tidak valid.")

        if coupon.get("uses_left", 1) <= 0:
            raise ValueError(
                f"{client.ns.emoji.cross_mark} Kupon ini sudah habis digunakan."
            )

        expiry_str = coupon.get("expiry_date")
        coupon_expiry = parse_dt(expiry_str)
        if coupon_expiry and coupon_expiry < datetime.now(timezone.utc):
            raise ValueError(
                f"{client.ns.emoji.cross_mark} Kupon ini sudah kedaluwarsa."
            )

        discount_type = coupon["discount_type"]
        discount_value = coupon["discount_value"]

        if discount_type == "percentage":
            final_amount = original_amount - original_amount * (discount_value / 100)
        else:
            final_amount = original_amount - discount_value

        final_amount = max(1000, int(final_amount))

        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} Kupon `{coupon_code}` berhasil digunakan! Harga awal `Rp {original_amount:,}` menjadi `Rp {final_amount:,}`.",
        )
        await _create_payment_invoice(
            client,
            callback_query.from_user,
            item_index,
            tipe,
            final_amount,
            coupon_code,
        )

    except listen.UserCancelled:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.alarm_clock} **Waktu Habis**\nProses telah dibatalkan otomatis.",
        )
    except ValueError as e:
        await client.send_message(chat_id, str(e))
    except Exception as e:
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>{e}</pre>",
        )


@command(
    lambda ctx: filters.regex("^paynow_(\\d+)_(normal|promo)_(\\d+)"),
    handler_type="callback",
)
async def paynow(client, callback_query):
    match = callback_query.matches[0]
    item_index = int(match.group(1))
    tipe = match.group(2)
    amount = int(match.group(3))

    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text(
            f"{client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar."
        )

    await _create_payment_invoice(
        client,
        callback_query.from_user,
        item_index,
        tipe,
        amount,
    )


@command(
    lambda ctx: filters.regex("^renew_sub_(\\d+)"),
    handler_type="callback",
)
async def renew_subscription_callback(client, callback_query):
    item_index = int(callback_query.matches[0].group(1))
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

    try:
        item = vvip_list[item_index]
    except IndexError:
        return await callback_query.answer(
            "❌ Paket VVIP tidak ditemukan.",
            show_alert=True,
        )

    if item.get("promo_price", 0) > 0:
        callback_query.data = f"promo_detail_{item_index}"
        callback_query.matches = [re.match("promo_detail_(\\d+)", callback_query.data)]
        await promo_detail(client, callback_query)
    else:
        callback_query.data = f"notes_{item_index}"
        callback_query.matches = [re.match("notes_(\\d+)", callback_query.data)]
        await notes_data(client, callback_query)
