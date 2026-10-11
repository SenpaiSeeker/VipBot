from helpers import parse_dt

import pyrogram

from .. import *


@command(lambda ctx: filters.command("login") & filters.user(ctx.owner_id))
async def login_command_handler(client, message):
    usage_text = (
        f"{client.ns.emoji.md('robot')} **Perintah Login Bot**\n\n"
        "Khusus Owner Utama untuk membuat / mengaktifkan ulang bot yang mati.\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], [['Format 1', '`/login (bot_token)`'], ['Format 2', '`/login (bot_token) (owner_id)`'], ['Balas Pesan', 'Balas pesan berisi bot token dengan `/login` atau `/login (owner_id)`'], ['Owner ID', '`owner_id` bersifat opsional. Jika tidak diberikan dan sudah tersimpan sebelumnya, data owner lama akan dipakai']])}"
    )

    args_text = client.ns.telegram.arg.getMessage(message, is_arg=True)
    parts = (args_text or "").strip().split()
    bot_token = parts[0] if parts else None
    owner_id_arg = parts[1] if len(parts) >= 2 else None

    if not bot_token:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(markdown=usage_text)
        )

    try:
        new_bot_id = int(bot_token.split(":", 1)[0])
    except (ValueError, IndexError):
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Token tidak valid**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Format Benar', '`(bot_id):(secret)`'], ['Contoh', '`123456789:AAH...`']])}"
                )
            )
        )

    owner_id = None
    if owner_id_arg:
        try:
            owner_id = int(owner_id_arg)
        except ValueError:
            return await message.reply_rich(
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Owner ID tidak valid**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Owner ID tidak valid'], ['Syarat', '`owner_id` harus berupa angka']])}"
                    )
                )
            )

    if new_bot_id in ctx.manager.running_bots:
        running = ctx.manager.running_bots[new_bot_id]
        bot_name = running.me.first_name if running.me else f"ID {new_bot_id}"
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('warning')} **Bot Sudah Berjalan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', f'**{bot_name}** (`{new_bot_id}`)'], ['Status', 'Sudah berjalan. Tidak perlu login ulang']])}"
                )
            )
        )

    msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('mag')} **Memverifikasi Token**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Memverifikasi token & menghubungkan bot']])}"
            )
        )
    )

    try:
        bot_info = await client.ns.telegram.arg.getNamebot(bot_token)
        if not isinstance(bot_info, pyrogram.types.User):
            raise ValueError("Bot token tidak valid.")
    except Exception as e:
        return await msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal Memverifikasi Token**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal memverifikasi token'], ['Error', f'`{e}`']])}"
                )
            )
        )

    existing_owner = await ctx.db.getVars(new_bot_id, "owner_id")
    resolved_owner = owner_id or existing_owner or ctx.owner_id

    expiry_date_str = (datetime.now(timezone.utc) + timedelta(days=31)).isoformat()

    api_id = client.api_id
    api_hash = client.api_hash

    bot_data = {
        "name": str(new_bot_id),
        "api_id": api_id,
        "api_hash": api_hash,
        "bot_token": bot_token,
    }

    await ctx.manager.start_bot(bot_data)

    if new_bot_id not in ctx.manager.running_bots:
        remaining = await ctx.manager.flood_remaining(new_bot_id)
        if remaining > 0:
            mins = max(1, remaining // 60)
            return await msg.edit_text(
                rich_message=pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('hourglass')} **Kena FloodWait**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', f'`{new_bot_id}`'], ['Tunggu', f'±{mins} menit'], ['Penting', 'Jangan spam /login karena memperpanjang masa tunggu']])}"
                    )
                )
            )
        return await msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal Mengaktifkan Bot**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal mengaktifkan bot'], ['Keterangan', 'Token kemungkinan tidak valid / tidak bisa digunakan']])}"
                )
            )
        )

    await ctx.db.saveBot(new_bot_id, api_id, api_hash, bot_token, is_token=True)
    await ctx.db.setVars(new_bot_id, "owner_id", resolved_owner)
    await ctx.db.setVars(new_bot_id, "bot_expiration_date", expiry_date_str)

    if owner_id:
        owner_source = "argumen"
    elif existing_owner:
        owner_source = "data sebelumnya"
    else:
        owner_source = "Owner Utama"

    try:
        formatted_expiry = parse_dt(expiry_date_str).strftime("%d %b %Y")
    except ValueError:
        formatted_expiry = expiry_date_str

    await msg.edit_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=f"{client.ns.emoji.md('party_popper')} **Bot Berhasil Diaktifkan!**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', f'{bot_info.first_name} (`{new_bot_id}`)'], ['Owner', f'`{resolved_owner}` (dari {owner_source})'], ['Masa Aktif', f'`{formatted_expiry}`']])}"
        )
    )
