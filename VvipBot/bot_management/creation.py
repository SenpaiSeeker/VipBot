import asyncio
from datetime import datetime, timezone
import pyrogram
from pyrogram import filters
from helpers import listen
from .. import command, ctx


@command(
    lambda ctx: filters.regex("^start_creation_process$"),
    handler_type="callback",
)
async def start_creation_process_callback(client, callback_query):
    user_id = callback_query.from_user.id
    expiry_date_str = await ctx.db.getVars(user_id, "user_expiry_date")
    
    if not expiry_date_str or datetime.fromisoformat(expiry_date_str) < datetime.now(
        timezone.utc
    ):
        return await callback_query.answer(
            "Langganan Anda tidak valid atau telah berakhir.",
            show_alert=True,
        )

    all_bots_data = await ctx.db.getBots(is_token=True)
    
    if len(all_bots_data) >= 30:
        from config import BACKUP_BOT

        backup_text = f" melalui @{BACKUP_BOT}" if BACKUP_BOT else ""
        return await callback_query.answer(
            f"Kapasitas bot sudah penuh (30 Bot). Silakan buat bot baru{backup_text}.",
            show_alert=True,
        )

    await callback_query.message.delete()
    
    try:
        def ask(text):
            return client.ask(
                user_id,
                f"{text}\n\nKetik `/batal` untuk membatalkan.",
                timeout=600,
            )

        api_id_prompt = f"**{client.ns.emoji.lock} 1/3: Masukkan API ID Anda.**\nDapatkan dari my.telegram.org."
        api_id_msg = await ask(api_id_prompt)
        
        if api_id_msg.text.lower() == "/batal":
            raise listen.UserCancelled
            
        api_id = api_id_msg.text

        api_hash_prompt = f"**{client.ns.emoji.lock} 2/3: Masukkan API Hash Anda.**\nDapatkan dari my.telegram.org."
        api_hash_msg = await ask(api_hash_prompt)
        
        if api_hash_msg.text.lower() == "/batal":
            raise listen.UserCancelled
            
        api_hash = api_hash_msg.text

        token_prompt = f"**{client.ns.emoji.robot} 3/3: Masukkan Bot Token Anda.**\nDapatkan dari @BotFather."
        token_msg = await ask(token_prompt)
        
        if token_msg.text.lower() == "/batal":
            raise listen.UserCancelled
            
        token = token_msg.text

        msg = await client.send_message(
            user_id,
            f"{client.ns.emoji.mag} `Memverifikasi data & token...`",
        )
        
        new_bot_name = await client.ns.telegram.arg.getNamebot(token)
        
        if "invalid" in [new_bot_name]:
            raise ValueError("Token bot yang Anda masukkan tidak valid.")

        await msg.edit(
            f"{client.ns.emoji.white_check_mark} Bot '{new_bot_name.first_name}' valid dan sedang disimpan. "
            f"`{client.ns.emoji.rocket} Memulai bot...`"
        )
        
        new_bot_id = int(token.split(":", 1)[0])
        bot_data = {
            "name": str(new_bot_id),
            "api_id": api_id,
            "api_hash": api_hash,
            "bot_token": token,
        }
        
        await ctx.manager.start_bot(bot_data)
        
        await ctx.db.saveBot(
            new_bot_id,
            api_id,
            api_hash,
            token,
            is_token=True,
        )
        
        await ctx.db.setVars(
            new_bot_id,
            "bot_expiration_date",
            expiry_date_str,
        )
        
        await ctx.db.setVars(new_bot_id, "owner_id", user_id)
        await ctx.db.removeVars(user_id, "user_expiry_date")

        await msg.edit(
            f"{client.ns.emoji.party_popper} **Selamat!** Bot **{new_bot_name.first_name}** berhasil dibuat dan aktif."
        )
        
    except listen.UserCancelled:
        await client.send_message(
            user_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
        )
    except asyncio.TimeoutError:
        await client.send_message(
            user_id,
            f"{client.ns.emoji.alarm_clock} **Waktu Habis**\nProses telah dibatalkan otomatis.",
        )
    except Exception as e:
        await client.send_message(
            user_id,
            f"{client.ns.emoji.cross_mark} **Error Pembuatan Bot:** `{e}`",
        )
