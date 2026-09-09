import asyncio
from datetime import datetime, timezone, timedelta
import pyrogram
from pyrogram import filters
from .. import command, ctx, is_bot_owner, get_notification_target
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
                        ctx.log.print(f"Gagal membuat invite link bundle untuk {target_chat_id}: {e}")
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
                        f"• {item.get('name')}: {item.get('link')}"
                        for item in invite_payloads
                    ]
                )
                
                link_msg = await client.send_message(
                    user.id,
                    f"{client.ns.emoji.party_popper} **Pembayaran Paket Semua VIP Berhasil!**\n\n"
                    f"Berikut semua link akses VIP Anda:\n\n{link_text}\n\n"
                    f"{client.ns.emoji.exclamation} Setiap link hanya berlaku 1 kali klik dan kedaluwarsa dalam 60 menit.\n",
                    protect_content=True,
                )
                await callback_query.message.delete()
                
                asyncio.create_task(
                    verify_user_join_multiple(
                        client,
                        user,
                        invite_payloads,
                        link_msg,
                    )
                )
                
                owner_bot_id = await get_notification_target(client)
                
                bot_mention_str = client.me.mention
                user_mention_str = client.ns.telegram.arg.getMention(user)
                
                await client.send_message(
                    owner_bot_id,
                    f"{client.ns.emoji.money_bag} **Pemasukan Baru!**\n\n"
                    f"**Pengguna:** {user_mention_str}\n"
                    f"**Bot:** {bot_mention_str}\n"
                    f"**Kategori:** `Semua VIP` (Bundle)",
                )
                return
                
            try:
                item_found = vvip_list[item_index]
                name = item_found.get("name")
            except IndexError:
                raise ValueError(
                    "Kategori VVIP tidak ditemukan di database."
                )
                
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
                raise Exception(
                    "Gagal membuat link undangan."
                )
                
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
                coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
                
                for c in coupons:
                    if c.get("code") == coupon_code:
                        c["uses_left"] = c.get("uses_left", 1) - 1
                        break
                        
                await ctx.db.removeVars(client.me.id, "coupons")
                
                for c in coupons:
                    await ctx.db.setListVars(client.me.id, "coupons", c)
                    
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
            
            link_msg = await client.send_message(
                user.id,
                f"{client.ns.emoji.party_popper} **Pembayaran Dikonfirmasi!**\n\n"
                f"Terima kasih, berikut adalah link akses Anda untuk paket **{name}**:\n\n{link}\n\n"
                f"{client.ns.emoji.exclamation} Link ini hanya berlaku untuk 1 kali klik dan akan kedaluwarsa dalam 60 menit jika tidak digunakan.\n",
                protect_content=True,
            )
            await callback_query.message.delete()
            
            asyncio.create_task(
                verify_user_join(client, user, target_chat_id, link_msg)
            )
            
            owner_bot_id = await get_notification_target(client)
            
            user_mention_str = client.ns.telegram.arg.getMention(user)
            bot_mention_str = client.me.mention
            
            await client.send_message(
                owner_bot_id,
                f"{client.ns.emoji.money_bag} **Pemasukan Baru!**\n\n"
                f"**Pengguna:** {user_mention_str}\n"
                f"**Bot:** {bot_mention_str}\n"
                f"**Kategori:** `{name}` ({tipe.title()})",
            )
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
