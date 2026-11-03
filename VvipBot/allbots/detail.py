import pyrogram

from helpers import parse_dt
from helpers.modules import Modules

from .. import *
from .helpers import _resolve_owner_text, send_allbots_list


async def allbots_detail_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))

    bot_username = "Offline"
    bot_name = f"Bot ID {bot_id}"
    try:
        bot_instance = client.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username or "Tidak Ada"
    except Exception:
        pass

    owner_id = await client.db.getVars(bot_id, "owner_id")
    owner_text = await _resolve_owner_text(bot_instance or client, owner_id)

    exp_date = parse_dt(await client.db.getVars(bot_id, "bot_expiration_date"))
    days_left_text = (
        f"`{(exp_date - datetime.now(timezone.utc)).days}` hari"
        if exp_date
        else "Belum diatur"
    )

    text = (
        f"**{client.ns.emoji.md('toolbox')} Kelola Bot Spesifik**\n\n"
        f"| Label | Isi |\n"
        f"| :--- | :--- |\n"
        f"| Nama Bot | {bot_name} |\n"
        f"| ID Bot | `{bot_id}` |\n"
        f"| Username Bot | @{bot_username} |\n"
        f"| Pemilik | {owner_text} |\n"
        f"| Sisa Aktif | {days_left_text} |"
    )

    layout = [
        [
            {
                "text": "🗑️ Hapus Bot",
                "callback_data": f"allbots_confirm_delete_{bot_id}_{page}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ],
        [
            {
                "text": "🗓️ Kelola Masa Aktif",
                "callback_data": f"allbots_duration_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            }
        ],
        [
            {
                "text": "🔙 Kembali ke Daftar",
                "callback_data": f"allbots_back_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


async def allbots_back_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    page = int(callback_query.matches[0].group(1))
    await send_allbots_list(client, callback_query, page)


class AllBotsDetail(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^allbots_detail_(\\d+)_(\\d+)"))(
            self.handle(allbots_detail_callback)
        )
        self.client.on_callback_query(filters.regex("^allbots_back_(\\d+)"))(
            self.handle(allbots_back_callback)
        )
