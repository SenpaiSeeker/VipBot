import pyrogram

from helpers import parse_dt
from helpers.modules import Modules

from .. import *


async def login_command_handler(client, message):
    rows = [
        ["Format 1", "`/login (bot_token)`"],
        ["Format 2", "`/login (bot_token) (owner_id)`"],
        [
            "Balas Pesan",
            "Balas pesan berisi bot token dengan `/login` atau " "`/login (owner_id)`",
        ],
        [
            "Owner ID",
            "`owner_id` bersifat opsional. Jika tidak diberikan dan sudah "
            "tersimpan sebelumnya, data owner lama akan dipakai",
        ],
    ]
    usage_text = (
        f"{client.ns.emoji.md('robot')} **Perintah Login Bot**\n\n"
        "Khusus Owner Utama untuk membuat / mengaktifkan ulang bot yang mati.\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
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
        rows = [
            ["Format Benar", "`(bot_id):(secret)`"],
            ["Contoh", "`123456789:AAH...`"],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Token tidak valid**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

    owner_id = None
    if owner_id_arg:
        try:
            owner_id = int(owner_id_arg)
        except ValueError:
            rows = [
                ["Status", "Owner ID tidak valid"],
                ["Syarat", "`owner_id` harus berupa angka"],
            ]
            return await message.reply_rich(
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Owner ID tidak "
                        "valid**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                    )
                )
            )

    if new_bot_id in client.manager.running_bots:
        running = client.manager.running_bots[new_bot_id]
        bot_name = running.me.first_name if running.me else f"ID {new_bot_id}"
        rows = [
            ["Bot", f"**{bot_name}** (`{new_bot_id}`)"],
            ["Status", "Sudah berjalan. Tidak perlu login ulang"],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('warning')} **Bot Sudah Berjalan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

    rows = [["Status", "Memverifikasi token & menghubungkan bot"]]
    msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('mag')} **Memverifikasi Token**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
    )

    try:
        bot_info = await client.ns.telegram.arg.getNamebot(bot_token)
        if not isinstance(bot_info, pyrogram.types.User):
            raise ValueError("Bot token tidak valid.")
        if int(bot_info.id) != new_bot_id:
            raise ValueError("Token bot tidak cocok dengan ID bot.")
    except Exception as e:
        rows = [
            ["Status", "Gagal memverifikasi token"],
            ["Error", f"`{e}`"],
        ]
        return await msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal Memverifikasi "
                    "Token**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

    existing_owner = await client.db.getVars(new_bot_id, "owner_id")
    resolved_owner = owner_id or existing_owner or client.owner_id

    existing_expiry = parse_dt(
        await client.db.getVars(new_bot_id, "bot_expiration_date")
    )
    expiry_date = existing_expiry or (datetime.now(timezone.utc) + timedelta(days=31))
    expiry_date_str = expiry_date.isoformat()

    api_id = client.api_id
    api_hash = client.api_hash

    bot_data = {
        "name": str(new_bot_id),
        "api_id": api_id,
        "api_hash": api_hash,
        "bot_token": bot_token,
    }

    await client.db.saveBot(new_bot_id, api_id, api_hash, bot_token, is_token=True)

    await client.manager.start_bot(bot_data)

    if new_bot_id not in client.manager.running_bots:
        remaining = await client.manager.flood_remaining(new_bot_id)
        if remaining > 0:
            mins = max(1, remaining // 60)
            rows = [
                ["Bot", f"`{new_bot_id}`"],
                ["Tunggu", f"±{mins} menit"],
                [
                    "Penting",
                    "Jangan spam /login karena memperpanjang masa tunggu",
                ],
            ]
            return await msg.edit_text(
                rich_message=pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('hourglass')} **Kena FloodWait**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                    )
                )
            )
        rows = [
            ["Status", "Gagal mengaktifkan bot"],
            [
                "Keterangan",
                "Token kemungkinan tidak valid / tidak bisa digunakan",
            ],
        ]
        return await msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal Mengaktifkan Bot**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

    await client.db.setVars(new_bot_id, "owner_id", resolved_owner)
    await client.db.setVars(new_bot_id, "bot_expiration_date", expiry_date_str)

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

    rows = [
        ["Bot", f"{bot_info.first_name} (`{new_bot_id}`)"],
        ["Owner", f"`{resolved_owner}` (dari {owner_source})"],
        ["Masa Aktif", f"`{formatted_expiry}`"],
    ]
    await msg.edit_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=f"{client.ns.emoji.md('party_popper')} **Bot Berhasil "
            "Diaktifkan!**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
        )
    )


class AdminLogin(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_message(
            filters.command("login") & filters.user(self.client.owner_id)
        )(self.handle(login_command_handler))
