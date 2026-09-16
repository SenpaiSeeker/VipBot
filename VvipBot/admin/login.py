from config import API_HASH, API_ID

from .. import *


@command(lambda ctx: filters.command("login") & filters.user(ctx.owner_id))
async def login_command_handler(client, message):
    usage_text = (
        f"{client.ns.emoji.robot} **Perintah Login Bot**\n\n"
        "Khusus Owner Utama untuk membuat / mengaktifkan ulang bot yang mati.\n\n"
        f"{client.ns.emoji.pen} **Format:**\n"
        "`/login <bot_token>`\n"
        "`/login <bot_token> <owner_id>`\n"
        "atau balas pesan berisi bot token dengan `/login` atau `/login <owner_id>`.\n\n"
        "`owner_id` bersifat opsional. Jika tidak diberikan dan sudah tersimpan "
        "sebelumnya, data owner lama akan dipakai."
    )

    parts = (message.text or "").strip().split()
    bot_token = None
    owner_id_arg = None

    if len(parts) >= 2:
        bot_token = parts[1]
        if len(parts) >= 3:
            owner_id_arg = parts[2]
    elif message.reply_to_message and message.reply_to_message.text:
        replied_parts = message.reply_to_message.text.strip().split()
        if replied_parts:
            bot_token = replied_parts[0]
            if len(parts) >= 2:
                owner_id_arg = parts[1]

    if not bot_token:
        return await message.reply_text(usage_text)

    try:
        new_bot_id = int(bot_token.split(":", 1)[0])
    except (ValueError, IndexError):
        return await message.reply_text(
            f"{client.ns.emoji.cross_mark} **Token tidak valid.**\n"
            "Format token yang benar: `<bot_id>:<secret>`\n"
            "Contoh: `123456789:AAH...`"
        )

    owner_id = None
    if owner_id_arg:
        try:
            owner_id = int(owner_id_arg)
        except ValueError:
            return await message.reply_text(
                f"{client.ns.emoji.cross_mark} **Owner ID tidak valid.**\n"
                "`owner_id` harus berupa angka."
            )

    if new_bot_id in ctx.manager.running_bots:
        running = ctx.manager.running_bots[new_bot_id]
        bot_name = (
            running.me.first_name if running.me else f"ID {new_bot_id}"
        )
        return await message.reply_text(
            f"{client.ns.emoji.warning} Bot **{bot_name}** (`{new_bot_id}`) "
            "sudah berjalan. Tidak perlu login ulang."
        )

    msg = await message.reply_text(
        f"{client.ns.emoji.mag} `Memverifikasi token & menghubungkan bot...`"
    )

    try:
        bot_info = await client.ns.telegram.arg.getNamebot(bot_token)
        if "invalid" in [bot_info]:
            raise ValueError("Bot token tidak valid.")
    except Exception as e:
        return await msg.edit_text(
            f"{client.ns.emoji.cross_mark} **Gagal memverifikasi token:**\n`{e}`"
        )

    existing_owner = await ctx.db.getVars(new_bot_id, "owner_id")
    resolved_owner = owner_id or existing_owner or ctx.owner_id

    expiry_date_str = await ctx.db.getVars(new_bot_id, "bot_expiration_date")
    if not expiry_date_str:
        expiry_date_str = (
            datetime.now(timezone.utc) + timedelta(days=365)
        ).isoformat()

    bot_data = {
        "name": str(new_bot_id),
        "api_id": API_ID,
        "api_hash": API_HASH,
        "bot_token": bot_token,
    }

    await ctx.manager.start_bot(bot_data)

    if new_bot_id not in ctx.manager.running_bots:
        return await msg.edit_text(
            f"{client.ns.emoji.cross_mark} **Gagal mengaktifkan bot.**\n"
            "Token kemungkinan tidak valid / tidak bisa digunakan."
        )

    await ctx.db.saveBot(new_bot_id, API_ID, API_HASH, bot_token, is_token=True)
    await ctx.db.setVars(new_bot_id, "owner_id", resolved_owner)
    await ctx.db.setVars(new_bot_id, "bot_expiration_date", expiry_date_str)

    if owner_id:
        owner_source = "argumen"
    elif existing_owner:
        owner_source = "data sebelumnya"
    else:
        owner_source = "Owner Utama"

    try:
        formatted_expiry = datetime.fromisoformat(
            expiry_date_str
        ).strftime("%d %b %Y")
    except ValueError:
        formatted_expiry = expiry_date_str

    await msg.edit_text(
        f"{client.ns.emoji.party_popper} **Bot Berhasil Diaktifkan!**\n\n"
        f"{client.ns.emoji.robot} **Bot:** {bot_info.first_name} (`{new_bot_id}`)\n"
        f"{client.ns.emoji.bust_in_silhouette} **Owner:** `{resolved_owner}` "
        f"(dari {owner_source})\n"
        f"{client.ns.emoji.calendar} **Masa Aktif:** `{formatted_expiry}`"
    )