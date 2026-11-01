import asyncio
from datetime import datetime, timezone

import pyrogram
from pyrogram import filters

from helpers import listen, parse_dt
from helpers.modules import Modules

from .. import MAX_BOT_CAPACITY

_creation_lock = asyncio.Lock()


async def start_creation_process_callback(client, callback_query):
    user_id = callback_query.from_user.id
    expiry_date = parse_dt(await client.db.getVars(user_id, "user_expiry_date"))

    if not expiry_date or expiry_date <= datetime.now(timezone.utc):
        return await callback_query.answer(
            "Langganan Anda tidak valid atau telah berakhir.",
            show_alert=True,
        )

    all_bots_data = await client.db.getBots(is_token=True)

    if len(all_bots_data) >= MAX_BOT_CAPACITY:
        from config import BACKUP_BOT

        backup_text = f" melalui @{BACKUP_BOT}" if BACKUP_BOT else ""
        return await callback_query.answer(
            f"Kapasitas bot sudah penuh ({MAX_BOT_CAPACITY} Bot). Silakan "
            f"buat bot baru{backup_text}.",
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

        rows = [
            ["Isi", "Masukkan Bot Token Anda"],
            ["Sumber", "Dapatkan dari @BotFather"],
        ]
        token_prompt = (
            f"**{client.ns.emoji.md('robot')} Masukkan Bot Token**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
        )
        token_msg = await ask(token_prompt)

        if not token_msg or not token_msg.text:
            raise ValueError("Token bot tidak boleh kosong.")

        if token_msg.text.strip().lower() == "/batal":
            raise listen.UserCancelled

        token = token_msg.text.strip()

        rows = [["Status", "Memverifikasi data & token"]]
        msg = await client.send_rich_message(
            user_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('mag')} **Memverifikasi Data**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )

        new_bot_name = await client.ns.telegram.arg.getNamebot(token)

        if not isinstance(new_bot_name, pyrogram.types.User):
            raise ValueError("Token bot yang Anda masukkan tidak valid.")

        new_bot_id = int(token.split(":", 1)[0])
        if int(new_bot_name.id) != new_bot_id:
            raise ValueError("Token bot tidak cocok dengan ID bot.")

        existing_bots = await client.db.getBots(is_token=True)
        if any(str(bot.get("name")) == str(new_bot_id) for bot in existing_bots):
            raise ValueError(
                "Bot ini sudah terdaftar dan tidak dapat ditambahkan ulang."
            )

        rows = [
            ["Bot", f"'{new_bot_name.first_name}'"],
            ["Status", "Valid dan sedang disimpan"],
            ["Aksi", "Memulai bot"],
        ]
        await msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Token Valid**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

        api_id = client.api_id
        api_hash = client.api_hash
        bot_data = {
            "name": str(new_bot_id),
            "api_id": api_id,
            "api_hash": api_hash,
            "bot_token": token,
        }

        async with _creation_lock:
            existing_bots = await client.db.getBots(is_token=True)
            if any(str(bot.get("name")) == str(new_bot_id) for bot in existing_bots):
                raise ValueError(
                    "Bot ini sudah terdaftar dan tidak dapat ditambahkan ulang."
                )

            await client.db.saveBot(
                new_bot_id,
                api_id,
                api_hash,
                token,
                is_token=True,
            )

        await client.db.setVars(
            new_bot_id,
            "bot_expiration_date",
            expiry_date.isoformat(),
        )
        await client.db.setVars(new_bot_id, "owner_id", user_id)

        await client.manager.start_bot(bot_data)

        if new_bot_id not in client.manager.running_bots:
            remaining = await client.manager.flood_remaining(new_bot_id)
            if remaining > 0:
                mins = max(1, remaining // 60)
                raise ValueError(
                    f"Bot tersimpan tetapi sedang FloodWait ±{mins} menit. "
                    "Bot akan dicoba aktifkan kembali otomatis."
                )

            await client.db.removeBot(new_bot_id)
            await client.db.removeVars(new_bot_id, "owner_id")
            await client.db.removeVars(new_bot_id, "bot_expiration_date")
            raise ValueError("Gagal mengaktifkan bot. Silakan coba lagi.")

        await client.db.removeVars(user_id, "user_expiry_date")

        await msg.edit(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('party_popper')} **Selamat!** Bot "
                    f"**{new_bot_name.first_name}** berhasil dibuat dan "
                    "aktif.\n\n"
                    f"| Info | Detail |\n"
                    f"| :--- | :---: |\n"
                    f"| Nama Bot | {new_bot_name.first_name} |\n"
                    f"| ID | `{new_bot_id}` |\n"
                    f"| Masa Aktif | s/d `{expiry_date.strftime('%d-%m-%Y')}` |"
                )
            )
        )

    except listen.UserCancelled:
        rows = [["Status", "Dibatalkan"]]
        await client.send_rich_message(
            user_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Proses "
                    "Dibatalkan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )
    except asyncio.TimeoutError:
        rows = [
            ["Status", "Waktu habis"],
            ["Keterangan", "Proses telah dibatalkan otomatis"],
        ]
        await client.send_rich_message(
            user_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('alarm_clock')} **Waktu Habis**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )
    except Exception as e:
        rows = [
            ["Status", "Error pembuatan bot"],
            ["Error", f"`{e}`"],
        ]
        await client.send_rich_message(
            user_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Error Pembuatan "
                    "Bot**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )


class BotCreation(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^start_creation_process$"))(
            self.handle(start_creation_process_callback)
        )
