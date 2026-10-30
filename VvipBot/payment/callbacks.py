from helpers.modules import Modules
import asyncio
import re
from datetime import datetime, timezone

import pyrogram
from pyrogram import filters

from helpers import parse_dt

from .. import get_bot_cache, listen
from .invoice import (
    _create_all_vvip_payment_invoice,
    _create_payment_invoice,
    _create_pick_vvip_payment_invoice,
    _package_price,
)
from .verifier import _get_all_vvip_items


def _build_pay_all_rows(selected_items):
    return [
        [item.get("name", "Paket"), f"Rp {int(item.get('price', 0)):,}"]
        for item in selected_items
    ]


async def pay_all_vvip_callback(client, callback_query):
    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []
    selected_items = _get_all_vvip_items(vvip_list)

    if not selected_items:
        return await callback_query.answer(
            "❌ Tidak ada paket VIP valid untuk pembelian semua VIP.",
            show_alert=True,
        )

    total_amount = sum((item.get("price", 0) for item in selected_items))

    table = client.ns.table
    rows = _build_pay_all_rows(selected_items)
    text = (
        f"{client.ns.emoji.md('shopping_cart')} **Ringkasan Ambil Semua VIP**\n\n"
        f"{table.md(['Paket', 'Harga'], rows)}\n\n"
        f"{client.ns.emoji.md('money_bag')} **Total: Rp {int(total_amount):,}** ({len(selected_items)} paket)"
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

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def pay_all_vvip_confirm_callback(client, callback_query):
    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []
    selected_items = _get_all_vvip_items(vvip_list)

    if not selected_items:
        return await callback_query.answer(
            "❌ Tidak ada paket VIP valid untuk pembelian semua VIP.",
            show_alert=True,
        )

    processing_msg = None
    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=_processing_text(client)
            )
        )
        processing_msg = callback_query.message

    total_amount = sum((item.get("price", 0) for item in selected_items))

    await _create_all_vvip_payment_invoice(
        client,
        callback_query.from_user,
        selected_items,
        total_amount,
        processing_msg=processing_msg,
    )


def _parse_pick_sel(sel_text):
    if not sel_text or sel_text == "-":
        return []
    return sorted({int(i) for i in str(sel_text).split(",") if i.strip().isdigit()})


def _pick_valid_indexes(vvip_list):
    return [
        i
        for i, item in enumerate(vvip_list)
        if int(item.get("price", 0) or 0) > 0 and item.get("chat_id_normal")
    ]


async def _render_pick_panel(client, callback_query, selected):
    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []
    valid_idx = _pick_valid_indexes(vvip_list)
    if not valid_idx:
        return await callback_query.answer(
            "❌ Tidak ada paket VIP valid.", show_alert=True
        )

    selected = [i for i in selected if i in valid_idx]
    sel_txt = ",".join(str(i) for i in selected) or "-"

    rows = []
    total = 0
    layout = []
    for i in valid_idx:
        item = vvip_list[i]
        name = item.get("name", f"Paket {i + 1}")
        price = int(item.get("price", 0) or 0)
        picked = i in selected
        if picked:
            total += price
        rows.append([name, f"Rp {price:,}", "✅ Dipilih" if picked else "⬜ Belum"])
        layout.append(
            [
                {
                    "text": f"{'✅ ' if picked else ''}{name}",
                    "callback_data": f"pick_vvip_toggle_{sel_txt}_{i}",
                    "style": "green" if picked else "blue",
                    "emoji": client.ns.emoji.id(
                        "white_check_mark" if picked else "shopping_bags"
                    ),
                }
            ]
        )

    count = len(selected)
    text = (
        f"{client.ns.emoji.md('shopping_bags')} **Pilih Paket VIP**\n\n"
        f"{client.ns.table.md(['Paket', 'Harga', 'Status'], rows)}\n\n"
        f"{client.ns.emoji.md('money_bag')} **Total: Rp {total:,}** ({count} paket)"
    )

    layout.append(
        [
            {
                "text": f"💳 Bayar ({count})",
                "callback_data": f"pick_vvip_pay_{sel_txt}",
                "style": "green",
                "emoji": client.ns.emoji.id("white_check_mark"),
            }
        ]
    )
    layout.append(
        [
            {
                "text": "• Kembali ke Daftar VVIP •",
                "callback_data": "list_vvip",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def pick_vvip_callback(client, callback_query):
    await _render_pick_panel(client, callback_query, [])


async def pick_vvip_toggle_callback(client, callback_query):
    sel_txt = callback_query.matches[0].group(1)
    idx = int(callback_query.matches[0].group(2))
    selected = _parse_pick_sel(sel_txt)
    if idx in selected:
        selected.remove(idx)
    else:
        selected.append(idx)
    await _render_pick_panel(client, callback_query, selected)


async def pick_vvip_pay_callback(client, callback_query):
    sel_txt = callback_query.matches[0].group(1)
    selected = _parse_pick_sel(sel_txt)
    if not selected:
        return await callback_query.answer(
            "❌ Pilih minimal 1 paket dulu.", show_alert=True
        )

    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []
    valid_idx = _pick_valid_indexes(vvip_list)
    selected = [i for i in selected if i in valid_idx]
    if not selected:
        return await callback_query.answer(
            "❌ Paket yang dipilih sudah tidak valid.", show_alert=True
        )

    selected_items = [
        {
            "index": i,
            "name": vvip_list[i].get("name", f"Paket {i + 1}"),
            "price": int(vvip_list[i].get("price", 0) or 0),
            "chat_id": vvip_list[i].get("chat_id_normal"),
            "duration": vvip_list[i].get("duration", 0),
        }
        for i in selected
    ]
    total_amount = sum(item.get("price", 0) for item in selected_items)

    processing_msg = None
    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=_processing_text(client)
            )
        )
        processing_msg = callback_query.message

    await _create_pick_vvip_payment_invoice(
        client,
        callback_query.from_user,
        selected_items,
        total_amount,
        processing_msg=processing_msg,
    )


def _processing_text(client) -> str:
    return (
        f"{client.ns.emoji.md('hourglass')} **Sedang Memproses**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Sedang memproses'], ['Keterangan', 'Mohon tunggu sebentar']])}"
    )


def _build_package_detail_table(client, emoji_name, title, rows, footer):
    table = client.ns.table
    rich = (
        f"{client.ns.emoji.md(emoji_name)} **{title}**\n\n"
        f"{table.md(['Info', 'Rincian'], rows)}\n\n{footer}"
    )
    return rich


async def notes_data(client, callback_query):
    item_id = callback_query.matches[0].group(1)

    if item_id.isdigit():
        item_index = int(item_id)
    else:
        vip_cache = get_bot_cache(client, "vip_list")
        if item_id not in vip_cache:
            return await callback_query.answer(
                "Sesi kedaluwarsa, silakan muat ulang menu.",
                show_alert=True,
            )
        item_index = vip_cache[item_id]

    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []

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
        default_rows = [
            ("Nama Paket", f"`{name}`"),
            (
                "Deskripsi",
                "Dapatkan akses instan ke konten premium dan eksklusif setelah pembayaran berhasil.",
            ),
            ("Harga Normal", f"`Rp {formatted_price}`"),
        ]
        default_footer = "Silakan klik tombol **Bayar** di bawah untuk melanjutkan!"
        rich_desc = _build_package_detail_table(
            client, "sparkles", "Detail Paket VVIP", default_rows, default_footer
        )

        desc = (
            normal_text.replace("{name}", name).replace("{price}", formatted_price)
            if normal_text
            else rich_desc
        )

        layout = [
            [
                {
                    "text": "💸 Bayar Harga Normal",
                    "callback_data": f"paynow_{item_index}_normal",
                    "style": "green",
                    "emoji": client.ns.emoji.id("gem"),
                }
            ],
            [
                {
                    "text": "🎟️ Gunakan Kupon",
                    "callback_data": f"apply_coupon_{item_index}_normal",
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

        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=desc),
            reply_markup=btn,
        )

    table = client.ns.table
    missing_rows = [
        ["Status", "Paket tidak ditemukan"],
        ["Aksi", "Kembali ke daftar VVIP"],
    ]
    text = (
        f"{client.ns.emoji.md('cross_mark')} **Paket VVIP Tidak Ditemukan**\n\n"
        f"{table.md(['Info', 'Nilai'], missing_rows)}"
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def promo_detail(client, callback_query):
    item_id = callback_query.matches[0].group(1)

    if item_id.isdigit():
        item_index = int(item_id)
    else:
        vip_cache = get_bot_cache(client, "vip_list")
        if item_id not in vip_cache:
            return await callback_query.answer(
                "Sesi kedaluwarsa, silakan muat ulang menu.",
                show_alert=True,
            )
        item_index = vip_cache[item_id]

    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []

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
        default_rows = [
            ("Nama Paket", f"`{name}`"),
            (
                "Deskripsi",
                "Jangan lewatkan kesempatan emas ini untuk bergabung dengan harga yang jauh lebih terjangkau!",
            ),
            ("Harga Promo", f"`Rp {formatted_promo}`"),
        ]
        default_footer = "Segera amankan slot Anda sebelum promo berakhir!"
        rich_desc = _build_package_detail_table(
            client,
            "party_popper",
            "Penawaran Spesial Terbatas!",
            default_rows,
            default_footer,
        )

        desc = (
            promo_text.replace("{name}", name).replace("{promo_price}", formatted_promo)
            if promo_text
            else rich_desc
        )

        layout = [
            [
                {
                    "text": "✅ Bayar Harga Promo",
                    "callback_data": f"paynow_{item_index}_promo",
                    "style": "green",
                    "emoji": client.ns.emoji.id("white_check_mark"),
                }
            ],
            [
                {
                    "text": "🎟️ Gunakan Kupon",
                    "callback_data": f"apply_coupon_{item_index}_promo",
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

        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=desc),
            reply_markup=btn,
        )

    text = (
        f"{client.ns.emoji.md('cross_mark')} **Paket Tidak Ditemukan**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Paket promo tidak ditemukan atau tidak aktif']])}"
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def apply_coupon_callback(client, callback_query):
    chat_id = callback_query.from_user.id
    match = callback_query.matches[0]
    item_index = int(match.group(1))
    tipe = match.group(2)

    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []
    try:
        package = vvip_list[item_index]
    except (IndexError, TypeError):
        return await callback_query.answer(
            "❌ Paket VVIP tidak ditemukan.",
            show_alert=True,
        )

    original_amount = _package_price(package, tipe)
    if original_amount <= 0:
        return await callback_query.answer(
            "❌ Harga paket belum diatur.",
            show_alert=True,
        )

    await callback_query.message.delete()

    try:
        ask_msg = await client.ask(
            chat_id,
            f"**Masukkan Kode Kupon**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Instruksi', 'Silakan masukkan kode kupon Anda'], ['Batal', 'Ketik `/batal` untuk membatalkan']])}",
            timeout=300,
        )

        if ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        coupon_code = ask_msg.text.upper()
        coupons = await client.db.getListVars(client.me.id, "coupons") or []
        coupon = next(
            (c for c in coupons if str(c.get("code", "")).upper() == coupon_code),
            None,
        )

        if not coupon:
            raise ValueError(
                f"{client.ns.emoji.md('cross_mark')} Kode kupon tidak valid."
            )

        try:
            uses_left = int(coupon.get("uses_left", 0) or 0)
        except (TypeError, ValueError):
            uses_left = 0

        if uses_left <= 0:
            raise ValueError(
                f"{client.ns.emoji.md('cross_mark')} Kupon ini sudah habis digunakan."
            )

        expiry_str = coupon.get("expiry_date")
        try:
            coupon_expiry = parse_dt(expiry_str)
        except (TypeError, ValueError):
            raise ValueError(
                f"{client.ns.emoji.md('cross_mark')} Tanggal kedaluwarsa kupon tidak valid."
            )

        if coupon_expiry and coupon_expiry < datetime.now(timezone.utc):
            raise ValueError(
                f"{client.ns.emoji.md('cross_mark')} Kupon ini sudah kedaluwarsa."
            )

        discount_type = coupon["discount_type"]
        discount_value = float(coupon["discount_value"])

        if discount_type == "percentage":
            final_amount = original_amount - original_amount * (discount_value / 100)
        else:
            final_amount = original_amount - discount_value

        final_amount = min(original_amount, max(1000, int(final_amount)))

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} Kupon `{coupon_code}` "
                    f"berhasil digunakan! Harga awal `Rp {original_amount:,}` "
                    f"menjadi `Rp {final_amount:,}`."
                )
            ),
        )
        await _create_payment_invoice(
            client,
            callback_query.from_user,
            item_index,
            tipe,
            coupon_code=coupon_code,
        )

    except listen.UserCancelled:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Proses Dibatalkan**"
            ),
        )
    except asyncio.TimeoutError:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('alarm_clock')} **Waktu Habis**\n"
                    f"Proses telah dibatalkan otomatis."
                )
            ),
        )
    except ValueError as e:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Kode Promo Tidak Valid**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal'], ['Error', f'`{e}`']])}"
                )
            ),
        )
    except Exception as e:
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Terjadi kesalahan'], ['Error', f'`{e}`']])}"
                )
            ),
        )


async def paynow(client, callback_query):
    match = callback_query.matches[0]
    item_index = int(match.group(1))
    tipe = match.group(2)

    processing_msg = None
    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=_processing_text(client)
            )
        )
        processing_msg = callback_query.message

    await _create_payment_invoice(
        client,
        callback_query.from_user,
        item_index,
        tipe,
        processing_msg=processing_msg,
    )


async def renew_subscription_callback(client, callback_query):
    item_index = int(callback_query.matches[0].group(1))
    vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []

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


class PaymentCallbacks(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^pay_all_vvip$"))(
            self.handle(pay_all_vvip_callback)
        )
        self.client.on_callback_query(filters.regex("^pay_all_vvip_confirm$"))(
            self.handle(pay_all_vvip_confirm_callback)
        )
        self.client.on_callback_query(filters.regex("^pick_vvip$"))(
            self.handle(pick_vvip_callback)
        )
        self.client.on_callback_query(filters.regex("^pick_vvip_toggle_(.+?)_(\\d+)$"))(
            self.handle(pick_vvip_toggle_callback)
        )
        self.client.on_callback_query(filters.regex("^pick_vvip_pay_(.+)$"))(
            self.handle(pick_vvip_pay_callback)
        )
        self.client.on_callback_query(filters.regex("^notes_(.+)"))(
            self.handle(notes_data)
        )
        self.client.on_callback_query(filters.regex("^promo_detail_(.+)"))(
            self.handle(promo_detail)
        )
        self.client.on_callback_query(
            filters.regex("^apply_coupon_(\\d+)_(normal|promo)(?:_\\d+)?$")
        )(self.handle(apply_coupon_callback))
        self.client.on_callback_query(
            filters.regex("^paynow_(\\d+)_(normal|promo)(?:_\\d+)?$")
        )(self.handle(paynow))
        self.client.on_callback_query(filters.regex("^renew_sub_(\\d+)"))(
            self.handle(renew_subscription_callback)
        )
