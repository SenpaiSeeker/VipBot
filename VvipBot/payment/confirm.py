import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pyrogram
from pyrogram import filters

from helpers.income_template import render_income_template

from .. import command, ctx, get_notification_target, is_bot_owner
from .verifier import verify_user_join, verify_user_join_multiple

_TZ = ZoneInfo("Asia/Jakarta")


def _format_rupiah(value) -> str:
    try:
        return f"Rp {int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


def _format_duration(days) -> str:
    try:
        days = int(days or 0)
    except (TypeError, ValueError):
        days = 0
    if days <= 0:
        return "Permanen"
    return f"{days} hari"


def _format_waktu(value=None) -> str:
    dt = value or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ).strftime("%d-%m-%Y %H:%M:%S WIB")


async def _build_income_notification(
    client,
    user,
    orders,
    amount_raw,
    transaction_id,
    tipe,
    coupon_code=None,
):
    emoji = client.ns.emoji
    table = client.ns.table
    user_mention = client.ns.telegram.arg.getMention(user, md=True)
    bot_mention = client.ns.telegram.arg.getMention(client.me, md=True)

    subtotal = sum(int(o.get("price", 0) or 0) for o in orders)
    total = int(amount_raw or 0)
    diskon = max(subtotal - total, 0)
    tipe_label = {
        "normal": "Normal",
        "promo": "Promo",
        "bundle": "Bundle (Semua VIP)",
        "pick": "Pilihan Sendiri",
    }.get(tipe, str(tipe or "-").title())

    def section(title):
        return table.md([title], [])

    ringkasan_rows = [
        [f"{emoji.md('notes')} **ORDER ID**", f"`{transaction_id}`"],
        [f"{emoji.md('white_check_mark')} **STATUS**", "Lunas"],
        [f"{emoji.md('pencil')} **TIPE**", tipe_label],
        [f"{emoji.md('toolbox')} **JUMLAH PAKET**", f"`{len(orders)}`"],
    ]

    pembeli_rows = [
        [f"{emoji.md('bust_in_silhouette')} **NAMA**", user_mention],
        [f"{emoji.md('id_card')} **USER ID**", f"`{user.id}`"],
        [
            f"{emoji.md('alien')} **USERNAME**",
            f"`@{user.username}`" if user.username else "Tidak ada",
        ],
    ]

    paket_rows = [
        [
            f"**{order.get('name', '-')}**",
            _format_rupiah(order.get("price", 0)),
            _format_duration(order.get("duration", 0)),
            f"`{order.get('chat_id', '-')}`",
        ]
        for order in orders
    ]

    pembayaran_rows = [
        [f"{emoji.md('money_bag')} **SUBTOTAL**", _format_rupiah(subtotal)],
    ]
    if diskon > 0:
        pembayaran_rows.append(
            [
                f"{emoji.md('ticket')} **DISKON KUPON**",
                f"`{coupon_code or 'Tanpa Kupon'}` → {_format_rupiah(diskon)}",
            ]
        )
    pembayaran_rows.extend(
        [
            [f"{emoji.md('gem')} **TOTAL BAYAR**", f"**{_format_rupiah(total)}**"],
            [f"{emoji.md('shopping_cart')} **METODE**", "QRIS (Saweria)"],
            [f"{emoji.md('hourglass')} **WAKTU**", _format_waktu()],
        ]
    )

    bot_rows = [
        [f"{emoji.md('robot')} **BOT**", bot_mention],
        [f"{emoji.md('link')} **USERNAME**", f"`@{client.me.username}`"],
        [f"{emoji.md('chart_up')} **ITEM TERJUAL**", f"`{len(orders)}`"],
    ]

    h_info = f"{emoji.md('open_folder')} INFO"
    h_ket = f"{emoji.md('open_book')} KETERANGAN"

    first_order = orders[0] if orders else {}
    item_names = " + ".join(str(o.get("name", "-")) for o in orders) or "-"
    item_list = (
        "\n".join(
            f"{emoji.md('gem')} **{o.get('name', '-')}** — "
            f"{_format_rupiah(o.get('price', 0))} — "
            f"{_format_duration(o.get('duration', 0))} "
            f"(Chat ID: `{o.get('chat_id', '-')}`)"
            for o in orders
        )
        or "-"
    )
    item_table = (
        table.md(
            [
                f"{emoji.md('gem')} NAMA VIP",
                f"{emoji.md('money_bag')} HARGA",
                f"{emoji.md('hourglass')} DURASI",
                f"{emoji.md('link')} CHAT ID",
            ],
            paket_rows,
        )
        if paket_rows
        else "-"
    )

    values = {
        "mention": user_mention,
        "buyer_name": f"{user.first_name or ''} {user.last_name or ''}".strip() or "-",
        "buyer_id": user.id,
        "buyer_username": f"@{user.username}" if user.username else "Tidak ada",
        "order_id": transaction_id,
        "status": "Lunas",
        "type": tipe_label,
        "quantity": len(orders),
        "item_name": item_names,
        "item_price": _format_rupiah(first_order.get("price", 0)),
        "item_duration": _format_duration(first_order.get("duration", 0)),
        "item_chat_id": first_order.get("chat_id", "-"),
        "item_list": item_list,
        "item_table": item_table,
        "subtotal": _format_rupiah(subtotal),
        "discount": _format_rupiah(diskon),
        "coupon": coupon_code or "Tanpa Kupon",
        "total": _format_rupiah(total),
        "method": "QRIS (Saweria)",
        "time": _format_waktu(),
        "bot_name": client.me.first_name or "-",
        "bot_username": f"@{client.me.username}" if client.me.username else "-",
        "bot_mention": bot_mention,
        "sold_count": len(orders),
    }

    custom_template = await ctx.db.getVars(client.me.id, "income_text_template")
    if custom_template:
        return render_income_template(custom_template, values)

    return (
        f"{section(f'{emoji.md('money_bag')} PEMASUKAN BARU')}\n\n"
        f"<details>\n"
        f"<summary><strong>DETAIL PEMASUKAN</strong></summary>\n\n"
        f"{section(f'{emoji.md('bell')} RINGKASAN TRANSAKSI')}\n\n"
        f"{table.md([h_info, h_ket], ringkasan_rows)}\n\n"
        f"{section(f'{emoji.md('bust_in_silhouette')} DATA PEMBELI')}\n\n"
        f"{table.md([h_info, h_ket], pembeli_rows)}\n\n"
        f"{section(f'{emoji.md('gem')} DETAIL PAKET VIP')}\n\n"
        f"{table.md([f'{emoji.md('gem')} NAMA VIP', f'{emoji.md('money_bag')} HARGA', f'{emoji.md('hourglass')} DURASI', f'{emoji.md('link')} CHAT ID'], paket_rows)}\n\n"
        f"{section(f'{emoji.md('money_bag')} RINCIAN PEMBAYARAN')}\n\n"
        f"{table.md([h_info, h_ket], pembayaran_rows)}\n\n"
        f"{section(f'{emoji.md('robot')} INFO BOT')}\n\n"
        f"{table.md([h_info, h_ket], bot_rows)}\n\n"
        f"</details>"
    )


@command(
    lambda ctx: filters.regex("^confirm_payment\\s(.+)"),
    handler_type="callback",
)
async def manual_check_payment_callback(client, callback_query):
    transaction_id = callback_query.data.split(" ", 1)[1]
    user = callback_query.from_user
    ref_data_str = await ctx.db.getVars(client.me.id, transaction_id)

    if not ref_data_str:
        return await callback_query.answer(
            "⚠️ Invoice ini sudah tidak valid atau telah selesai.", show_alert=True
        )

    ref_parts = ref_data_str.split("|")
    is_bundle_order = ref_parts[0] == "ALL"
    is_pick_order = ref_parts[0] == "PICK"
    is_multi_order = is_bundle_order or is_pick_order
    tipe = (
        ref_parts[1] if len(ref_parts) > 1 else ("normal" if is_multi_order else None)
    )
    amount_raw = int(ref_parts[2]) if len(ref_parts) > 2 else 0
    coupon_code = None
    bundle_indexes = []

    if len(ref_parts) >= 5:
        buyer_id = int(ref_parts[3])
        extra = ref_parts[4]
    else:
        buyer_id = None
        extra = ref_parts[3] if len(ref_parts) > 3 else None

    if buyer_id and buyer_id != user.id:
        return await callback_query.answer(
            "⚠️ Invoice ini milik pengguna lain.",
            show_alert=True,
        )

    if is_multi_order:
        if extra:
            bundle_indexes = [int(i) for i in extra.split(",") if i.strip().isdigit()]
    else:
        item_index = int(ref_parts[0])
        coupon_code = extra or None

    try:
        is_owner_confirm = await is_bot_owner(client, user.id)
        is_paid = is_owner_confirm or await client.services.saweria.check_paid_status(
            transaction_id
        )

        if is_paid:
            block_mode = bool(
                await ctx.db.getVars(client.me.id, "purchase_block") or False
            )
            await callback_query.edit_message_reply_markup(None)
            await ctx.db.removeVars(client.me.id, transaction_id)
            vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

            if is_multi_order:
                invite_payloads = []
                purchased_names = []
                bundle_orders = []

                for idx in bundle_indexes:
                    try:
                        item_found = vvip_list[idx]
                    except IndexError:
                        continue

                    name = item_found.get("name")
                    target_chat_id = item_found.get("chat_id_normal")

                    if not target_chat_id:
                        continue

                    try:
                        expire_date_link = datetime.now() + timedelta(minutes=60)

                        invite_link_obj = await client.create_chat_invite_link(
                            chat_id=target_chat_id,
                            member_limit=1,
                            expire_date=expire_date_link,
                        )
                        link = invite_link_obj.invite_link

                    except Exception as e:
                        ctx.log.print(
                            f"Gagal membuat invite link bundle untuk {target_chat_id}: {e}"
                        )
                        continue

                    member_data = {
                        "user_id": user.id,
                        "vvip_name": name,
                        "join_date": datetime.now(timezone.utc).isoformat(),
                        "payment_type": "normal",
                        "chat_id_kick": target_chat_id,
                    }

                    duration = item_found.get("duration", 0)
                    if duration > 0:
                        expiry_date = datetime.now(timezone.utc) + timedelta(
                            days=duration
                        )
                        member_data["expiry_date"] = expiry_date.isoformat()

                    await ctx.db.setListVars(
                        client.me.id,
                        "vvip_members",
                        member_data,
                    )
                    purchased_names.append(name)

                    invite_payloads.append(
                        {
                            "name": name,
                            "chat_id": target_chat_id,
                            "link": link,
                        }
                    )

                    bundle_orders.append(
                        {
                            "name": name,
                            "price": item_found.get("price", 0),
                            "duration": item_found.get("duration", 0),
                            "chat_id": target_chat_id,
                        }
                    )

                if not invite_payloads:
                    raise ValueError(
                        "Tidak ada paket valid untuk pilihan Anda."
                        if is_pick_order
                        else "Tidak ada paket VIP valid untuk pembelian semua VIP."
                    )

                if not block_mode:
                    revenue_data = {
                        "user_id": user.id,
                        "username": user.username or user.first_name,
                        "amount": amount_raw,
                        "date": datetime.now(timezone.utc).isoformat(),
                        "item_name": " + ".join(purchased_names),
                        "type": "pick" if is_pick_order else "bundle",
                    }

                    await ctx.db.setListVars(
                        client.me.id,
                        "vip_revenue_history",
                        revenue_data,
                    )

                if is_pick_order:
                    for payload in invite_payloads:
                        pick_link_msg = await client.send_rich_message(
                            user.id,
                            pyrogram.types.InputRichMessage(
                                markdown=(
                                    f"{client.ns.emoji.md('party_popper')} **Pembayaran Paket {payload.get('name')} Berhasil!**\n\n"
                                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Pembayaran berhasil'], ['Paket', f"**{payload.get('name')}**"], ['Akses', 'Berikut link akses Anda']])}\n\n"
                                    f"{payload.get('link')}\n\n"
                                    f"{client.ns.table.md(['Info', 'Nilai'], [['Perhatian', 'Link hanya berlaku 1 kali klik dan kedaluwarsa dalam 60 menit']])}"
                                )
                            ),
                            protect_content=True,
                        )
                        asyncio.create_task(
                            verify_user_join(
                                client,
                                user,
                                payload.get("chat_id"),
                                pick_link_msg,
                            )
                        )
                else:
                    link_text = "\n".join(
                        [
                            f"- {item.get('name')}: {item.get('link')}"
                            for item in invite_payloads
                        ]
                    )

                    link_msg = await client.send_rich_message(
                        user.id,
                        pyrogram.types.InputRichMessage(
                            markdown=(
                                f"{client.ns.emoji.md('party_popper')} **Pembayaran Paket Semua VIP Berhasil!**\n\n"
                                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Pembayaran berhasil'], ['Akses', 'Berikut semua link akses VIP Anda']])}\n\n"
                                f"{link_text}\n\n"
                                f"{client.ns.table.md(['Info', 'Nilai'], [['Perhatian', 'Setiap link hanya berlaku 1 kali klik dan kedaluwarsa dalam 60 menit']])}"
                            )
                        ),
                        protect_content=True,
                    )

                try:
                    await callback_query.message.delete()
                except Exception:
                    pass

                if not is_pick_order:
                    asyncio.create_task(
                        verify_user_join_multiple(
                            client,
                            user,
                            invite_payloads,
                            link_msg,
                        )
                    )

                await callback_query.answer(
                    "✅ Pembayaran berhasil dikonfirmasi!", show_alert=False
                )

                try:
                    if block_mode:
                        owner_bot_id = ctx.owner_id
                    else:
                        owner_bot_id = await get_notification_target(client)

                    await client.send_rich_message(
                        owner_bot_id,
                        pyrogram.types.InputRichMessage(
                            markdown=await _build_income_notification(
                                client=client,
                                user=user,
                                orders=bundle_orders,
                                amount_raw=amount_raw,
                                transaction_id=transaction_id,
                                tipe="pick" if is_pick_order else "bundle",
                                coupon_code=coupon_code,
                            )
                        ),
                    )
                except Exception as e:
                    ctx.log.print(f"Gagal mengirim notifikasi pemasukan: {e}")

                return

            try:
                item_found = vvip_list[item_index]
                name = item_found.get("name")
            except IndexError:
                raise ValueError("Kategori VVIP tidak ditemukan di database.")

            is_promo = tipe == "promo"
            target_chat_id = (
                item_found.get("chat_id_promo")
                if is_promo
                else item_found.get("chat_id_normal")
            )

            if not target_chat_id:
                raise ValueError(
                    "Chat ID untuk paket VVIP ini belum diatur oleh admin."
                )

            try:
                expire_date_link = datetime.now() + timedelta(minutes=60)

                invite_link_obj = await client.create_chat_invite_link(
                    chat_id=target_chat_id,
                    member_limit=1,
                    expire_date=expire_date_link,
                )
                link = invite_link_obj.invite_link

            except Exception as e:
                ctx.log.print(f"Gagal membuat invite link untuk {target_chat_id}: {e}")
                raise Exception("Gagal membuat link undangan.")

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
                coupon_consumed = {"found": False}

                async def _consume_coupon(coupons):
                    new_coupons = []
                    for c in coupons:
                        c = dict(c)
                        if c.get("code") == coupon_code:
                            c["uses_left"] = max(int(c.get("uses_left", 1)) - 1, 0)
                            coupon_consumed["found"] = True
                        new_coupons.append(c)
                    return new_coupons if coupon_consumed["found"] else None

                await ctx.db.updateListVars(client.me.id, "coupons", _consume_coupon)

            await ctx.db.setListVars(client.me.id, "vvip_members", member_data)

            if not block_mode:
                revenue_data = {
                    "user_id": user.id,
                    "username": user.username or user.first_name,
                    "amount": amount_raw,
                    "date": datetime.now(timezone.utc).isoformat(),
                    "item_name": name,
                    "type": tipe,
                }

                await ctx.db.setListVars(
                    client.me.id,
                    "vip_revenue_history",
                    revenue_data,
                )

            link_msg = await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('party_popper')} **Pembayaran Dikonfirmasi!**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Pembayaran dikonfirmasi'], ['Paket', f'**{name}**'], ['Akses', 'Berikut adalah link akses Anda']])}\n\n"
                        f"{link}\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Perhatian', 'Link ini hanya berlaku untuk 1 kali klik dan akan kedaluwarsa dalam 60 menit jika tidak digunakan']])}"
                    )
                ),
                protect_content=True,
            )

            try:
                await callback_query.message.delete()
            except Exception:
                pass

            asyncio.create_task(
                verify_user_join(client, user, target_chat_id, link_msg)
            )

            await callback_query.answer(
                "✅ Pembayaran berhasil dikonfirmasi!", show_alert=False
            )

            try:
                if block_mode:
                    owner_bot_id = ctx.owner_id
                else:
                    owner_bot_id = await get_notification_target(client)

                unit_price = item_found.get("promo_price" if is_promo else "price", 0)
                single_order = {
                    "name": name,
                    "price": unit_price or amount_raw,
                    "duration": item_found.get("duration", 0),
                    "chat_id": target_chat_id,
                }

                await client.send_rich_message(
                    owner_bot_id,
                    pyrogram.types.InputRichMessage(
                        markdown=await _build_income_notification(
                            client=client,
                            user=user,
                            orders=[single_order],
                            amount_raw=amount_raw,
                            transaction_id=transaction_id,
                            tipe=tipe,
                            coupon_code=coupon_code,
                        )
                    ),
                )
            except Exception as e:
                ctx.log.print(f"Gagal mengirim notifikasi pemasukan: {e}")
        else:
            await callback_query.answer(
                "❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah beberapa saat.",
                show_alert=True,
            )
    except Exception as e:
        await callback_query.answer(
            f"**Terjadi Kesalahan**\n{e}",
            show_alert=True,
        )


@command(
    lambda ctx: filters.PreCheckoutQuery,
    handler_type="pre_checkout",
)
async def pre_checkout_handler(client, pre_checkout_query):
    await pre_checkout_query.answer(ok=True)
