import uuid
from time import time
import pyrogram
from pyrogram import filters
from .. import command, ctx, get_notification_target


@command(lambda ctx: filters.successful_payment)
async def successful_donation_handler(client, message):
    if not message.successful_payment.invoice_payload.startswith("donation_"):
        return
        
    user = message.from_user
    stars_donated = message.successful_payment.total_amount
    charge_id = message.successful_payment.telegram_payment_charge_id
    current_bot_id = client.me.id
    super_admin_id = ctx.owner_id
    
    await client.send_message(
        chat_id=user.id,
        text=f"{client.ns.emoji.party_popper} **Terima Kasih Banyak, {user.first_name}!**\n\nKami telah menerima donasi Anda sebesar **{stars_donated} Stars ({client.ns.emoji.star})**.\nDukungan Anda adalah bahan bakar semangat bagi kami. Semoga hari Anda menyenangkan!",
    )
    
    owner_of_this_bot = await get_notification_target(client)
    main_bot_client = ctx.manager.main_bot_client
    
    try:
        user_mention_str = client.ns.telegram.arg.getMention(user)
        bot_mention_str = client.me.mention
        
        notification_text = (
            f"{client.ns.emoji.sparkles} **Donasi Baru Diterima!**\n\n"
            f"**Jumlah:** `{stars_donated}` Stars ({client.ns.emoji.star})\n"
            f"**Dari:** {user_mention_str} (`{user.id}`)\n"
            f"**Melalui Bot:** {bot_mention_str}"
        )
        
        refund_key = uuid.uuid4().hex[:16]
        refund_data = {
            "user_id": user.id,
            "charge_id": charge_id,
        }
        
        await ctx.db.setVars(
            current_bot_id,
            f"refund_{refund_key}",
            refund_data,
        )
        
        refund_callback_data = f"refund_stars_{refund_key}"
        layout = [
            [
                {
                    "text": "🔙 Kembalikan Donasi",
                    "callback_data": refund_callback_data,
                    "style": "red",
                    "emoji": client.ns.emoji.id("minus"),
                }
            ]
        ]
        refund_btn = client.ns.telegram.button.build_button_grid(layout)
        
        await client.send_message(
            chat_id=owner_of_this_bot,
            text=notification_text,
            reply_markup=refund_btn,
        )
        
    except pyrogram.errors.UserIsBlocked:
        if main_bot_client and owner_of_this_bot != super_admin_id:
            user_mention_str = client.ns.telegram.arg.getMention(user)
            
            await main_bot_client.send_message(
                super_admin_id,
                f"{client.ns.emoji.exclamation} **Notifikasi Gagal Terkirim**\n\n"
                f"Notifikasi donasi sebesar `{stars_donated}` Stars dari {user_mention_str} "
                f"gagal dikirim ke owner bot `{client.me.first_name}` karena bot diblokir olehnya.",
            )
            
    except Exception as e:
        ctx.log.print(f"Gagal mengirim notifikasi donasi: {e}")
