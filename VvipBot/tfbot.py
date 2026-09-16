from . import command, ctx, filters


@command(lambda ctx: filters.command("tfbot") & filters.user(ctx.owner_id))
async def tfbot_command_handler(client, message):
    args = message.command
    if len(args) != 4:
        return await message.reply_text(
            "Format salah. Gunakan: `/tfbot <id_bot> <source_db> <target_db>`\nContoh: `/tfbot 123456789 vvip_database vvip_databaseV2`"
        )
    try:
        bot_id = int(args[1])
    except ValueError:
        return await message.reply_text("ID Bot harus berupa angka.")
    source_db_name = args[2]
    target_db_name = args[3]
    msg = await message.reply_text(f"{client.ns.emoji.repeat} Memproses migrasi bot...")
    try:
        from helpers.database import DataBase

        source_db = (
            ctx.db
            if source_db_name == ctx.db.file_name
            else DataBase(
                storage_type=ctx.db.storage_type,
                file_name=source_db_name,
                keys_encrypt=ctx.db.keys_encrypt,
                method_encrypt=ctx.db.method_encrypt,
                auto_backup=False,
            )
        )
        target_db = (
            ctx.db
            if target_db_name == ctx.db.file_name
            else DataBase(
                storage_type=ctx.db.storage_type,
                file_name=target_db_name,
                keys_encrypt=ctx.db.keys_encrypt,
                method_encrypt=ctx.db.method_encrypt,
                auto_backup=False,
            )
        )
        bots_token = await source_db.getBots(is_token=True)
        bots_session = await source_db.getBots(is_token=False)
        all_bots = bots_token + bots_session
        bot_data = next((b for b in all_bots if str(b["name"]) == str(bot_id)), None)
        if not bot_data:
            if source_db != ctx.db:
                await source_db.close_async()
            if target_db != ctx.db:
                await target_db.close_async()
            return await msg.edit_text(
                f"{client.ns.emoji.cross_mark} Bot dengan ID `{bot_id}` tidak ditemukan di `{source_db_name}`."
            )
        source_vars = await source_db._get_user_vars(bot_id)
        api_id = bot_data.get("api_id")
        api_hash = bot_data.get("api_hash")
        bot_token = bot_data.get("bot_token")
        session_string = bot_data.get("session_string")
        if bot_token:
            await target_db.saveBot(bot_id, api_id, api_hash, bot_token, is_token=True)
        elif session_string:
            await target_db.saveBot(
                bot_id, api_id, api_hash, session_string, is_token=False
            )
        if source_vars:
            await target_db._set_user_vars(bot_id, source_vars)
        await source_db.removeBot(bot_id)
        await source_db.removeAllVars(bot_id)
        if bot_id in getattr(ctx.manager, "running_bots", {}):
            await ctx.manager.stop_bot(bot_id)
        if source_db != ctx.db:
            await source_db.close_async()
        if target_db != ctx.db:
            await target_db.close_async()
        await msg.edit_text(
            f"{client.ns.emoji.white_check_mark} **Migrasi Bot Berhasil!**\n\n"
            f"**Bot ID:** `{bot_id}`\n"
            f"**Dari:** `{source_db_name}`\n"
            f"**Ke:** `{target_db_name}`\n\n"
            f"Bot beserta seluruh datanya telah dipindahkan dan dihapus dari database lama.\n\n"
            f"Jangan lupa restart bot tujuan agar bot ini segera menyala."
        )
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Error saat tfbot: {e}")