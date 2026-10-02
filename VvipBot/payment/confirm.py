import asyncio
from datetime import datetime, timedelta, timezone

import pyrogram
from pyrogram import filters

from .. import command, ctx, get_notification_target, is_bot_owner
from .verifier import verify_user_join, verify_user_join_multiple


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
    tipe = ref_parts[1] if len(ref_parts) > 1 else ("normal" if is_bundle_order else None)
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

    if is_bundle_order:
        if extra:
            bundle_indexes = [
                int(i) for i in extra.split(",") if i.strip().isdigit()
            ]
    else:
        item_index = int(ref_parts[0])
        coupon_code = extra or None

    try:
        is_owner_confirm = await is_bot_owner(client, user.id)
        is_paid = is_owner_confirm or await client.services.saweria.check_paid_status(
            transaction_id
        )

        if is_paid:
            await callback_query.edit_message_reply_markup(None)
            await ctx.db.removeVars(client.me.id, transaction_id)
            vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []

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

                if not invite_payloads:
                    raise ValueError(
                        "Tidak ada paket VIP valid untuk pembelian semua VIP."
                    )

                revenue_data = {
                    "user_id": user.id,
                    "username": user.username or user.first_name,
                    "amount": amount_raw,
                    "date": datetime.now(timezone.utc).isoformat(),
                    "item_name": " + ".join(purchased_names),
                    "type": "bundle",
                }

                await ctx.db.setListVars(
                    client.me.id,
                    "vip_revenue_history",
                    revenue_data,
                )

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
                            f"Berikut semua link akses VIP Anda:\n\n{link_text}\n\n"
                            f"{client.ns.emoji.md('exclamation')} Setiap link hanya berlaku 1 kali klik dan kedaluwarsa dalam 60 menit."
                        )
                    ),
                    protect_content=True,
                )

                try:
                    await callback_query.message.delete()
                except Exception:
                    pass

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
                    owner_bot_id = await get_notification_target(client)

                    bot_mention_str = client.ns.telegram.arg.getMention(client.me, md=True)
                    user_mention_str = client.ns.telegram.arg.getMention(user, md=True)

                    await client.send_rich_message(
                        owner_bot_id,
                        pyrogram.types.InputRichMessage(
                            markdown=(
                                f"{client.ns.emoji.md('money_bag')} **Pemasukan Baru!**\n\n"
                                f"**Pengguna:** {user_mention_str}\n"
                                f"**Bot:** {bot_mention_str}\n"
                                f"**Kategori:** `Semua VIP` (Bundle)"
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

                await ctx.db.updateListVars(
                    client.me.id, "coupons", _consume_coupon
                )

            await ctx.db.setListVars(client.me.id, "vvip_members", member_data)

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
                        f"Terima kasih, berikut adalah link akses Anda untuk paket **{name}**:\n\n{link}\n\n"
                        f"{client.ns.emoji.md('exclamation')} Link ini hanya berlaku untuk 1 kali klik dan akan kedaluwarsa dalam 60 menit jika tidak digunakan."
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
                owner_bot_id = await get_notification_target(client)

                user_mention_str = client.ns.telegram.arg.getMention(user, md=True)
                bot_mention_str = client.ns.telegram.arg.getMention(client.me, md=True)

                await client.send_rich_message(
                    owner_bot_id,
                    pyrogram.types.InputRichMessage(
                        markdown=(
                            f"{client.ns.emoji.md('money_bag')} **Pemasukan Baru!**\n\n"
                            f"**Pengguna:** {user_mention_str}\n"
                            f"**Bot:** {bot_mention_str}\n"
                            f"**Kategori:** `{name}` ({tipe.title()})"
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
