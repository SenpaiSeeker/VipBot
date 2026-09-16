from . import command, ctx, filters


@command(lambda ctx: filters.command("tfdatabase") & filters.user(ctx.owner_id))
async def tfdatabase_command_handler(client, message):
    args = message.command
    if len(args) != 3:
        return await message.reply_text(
            "Format salah. Gunakan: `/tfdatabase <source_id>:<source_db> <target_id>:<target_db>`\nContoh: `/tfdatabase 123455:databaseV1 666999:databaseV2`"
        )
    source_part = args[1]
    target_part = args[2]
    try:
        source_id_str, source_db_name = source_part.split(":")
        target_id_str, target_db_name = target_part.split(":")
        source_id = int(source_id_str)
        target_id = int(target_id_str)
    except Exception:
        return await message.reply_text(
            "Format salah. Pastikan menggunakan format `ID:NAMA_DB`. Contoh: `/tfdatabase 123455:databaseV1 666999:databaseV2`"
        )
    msg = await message.reply_text(
        f"{client.ns.emoji.repeat} Memproses transfer database..."
    )
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
        source_data = await source_db._get_user_vars(source_id)
        if not source_data:
            if source_db != ctx.db:
                await source_db.close_async()
            if target_db != ctx.db:
                await target_db.close_async()
            return await msg.edit_text(
                f"{client.ns.emoji.cross_mark} Data sumber tidak ditemukan pada database."
            )
        await target_db._set_user_vars(target_id, source_data)
        if source_db != ctx.db:
            await source_db.close_async()
        if target_db != ctx.db:
            await target_db.close_async()
        await msg.edit_text(
            f"{client.ns.emoji.white_check_mark} **Transfer Database Berhasil!**\n\n"
            f"**Sumber:** `{source_id}` (`{source_db_name}`)\n"
            f"**Tujuan:** `{target_id}` (`{target_db_name}`)\n\n"
            f"Semua data berhasil disalin secara lengkap."
        )
    except Exception as e:
        await msg.edit_text(
            f"{client.ns.emoji.cross_mark} Terjadi kesalahan saat mentransfer database:\n<pre>{e}</pre>"
        )