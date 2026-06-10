import asyncio
from datetime import datetime, timedelta, timezone
from time import time

from telethon import errors, events, functions

from helpers.saweria_message_generator import generate_safe_saweria_message
from VvipBot import command, ctx, is_bot_owner


async def is_participant(client, chat_id, user_id):
    try:
        permissions = await client.get_permissions(chat_id, user_id)
        return permissions.participant
    except errors.UserNotParticipantError:
        return False
    except Exception:
        return False


async def verify_user_join(client, user, chat_id, link_msg):
    verification_timeout = 3600
    start_time = time()
    is_joined = False

    while time() - start_time < verification_timeout:
        try:
            joined = await is_participant(client, chat_id, user.id)
            if joined:
                is_joined = True
                ctx.log.print(f"User {user.id} berhasil bergabung ke {chat_id}.")
                break
        except Exception:
            break
        await asyncio.sleep(15)

    try:
        await link_msg.delete()
    except Exception:
        pass

    if not is_joined:
        em = client.ns.emoji
        try:
            await client.send_message(
                user.id,
                f"{em.alarm_clock} Link undangan Anda telah kedaluwarsa karena tidak bergabung dalam 60 menit.",
                parse_mode="html",
            )
        except Exception:
            pass


async def verify_user_join_multiple(client, user, invite_payloads, link_msg):
    verification_timeout = 3600
    start_time = time()

    while time() - start_time < verification_timeout:
        pending_payloads = []
        for payload in invite_payloads:
            chat_id = payload.get("chat_id")
            try:
                joined = await is_participant(client, chat_id, user.id)
                if not joined:
                    pending_payloads.append(payload)
            except Exception:
                pending_payloads.append(payload)

        if not pending_payloads:
            try:
                await link_msg.delete()
            except Exception:
                pass
            return
        await asyncio.sleep(15)

    em = client.ns.emoji
    pending_lines = [
        f"• {item.get('name')}: {item.get('link')}" for item in pending_payloads
    ]

    try:
        await client.send_message(
            user.id,
            f"{em.alarm_clock} Anda belum join ke semua grup VIP dalam waktu 60 menit.\n\n"
            f"Silakan join grup berikut:\n" + "\n".join(pending_lines),
            parse_mode="html",
        )
    except Exception:
        pass


def _get_all_vvip_items(vvip_list):
    selected_items = []
    for index, item in enumerate(vvip_list):
        price = int(item.get("price", 0) or 0)
        chat_id_normal = item.get("chat_id_normal")
        if price > 0 and chat_id_normal:
            selected_items.append(
                {
                    "index": index,
                    "name": item.get("name", f"Paket {index + 1}"),
                    "price": price,
                    "chat_id": chat_id_normal,
                    "duration": item.get("duration", 0),
                }
            )
    return selected_items


async def _create_payment_invoice(
    client, user, item_index, tipe, amount, coupon_code=None
):
    em = client.ns.emoji
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    try:
        item = vvip_list[item_index]
        names = item.get("name")
    except IndexError:
        return await client.send_message(
            user.id,
            f"{em.cross_mark} Paket VVIP tidak ditemukan.",
            parse_mode="html",
        )

    saweria_user_id = await ctx.db.getVars(client.uid, "SAWERIA_USER_ID")
    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = (
                f"{em.anger} <b>Layanan Pembayaran Tidak Aktif</b>\n\n"
                f"Silakan atur API Key terlebih dahulu."
            )
            layout = [
                [
                    {
                        "text": "🔑 Atur Kunci API",
                        "callback_data": "api_settings",
                        "style": "primary",
                        "emoji": 5330115548900501467,
                    }
                ]
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(user.id, text, buttons=btn, parse_mode="html")
        else:
            await client.send_message(
                user.id,
                "Maaf, layanan pembayaran saat ini tidak tersedia.",
            )
        return

    msg = await client.send_message(
        user.id,
        f"{em.hourglass} <b>Sedang Memproses...</b>\nMohon tunggu sebentar.",
        parse_mode="html",
    )
    try:
        fakeinfo = client.ns.utils.faker.generate()
        random_message = generate_safe_saweria_message(fakeinfo.name)
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
        order_data = f"{item_index}|{tipe}|{amount_raw}"
        if coupon_code:
            order_data += f"|{coupon_code}"
        await ctx.db.setVars(client.uid, transaction_id, order_data)

        caption = (
            f"{em.white_check_mark} <b>Pembayaran Siap Dilakukan!</b>\n\n"
            f"Silakan scan QRIS di atas untuk membayar. Setelah itu, tekan tombol "
            f"<b>Konfirmasi Pembayaran</b>.\n\n"
            f"╭─ <b>Detail Tagihan</b>\n"
            f"│\n"
            f"├─ {em.shopping_bags} <b>Produk:</b> {names} ({tipe.title()})\n"
            f"├─ {em.money_bag} <b>Jumlah:</b> <code>Rp {int(amount_raw):,}</code>\n"
            f"├─ <b>Order ID:</b> "
            f'<a href="https://saweria.co/qris/{transaction_id}">{transaction_id}</a>\n'
            f"│\n"
            f"╰─ {em.down_pointing} <b>Jika sudah membayar, silakan klik tombol di bawah ini.</b>\n"
        )
        layout = [
            [
                {
                    "text": "✅ Konfirmasi Pembayaran",
                    "callback_data": f"confirm_payment {transaction_id}",
                    "style": "success",
                    "emoji": 5427009714745517609,
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await client.send_message(
            user.id, caption, file=qr_image_stream, buttons=btn, parse_mode="html"
        )
        await msg.delete()
    except Exception as e:
        await msg.edit(
            f"{em.cross_mark} <b>Terjadi Kesalahan</b>\n<pre>{e}</pre>",
            parse_mode="html",
        )


async def _create_all_vvip_payment_invoice(client, user, selected_items, total_amount):
    em = client.ns.emoji
    saweria_user_id = await ctx.db.getVars(client.uid, "SAWERIA_USER_ID")
    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = (
                f"{em.anger} <b>Layanan Pembayaran Tidak Aktif</b>\n\n"
                f"Silakan atur API Key terlebih dahulu."
            )
            layout = [
                [
                    {
                        "text": "🔑 Atur Kunci API",
                        "callback_data": "api_settings",
                        "style": "primary",
                        "emoji": 5330115548900501467,
                    }
                ]
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(user.id, text, buttons=btn, parse_mode="html")
        else:
            await client.send_message(
                user.id,
                "Maaf, layanan pembayaran saat ini tidak tersedia.",
            )
        return

    msg = await client.send_message(
        user.id,
        f"{em.hourglass} <b>Sedang Memproses...</b>\nMohon tunggu sebentar.",
        parse_mode="html",
    )
    try:
        fakeinfo = client.ns.utils.faker.generate()
        random_message = generate_safe_saweria_message(fakeinfo.name)
        (
            qr_string,
            transaction_id,
            qr_image_stream,
            amount_raw,
        ) = await client.services.saweria.create_payment(
            user_id=saweria_user_id,
            amount=int(total_amount),
            name=fakeinfo.name,
            email=fakeinfo.email,
            message=random_message,
            creator_name=client.me.username,
        )
        package_indexes = ",".join(str(item.get("index")) for item in selected_items)
        order_data = f"ALL|normal|{int(amount_raw)}|{package_indexes}"
        await ctx.db.setVars(client.uid, transaction_id, order_data)

        caption = (
            f"{em.white_check_mark} <b>Pembayaran Siap Dilakukan!</b>\n\n"
            f"Silakan scan QRIS di atas untuk membayar. Setelah itu, tekan tombol "
            f"<b>Konfirmasi Pembayaran</b>.\n\n"
            f"╭─ <b>Detail Tagihan</b>\n"
            f"│\n"
            f"├─ {em.shopping_bags} <b>Produk:</b> Semua VIP ({len(selected_items)} paket) (Bundle)\n"
            f"├─ {em.money_bag} <b>Jumlah:</b> <code>Rp {int(amount_raw):,}</code>\n"
            f"├─ <b>Order ID:</b> "
            f'<a href="https://saweria.co/qris/{transaction_id}">{transaction_id}</a>\n'
            f"│\n"
            f"╰─ {em.down_pointing} <b>Jika sudah membayar, silakan klik tombol di bawah ini.</b>\n"
        )
        layout = [
            [
                {
                    "text": "✅ Konfirmasi Pembayaran",
                    "callback_data": f"confirm_payment {transaction_id}",
                    "style": "success",
                    "emoji": 5427009714745517609,
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await client.send_message(
            user.id, caption, file=qr_image_stream, buttons=btn, parse_mode="html"
        )
        await msg.delete()
    except Exception as e:
        await msg.edit(
            f"{em.cross_mark} <b>Terjadi Kesalahan</b>\n<pre>{e}</pre>",
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^confirm_payment (.+)"))
async def manual_check_payment_callback(client, event):
    transaction_id = event.data.decode("utf-8").split(" ")[1]
    sender = await event.get_sender()
    em = client.ns.emoji
    ref_data_str = await ctx.db.getVars(client.uid, transaction_id)

    if not ref_data_str:
        return await event.answer(
            "💢 Invoice ini sudah tidak valid atau telah selesai.", alert=True
        )

    ref_parts = ref_data_str.split("|")
    is_bundle_order = ref_parts[0] == "ALL"
    tipe = ref_parts[1]
    amount_raw = int(ref_parts[2])
    coupon_code = None
    bundle_indexes = []

    if is_bundle_order:
        bundle_indexes = (
            [int(i) for i in ref_parts[3].split(",") if i.strip().isdigit()]
            if len(ref_parts) > 3
            else []
        )
    else:
        item_index = int(ref_parts[0])
        coupon_code = ref_parts[3] if len(ref_parts) > 3 else None

    try:
        is_owner_confirm = await is_bot_owner(client, sender.id)
        is_paid = is_owner_confirm or await client.services.saweria.check_paid_status(
            transaction_id
        )

        if is_paid:
            await event.edit(buttons=None)
            await ctx.db.removeVars(client.uid, transaction_id)
            vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []

            if is_bundle_order:
                invite_payloads = []
                purchased_names = []

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
                        expire_date_link = datetime.now(timezone.utc) + timedelta(
                            minutes=60
                        )
                        res = await client(
                            functions.messages.ExportChatInviteRequest(
                                peer=await client.get_input_entity(target_chat_id),
                                expire_date=expire_date_link,
                                usage_limit=1,
                            )
                        )
                        link = res.link
                    except Exception:
                        continue

                    member_data = {
                        "user_id": sender.id,
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

                    await ctx.db.setListVars(client.uid, "vvip_members", member_data)
                    purchased_names.append(name)
                    invite_payloads.append(
                        {"name": name, "chat_id": target_chat_id, "link": link}
                    )

                if not invite_payloads:
                    raise ValueError("Tidak ada paket VIP valid untuk pembelian.")

                revenue_data = {
                    "user_id": sender.id,
                    "username": sender.username or sender.first_name,
                    "amount": amount_raw,
                    "date": datetime.now(timezone.utc).isoformat(),
                    "item_name": " + ".join(purchased_names),
                    "type": "bundle",
                }
                await ctx.db.setListVars(
                    client.uid, "vip_revenue_history", revenue_data
                )

                links_text = "\n".join(
                    f"• {it['name']}: {it['link']}" for it in invite_payloads
                )
                link_msg = await client.send_message(
                    sender.id,
                    f"{em.party_popper} <b>Pembayaran Paket Semua VIP Berhasil!</b>\n\n"
                    f"Berikut semua link akses VIP Anda:\n\n{links_text}\n\n"
                    f"{em.alarm_clock} Setiap link hanya berlaku 1 kali klik dan kedaluwarsa dalam 60 menit.\n",
                    parse_mode="html",
                )
                await event.delete()
                asyncio.create_task(
                    verify_user_join_multiple(client, sender, invite_payloads, link_msg)
                )

                owner_bot_id = (
                    await ctx.db.getVars(client.uid, "owner_id") or ctx.owner_id
                )
                await client.send_message(
                    owner_bot_id,
                    f"{em.money_bag} <b>Pemasukan Baru!</b>\n\n"
                    f"<b>Pengguna:</b> {client.ns.telegram.arg.getMention(sender)}\n"
                    f"<b>Bot:</b> {client.me.first_name}\n"
                    f"<b>Kategori:</b> <code>Semua VIP</code> (Bundle)",
                    parse_mode="html",
                )
                return

            try:
                item_found = vvip_list[item_index]
                name = item_found.get("name")
            except IndexError:
                raise ValueError("Kategori VVIP tidak ditemukan.")

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
                expire_date_link = datetime.now(timezone.utc) + timedelta(minutes=60)
                res = await client(
                    functions.messages.ExportChatInviteRequest(
                        peer=await client.get_input_entity(target_chat_id),
                        expire_date=expire_date_link,
                        usage_limit=1,
                    )
                )
                link = res.link
            except Exception as e:
                raise Exception(f"Gagal membuat link undangan: {e}")

            member_data = {
                "user_id": sender.id,
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
                coupons = await ctx.db.getListVars(client.uid, "coupons") or []
                for c in coupons:
                    if c.get("code") == coupon_code:
                        c["uses_left"] = c.get("uses_left", 1) - 1
                        break
                await ctx.db.removeVars(client.uid, "coupons")
                for c in coupons:
                    await ctx.db.setListVars(client.uid, "coupons", c)

            await ctx.db.setListVars(client.uid, "vvip_members", member_data)
            revenue_data = {
                "user_id": sender.id,
                "username": sender.username or sender.first_name,
                "amount": amount_raw,
                "date": datetime.now(timezone.utc).isoformat(),
                "item_name": name,
                "type": tipe,
            }
            await ctx.db.setListVars(client.uid, "vip_revenue_history", revenue_data)

            link_msg = await client.send_message(
                sender.id,
                f"{em.party_popper} <b>Pembayaran Dikonfirmasi!</b>\n\n"
                f"Terima kasih, berikut adalah link akses Anda untuk paket <b>{name}</b>:\n\n"
                f"{link}\n\n"
                f"{em.alarm_clock} Link ini hanya berlaku untuk 1 kali klik dan akan kedaluwarsa "
                f"dalam 60 menit jika tidak digunakan.\n",
                parse_mode="html",
            )
            await event.delete()
            asyncio.create_task(
                verify_user_join(client, sender, target_chat_id, link_msg)
            )

            owner_bot_id = await ctx.db.getVars(client.uid, "owner_id") or ctx.owner_id
            await client.send_message(
                owner_bot_id,
                f"{em.money_bag} <b>Pemasukan Baru!</b>\n\n"
                f"<b>Pengguna:</b> {client.ns.telegram.arg.getMention(sender)}\n"
                f"<b>Bot:</b> {client.me.first_name}\n"
                f"<b>Kategori:</b> <code>{name}</code> ({tipe.title()})",
                parse_mode="html",
            )
        else:
            await event.answer(
                "❌ Pembayaran belum terdeteksi. Silakan coba lagi nanti.",
                alert=True,
            )
    except Exception as e:
        await event.answer(f"Error: {e}", alert=True)


@command(lambda ctx: events.CallbackQuery(pattern=b"^pay_all_vvip$"))
async def pay_all_vvip_callback(client, event):
    em = client.ns.emoji
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    selected_items = _get_all_vvip_items(vvip_list)

    if not selected_items:
        return await event.answer(
            "❌ Tidak ada paket VIP valid untuk pembelian.", alert=True
        )

    total_amount = sum(item.get("price", 0) for item in selected_items)
    await event.delete()
    sender = await event.get_sender()
    await _create_all_vvip_payment_invoice(client, sender, selected_items, total_amount)


@command(lambda ctx: events.CallbackQuery(pattern=b"^notes_(\\d+)"))
async def notes_data(client, event):
    item_index = int(event.data.decode("utf-8").split("_")[1])
    em = client.ns.emoji
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    layout = [[{"text": "◀️ Kembali ke Daftar VVIP", "callback_data": "list_vvip", "style": "primary", "emoji": 5373098009640836781}]]

    try:
        item = vvip_list[item_index]
    except IndexError:
        item = None

    if item:
        name = item.get("name")
        price_val = item.get("price", 0)
        normal_text = item.get("normal_text", "")
        desc = (
            normal_text.format(name=name, price=f"{price_val:,}")
            if normal_text
            else (
                f"╭─ {em.sparkles} <b>Detail Paket VVIP</b>\n"
                f"│\n"
                f"├─ {em.open_folder} <b>Nama Paket:</b> <code>{name}</code>\n"
                f"├─ <b>Deskripsi:</b> Dapatkan akses instan setelah pembayaran berhasil.\n"
                f"│\n"
                f"├─ {em.money_bag} <b>Harga Normal:</b> <code>Rp {price_val:,}</code>\n"
                f"│\n"
                f"╰─ Silakan klik tombol 'Bayar' di bawah untuk melanjutkan!\n"
            )
        )
        layout = [
            [
                {
                    "text": "💳 Bayar Harga Normal",
                    "callback_data": f"paynow_{item_index}_normal_{price_val}",
                    "style": "success",
                    "emoji": 5375296873982604963,
                }
            ],
            [
                {
                    "text": "🎟️ Gunakan Kupon",
                    "callback_data": f"apply_coupon_{item_index}_normal_{price_val}",
                    "style": "primary",
                    "emoji": 5418010521309815154,
                },
                {"text": "◀️ Kembali", "callback_data": "list_vvip", "style": "primary", "emoji": 5373098009640836781},
            ],
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await event.edit(desc, buttons=btn, parse_mode="html")
    else:
        btn = client.ns.telegram.button.build_button_grid(layout)
        await event.edit(
            f"{em.cross_mark} Paket VVIP tidak ditemukan.",
            buttons=btn,
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^promo_detail_(\\d+)"))
async def promo_detail(client, event):
    item_index = int(event.data.decode("utf-8").split("_")[2])
    em = client.ns.emoji
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    layout = [[{"text": "◀️ Kembali ke Daftar VVIP", "callback_data": "list_vvip", "style": "primary", "emoji": 5373098009640836781}]]

    try:
        item = vvip_list[item_index]
    except IndexError:
        item = None

    if item and item.get("promo_price", 0) > 0:
        name = item.get("name")
        promo_price_val = item.get("promo_price", 0)
        promo_text = item.get("promo_text", "")
        desc = (
            promo_text.format(name=name, promo_price=f"{promo_price_val:,}")
            if promo_text
            else (
                f"╭─ {em.party_popper} <b>Penawaran Spesial Terbatas!</b>\n"
                f"│\n"
                f"├─ {em.open_folder} <b>Nama Paket:</b> <code>{name}</code>\n"
                f"├─ <b>Deskripsi:</b> Bergabunglah dengan harga promo eksklusif.\n"
                f"│\n"
                f"├─ {em.money_bag} <b>Harga Promo:</b> <code>Rp {promo_price_val:,}</code>\n"
                f"│\n"
                f"╰─ Segera amankan slot Anda sebelum promo berakhir!\n"
            )
        )
        layout = [
            [
                {
                    "text": "💳 Bayar Harga Promo",
                    "callback_data": f"paynow_{item_index}_promo_{promo_price_val}",
                    "style": "success",
                    "emoji": 5427009714745517609,
                }
            ],
            [
                {
                    "text": "🎟️ Gunakan Kupon",
                    "callback_data": f"apply_coupon_{item_index}_promo_{promo_price_val}",
                    "style": "primary",
                    "emoji": 5418010521309815154,
                },
                {"text": "◀️ Kembali", "callback_data": "list_vvip", "style": "primary", "emoji": 5373098009640836781},
            ],
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await event.edit(desc, buttons=btn, parse_mode="html")
    else:
        btn = client.ns.telegram.button.build_button_grid(layout)
        await event.edit(
            f"{em.cross_mark} Paket promo tidak ditemukan atau tidak aktif.",
            buttons=btn,
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^apply_coupon_"))
async def apply_coupon_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji
    payload = event.data.decode("utf-8")
    parts = payload.split("_")
    item_index = int(parts[2])
    tipe = parts[3]
    original_amount = int(parts[4])

    await event.delete()
    try:
        ask_msg = await client.ask(
            sender.id,
            f"{em.ticket} Silakan masukkan kode kupon Anda.\n\nKetik <code>/batal</code> untuk membatalkan.",
            parse_mode="html",
        )
        coupon_code = ask_msg.text.strip().upper()
        coupons = await ctx.db.getListVars(client.uid, "coupons") or []
        coupon = next((c for c in coupons if c.get("code") == coupon_code), None)

        if not coupon:
            raise ValueError(f"{em.cross_mark} Kode kupon tidak valid.")
        if coupon.get("uses_left", 1) <= 0:
            raise ValueError(f"{em.cross_mark} Kupon ini sudah habis digunakan.")

        expiry_str = coupon.get("expiry_date")
        if expiry_str and datetime.fromisoformat(expiry_str) < datetime.now(
            timezone.utc
        ):
            raise ValueError(f"{em.cross_mark} Kupon ini sudah kedaluwarsa.")

        discount_type = coupon["discount_type"]
        discount_value = coupon["discount_value"]

        if discount_type == "percentage":
            final_amount = original_amount - original_amount * (discount_value / 100)
        else:
            final_amount = original_amount - discount_value

        final_amount = max(1000, int(final_amount))
        await client.send_message(
            sender.id,
            f"{em.white_check_mark} Kupon <code>{coupon_code}</code> berhasil digunakan! "
            f"Harga awal <code>Rp {original_amount:,}</code> menjadi <code>Rp {final_amount:,}</code>.",
            parse_mode="html",
        )
        await _create_payment_invoice(
            client, sender, item_index, tipe, final_amount, coupon_code
        )
    except client.userCancel:
        await client.send_message(
            sender.id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(sender.id, str(e), parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^paynow_"))
async def paynow(client, event):
    payload = event.data.decode("utf-8")
    parts = payload.split("_")
    item_index = int(parts[1])
    tipe = parts[2]
    amount = int(parts[3])

    await event.delete()
    sender = await event.get_sender()
    await _create_payment_invoice(client, sender, item_index, tipe, amount)


@command(lambda ctx: events.CallbackQuery(pattern=b"^renew_sub_(\\d+)"))
async def renew_subscription_callback(client, event):
    item_index = int(event.data.decode("utf-8").split("_")[2])
    em = client.ns.emoji
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    try:
        item = vvip_list[item_index]
    except IndexError:
        return await event.answer(
            "❌ Paket VVIP tidak ditemukan.", alert=True
        )

    if item.get("promo_price", 0) > 0:
        event.data = f"promo_detail_{item_index}".encode("utf-8")
        await promo_detail(client, event)
    else:
        event.data = f"notes_{item_index}".encode("utf-8")
        await notes_data(client, event)
