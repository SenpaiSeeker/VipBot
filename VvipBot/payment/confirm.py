import asyncio
from datetime import datetime, timedelta, timezone
from weakref import WeakValueDictionary
from zoneinfo import ZoneInfo

import pyrogram
from pyrogram import filters

from helpers import parse_dt
from helpers.income_template import render_income_template
from helpers.modules import Modules

from .. import get_member_lock, get_notification_target, get_sales_count, is_bot_owner
from .verifier import verify_user_join, verify_user_join_multiple

_TZ = ZoneInfo("Asia/Jakarta")
_confirm_locks = WeakValueDictionary()
_sales_lock = asyncio.Lock()


def _get_confirm_lock(bot_id, transaction_id):
    key = (bot_id, transaction_id)
    lock = _confirm_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _confirm_locks[key] = lock
    return lock


async def _handle_paid_sale(client, transaction_id, block_mode, route_sale_no=None):
    if block_mode:
        return None
    if not route_sale_no:
        marker_key = f"sale_route_{transaction_id}"
        route_sale_no = await client.db.getVars(client.me.id, marker_key)
    async with _sales_lock:
        count = await get_sales_count(client)
        await client.db.increment_sales_once(
            client.me.id,
            transaction_id,
            count + 1,
        )
    return route_sale_no


async def _preflight_chat(client, chat_id):
    try:
        await client.get_chat(chat_id)
    except Exception as e:
        raise ValueError(
            f"Bot tidak dapat mengakses grup `{chat_id}`. Pastikan bot masih "
            f"menjadi admin dan chat ID benar. ({e})"
        )


def _duration_days(value):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


async def _upsert_member(client, member_data, route_to_owner, transaction_id):
    lock = get_member_lock(client)
    async with lock:
        members = await client.db.getListVars(client.me.id, "vvip_members") or []
        user_id = str(member_data.get("user_id"))
        chat_id = str(member_data.get("chat_id_kick"))
        existing = next(
            (
                member
                for member in members
                if str(member.get("user_id")) == user_id
                and str(member.get("chat_id_kick")) == chat_id
            ),
            None,
        )
        now = datetime.now(timezone.utc)
        duration = _duration_days(member_data.get("duration", 0))

        if existing is None:
            new_member = dict(member_data)
            new_member.pop("duration", None)
            new_member["join_date"] = now.isoformat()
            new_member["last_transaction_id"] = transaction_id
            if route_to_owner:
                new_member["hidden"] = True
            if duration > 0:
                new_member["expiry_date"] = (now + timedelta(days=duration)).isoformat()
            else:
                new_member.pop("expiry_date", None)
            await client.db.setListVars(
                client.me.id,
                "vvip_members",
                new_member,
            )
            return

        updated = dict(existing)
        updated["vvip_name"] = member_data.get("vvip_name")
        updated["payment_type"] = member_data.get("payment_type")
        updated["last_transaction_id"] = transaction_id
        if route_to_owner:
            updated["hidden"] = True

        already_extended = str(existing.get("last_transaction_id")) == str(
            transaction_id
        )
        if not already_extended:
            old_expiry = parse_dt(updated.get("expiry_date"))
            base_date = old_expiry if old_expiry and old_expiry > now else now
            if duration > 0:
                updated["expiry_date"] = (
                    base_date + timedelta(days=duration)
                ).isoformat()
            else:
                updated.pop("expiry_date", None)

        async def update(member_list):
            return [
                (
                    updated
                    if str(member.get("user_id")) == user_id
                    and str(member.get("chat_id_kick")) == chat_id
                    else member
                )
                for member in member_list
            ]

        await client.db.updateListVars(
            client.me.id,
            "vvip_members",
            update,
        )


async def _record_revenue(client, transaction_id, revenue_data):
    async def update(history):
        if any(
            str(item.get("transaction_id")) == str(transaction_id) for item in history
        ):
            return None

        history.append({**revenue_data, "transaction_id": transaction_id})
        return history

    await client.db.updateListVars(
        client.me.id,
        "vip_revenue_history",
        update,
    )


async def _consume_coupon(client, transaction_id, coupon_code):
    if not coupon_code:
        return

    marker_key = f"coupon_used_{transaction_id}"
    if await client.db.getVars(client.me.id, marker_key):
        return

    coupon_consumed = {"found": False}
    expected_code = str(coupon_code).upper()

    async def update(coupons):
        new_coupons = []
        for coupon in coupons:
            coupon = dict(coupon)
            if (
                not coupon_consumed["found"]
                and str(coupon.get("code", "")).upper() == expected_code
            ):
                try:
                    uses_left = int(coupon.get("uses_left", 0) or 0)
                except (TypeError, ValueError):
                    uses_left = 0
                if uses_left > 0:
                    coupon["uses_left"] = uses_left - 1
                    coupon_consumed["found"] = True
            new_coupons.append(coupon)

        return new_coupons if coupon_consumed["found"] else None

    await client.db.updateListVars(client.me.id, "coupons", update)
    await client.db.setVars(client.me.id, marker_key, True)


async def _cleanup_order(client, transaction_id, route_sale_no):
    await client.db.removeVars(client.me.id, transaction_id)
    markers = [
        f"sale_counted_{transaction_id}",
        f"coupon_used_{transaction_id}",
        f"sale_route_{transaction_id}",
    ]

    for marker in markers:
        try:
            await client.db.removeVars(client.me.id, marker)
        except Exception:
            pass


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

    custom_template = await client.db.getVars(client.me.id, "income_text_template")
    if custom_template:
        return render_income_template(custom_template, values)

    paket_headers = [
        f"{emoji.md('gem')} NAMA VIP",
        f"{emoji.md('money_bag')} HARGA",
        f"{emoji.md('hourglass')} DURASI",
        f"{emoji.md('link')} CHAT ID",
    ]
    return (
        f"{section(f'{emoji.md('money_bag')} PEMASUKAN BARU')}\n\n"
        f"<details>\n"
        f"<summary><strong>DETAIL PEMASUKAN</strong></summary>\n\n"
        f"{section(f'{emoji.md('bell')} RINGKASAN TRANSAKSI')}\n\n"
        f"{table.md([h_info, h_ket], ringkasan_rows)}\n\n"
        f"{section(f'{emoji.md('bust_in_silhouette')} DATA PEMBELI')}\n\n"
        f"{table.md([h_info, h_ket], pembeli_rows)}\n\n"
        f"{section(f'{emoji.md('gem')} DETAIL PAKET VIP')}\n\n"
        f"{table.md(paket_headers, paket_rows)}\n\n"
        f"{section(f'{emoji.md('money_bag')} RINCIAN PEMBAYARAN')}\n\n"
        f"{table.md([h_info, h_ket], pembayaran_rows)}\n\n"
        f"{section(f'{emoji.md('robot')} INFO BOT')}\n\n"
        f"{table.md([h_info, h_ket], bot_rows)}\n\n"
        f"</details>"
    )


async def _confirm_payment(client, callback_query, transaction_id, user):
    table = client.ns.table
    ref_data_str = await client.db.getVars(client.me.id, transaction_id)

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
    coupon_code = None
    bundle_indexes = []
    snapshot_route = 0

    try:
        amount_raw = int(ref_parts[2]) if len(ref_parts) > 2 else 0
        if len(ref_parts) >= 5:
            buyer_id = int(ref_parts[3])
            extra = ref_parts[4]
        else:
            buyer_id = None
            extra = ref_parts[3] if len(ref_parts) > 3 else None
        if len(ref_parts) >= 6:
            snapshot_route = int(ref_parts[5] or 0)
        if not is_multi_order:
            item_index = int(ref_parts[0])
    except (TypeError, ValueError):
        return await callback_query.answer(
            "⚠️ Invoice ini tidak valid atau sudah kedaluwarsa.",
            show_alert=True,
        )

    if buyer_id and buyer_id != user.id:
        return await callback_query.answer(
            "⚠️ Invoice ini milik pengguna lain.",
            show_alert=True,
        )

    if buyer_id is None and not await is_bot_owner(client, user.id):
        return await callback_query.answer(
            "⚠️ Invoice ini tidak valid atau sudah kedaluwarsa.",
            show_alert=True,
        )

    if is_multi_order:
        if extra:
            bundle_indexes = [int(i) for i in extra.split(",") if i.strip().isdigit()]
    else:
        coupon_code = extra or None

    try:
        is_owner_confirm = await is_bot_owner(client, user.id)
        is_paid = (
            is_owner_confirm
            or await client.ns.payment.SaweriaScraper().check_paid_status(
                transaction_id,
                amount_raw or None,
            )
        )

        if is_paid:
            block_mode = bool(
                await client.db.getVars(client.me.id, "purchase_block") or False
            )
            route_sale_no = None
            if not block_mode:
                route_sale_no = snapshot_route or await client.db.getVars(
                    client.me.id,
                    f"sale_route_{transaction_id}",
                )
            route_to_owner = block_mode or bool(route_sale_no)
            await callback_query.edit_message_reply_markup(None)
            vvip_list = await client.db.getListVars(client.me.id, "list_vvip") or []

            if is_multi_order:
                selected_items = []
                seen_indexes = set()
                for idx in bundle_indexes:
                    if idx in seen_indexes:
                        continue
                    seen_indexes.add(idx)

                    try:
                        item_found = vvip_list[idx]
                    except (IndexError, TypeError):
                        raise ValueError("Paket VVIP tidak ditemukan di database.")

                    name = item_found.get("name")
                    target_chat_id = item_found.get("chat_id_normal")

                    if not target_chat_id:
                        raise ValueError(
                            f"Chat ID untuk paket {name or '-'} "
                            "belum diatur oleh admin."
                        )

                    selected_items.append((item_found, target_chat_id))

                if not selected_items:
                    raise ValueError(
                        "Tidak ada paket valid untuk pilihan Anda."
                        if is_pick_order
                        else "Tidak ada paket VIP valid untuk pembelian semua VIP."
                    )

                invite_payloads = []
                purchased_names = []
                bundle_orders = []
                checked_chats = set()

                for item_found, target_chat_id in selected_items:
                    name = item_found.get("name")
                    if target_chat_id not in checked_chats:
                        await _preflight_chat(client, target_chat_id)
                        checked_chats.add(target_chat_id)
                    expire_date_link = datetime.now() + timedelta(minutes=60)

                    invite_link_obj = await client.create_chat_invite_link(
                        chat_id=target_chat_id,
                        member_limit=1,
                        expire_date=expire_date_link,
                    )
                    link = invite_link_obj.invite_link

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

                for item_found, target_chat_id in selected_items:
                    member_data = {
                        "user_id": user.id,
                        "vvip_name": item_found.get("name"),
                        "join_date": datetime.now(timezone.utc).isoformat(),
                        "payment_type": "normal",
                        "chat_id_kick": target_chat_id,
                        "duration": item_found.get("duration", 0),
                    }

                    if route_to_owner:
                        member_data["hidden"] = True

                    await _upsert_member(
                        client,
                        member_data,
                        route_to_owner,
                        transaction_id,
                    )

                if is_pick_order:
                    for payload in invite_payloads:
                        rows = [
                            ["Status", "Pembayaran berhasil"],
                            ["Paket", f"**{payload.get('name')}**"],
                            ["Akses", "Berikut link akses Anda"],
                        ]
                        notice_rows = [
                            [
                                "Perhatian",
                                "Link hanya berlaku 1 kali klik dan kedaluwarsa "
                                "dalam 60 menit",
                            ]
                        ]
                        pick_link_msg = await client.send_rich_message(
                            user.id,
                            pyrogram.types.InputRichMessage(
                                markdown=(
                                    f"{client.ns.emoji.md('party_popper')} "
                                    "**Pembayaran "
                                    f"Paket {payload.get('name')} Berhasil!**\n\n"
                                    f"{table.md(['Info', 'Nilai'], rows)}\n\n"
                                    f"{payload.get('link')}\n\n"
                                    f"{table.md(['Info', 'Nilai'], notice_rows)}"
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

                    rows = [
                        ["Status", "Pembayaran berhasil"],
                        ["Akses", "Berikut semua link akses VIP Anda"],
                    ]
                    notice_rows = [
                        [
                            "Perhatian",
                            "Setiap link hanya berlaku 1 kali klik dan "
                            "kedaluwarsa dalam 60 menit",
                        ]
                    ]
                    link_msg = await client.send_rich_message(
                        user.id,
                        pyrogram.types.InputRichMessage(
                            markdown=(
                                f"{client.ns.emoji.md('party_popper')} **Pembayaran "
                                "Paket Semua VIP Berhasil!**\n\n"
                                f"{table.md(['Info', 'Nilai'], rows)}\n\n"
                                f"{link_text}\n\n"
                                f"{table.md(['Info', 'Nilai'], notice_rows)}"
                            )
                        ),
                        protect_content=True,
                    )

                await _handle_paid_sale(
                    client,
                    transaction_id,
                    block_mode,
                    route_sale_no,
                )
                if not route_to_owner:
                    revenue_data = {
                        "user_id": user.id,
                        "username": user.username or user.first_name,
                        "amount": amount_raw,
                        "date": datetime.now(timezone.utc).isoformat(),
                        "item_name": " + ".join(purchased_names),
                        "type": "pick" if is_pick_order else "bundle",
                    }

                    await _record_revenue(
                        client,
                        transaction_id,
                        revenue_data,
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

                try:
                    await callback_query.answer(
                        "✅ Pembayaran berhasil dikonfirmasi!", show_alert=False
                    )
                except Exception:
                    pass

                try:
                    if route_to_owner:
                        owner_bot_id = client.owner_id
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
                    client.log.print(f"Gagal mengirim notifikasi pemasukan: {e}")

                await _cleanup_order(client, transaction_id, route_sale_no)
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
                await _preflight_chat(client, target_chat_id)
                expire_date_link = datetime.now() + timedelta(minutes=60)

                invite_link_obj = await client.create_chat_invite_link(
                    chat_id=target_chat_id,
                    member_limit=1,
                    expire_date=expire_date_link,
                )
                link = invite_link_obj.invite_link

            except Exception as e:
                client.log.print(
                    f"Gagal membuat invite link untuk {target_chat_id}: {e}"
                )
                raise Exception("Gagal membuat link undangan.")

            member_data = {
                "user_id": user.id,
                "vvip_name": name,
                "join_date": datetime.now(timezone.utc).isoformat(),
                "payment_type": tipe,
                "chat_id_kick": target_chat_id,
                "duration": item_found.get("duration", 0),
            }

            if route_to_owner:
                member_data["hidden"] = True

            await _upsert_member(
                client,
                member_data,
                route_to_owner,
                transaction_id,
            )

            rows = [
                ["Status", "Pembayaran dikonfirmasi"],
                ["Paket", f"**{name}**"],
                ["Akses", "Berikut adalah link akses Anda"],
            ]
            notice_rows = [
                [
                    "Perhatian",
                    "Link ini hanya berlaku untuk 1 kali klik dan akan "
                    "kedaluwarsa dalam 60 menit jika tidak digunakan",
                ]
            ]
            link_msg = await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('party_popper')} **Pembayaran "
                        "Dikonfirmasi!**\n\n"
                        f"{table.md(['Info', 'Nilai'], rows)}\n\n"
                        f"{link}\n\n"
                        f"{table.md(['Info', 'Nilai'], notice_rows)}"
                    )
                ),
                protect_content=True,
            )

            await _handle_paid_sale(
                client,
                transaction_id,
                block_mode,
                route_sale_no,
            )
            await _consume_coupon(client, transaction_id, coupon_code)
            if not route_to_owner:
                revenue_data = {
                    "user_id": user.id,
                    "username": user.username or user.first_name,
                    "amount": amount_raw,
                    "date": datetime.now(timezone.utc).isoformat(),
                    "item_name": name,
                    "type": tipe,
                }

                await _record_revenue(
                    client,
                    transaction_id,
                    revenue_data,
                )

            try:
                await callback_query.message.delete()
            except Exception:
                pass

            asyncio.create_task(
                verify_user_join(client, user, target_chat_id, link_msg)
            )

            try:
                await callback_query.answer(
                    "✅ Pembayaran berhasil dikonfirmasi!", show_alert=False
                )
            except Exception:
                pass

            try:
                if route_to_owner:
                    owner_bot_id = client.owner_id
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
                client.log.print(f"Gagal mengirim notifikasi pemasukan: {e}")

            await _cleanup_order(client, transaction_id, route_sale_no)
        else:
            await callback_query.answer(
                "❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah "
                "beberapa saat.",
                show_alert=True,
            )
    except Exception as e:
        await callback_query.answer(
            f"**Terjadi Kesalahan**\n{e}",
            show_alert=True,
        )


async def manual_check_payment_callback(client, callback_query):
    transaction_id = callback_query.data.split(" ", 1)[1]
    user = callback_query.from_user
    lock = _get_confirm_lock(client.me.id, transaction_id)
    async with lock:
        await _confirm_payment(client, callback_query, transaction_id, user)


async def pre_checkout_handler(client, pre_checkout_query):
    await pre_checkout_query.answer(ok=True)


class PaymentConfirm(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^confirm_payment\\s(.+)"))(
            self.handle(manual_check_payment_callback)
        )
        self.client.on_pre_checkout_query()(self.handle(pre_checkout_handler))
