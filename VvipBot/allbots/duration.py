from helpers.modules import Modules
import pyrogram

from helpers import parse_dt

from .. import *
from .helpers import invalidate_page_cache, send_allbots_list


async def allbots_duration_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))
    layout = [
        [
            {
                "text": "➕ Tambah Masa Aktif",
                "callback_data": f"allbots_extend_{bot_id}_{page}",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            }
        ],
        [
            {
                "text": "➖ Kurangi Masa Aktif",
                "callback_data": f"allbots_reduce_{bot_id}_{page}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": f"allbots_back_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=f"**{client.ns.emoji.md('calendar')} Kelola Masa Aktif untuk Bot `{bot_id}`**"
        ),
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


async def allbots_extend_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))
    buttons = [
        {
            "text": f"+{days} hari",
            "callback_data": f"allbots_do_extend_{bot_id}_{days}_{page}",
            "style": "green",
            "emoji": client.ns.emoji.id("plus"),
        }
        for days in [7, 30, 90]
    ]
    layout = [
        buttons,
        [
            {
                "text": "• Kembali •",
                "callback_data": f"allbots_duration_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('plus')} **Pilih Durasi**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', f'`{bot_id}`'], ['Tindakan', 'Durasi yang akan ditambahkan'], ['Opsi', 'Pilih salah satu durasi di bawah ini']])}"
            )
        ),
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


async def allbots_do_extend_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    days = int(callback_query.matches[0].group(2))
    page = int(callback_query.matches[0].group(3))
    current_expiry_str = await client.db.getVars(bot_id, "bot_expiration_date")
    start_date = datetime.now(timezone.utc)
    current_expiry = parse_dt(current_expiry_str)
    if current_expiry and current_expiry > start_date:
        start_date = current_expiry
    await client.db.setVars(
        bot_id, "bot_expiration_date", (start_date + timedelta(days=days)).isoformat()
    )
    await callback_query.answer(
        f"{days} hari berhasil ditambahkan ke bot {bot_id}.",
        show_alert=True,
    )
    invalidate_page_cache(page)
    await send_allbots_list(client, callback_query, page, force_refresh=True)


async def allbots_reduce_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))
    buttons = [
        {
            "text": f"-{days} hari",
            "callback_data": f"allbots_do_reduce_{bot_id}_{days}_{page}",
            "style": "red",
            "emoji": client.ns.emoji.id("minus"),
        }
        for days in [7, 30, 90]
    ]
    layout = [
        buttons,
        [
            {
                "text": "• Kembali •",
                "callback_data": f"allbots_duration_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('minus')} **Pilih Durasi**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', f'`{bot_id}`'], ['Tindakan', 'Durasi yang akan dikurangi'], ['Opsi', 'Pilih salah satu durasi di bawah ini']])}"
            )
        ),
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


async def allbots_do_reduce_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    days = int(callback_query.matches[0].group(2))
    page = int(callback_query.matches[0].group(3))
    current_expiry = parse_dt(await client.db.getVars(bot_id, "bot_expiration_date"))
    if not current_expiry:
        await callback_query.answer(
            "Bot ini tidak memiliki tanggal kedaluwarsa untuk dikurangi.",
            show_alert=True,
        )
        return
    new_expiry_date = current_expiry - timedelta(days=days)
    await client.db.setVars(bot_id, "bot_expiration_date", new_expiry_date.isoformat())
    await callback_query.answer(
        f"Masa aktif bot {bot_id} berhasil dikurangi {days} hari.",
        show_alert=True,
    )
    invalidate_page_cache(page)
    await send_allbots_list(client, callback_query, page, force_refresh=True)


class AllBotsDuration(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^allbots_duration_(\\d+)_(\\d+)"))(
            self.handle(allbots_duration_callback)
        )
        self.client.on_callback_query(filters.regex("^allbots_extend_(\\d+)_(\\d+)"))(
            self.handle(allbots_extend_callback)
        )
        self.client.on_callback_query(
            filters.regex("^allbots_do_extend_(\\d+)_(\\d+)_(\\d+)")
        )(self.handle(allbots_do_extend_callback))
        self.client.on_callback_query(filters.regex("^allbots_reduce_(\\d+)_(\\d+)"))(
            self.handle(allbots_reduce_callback)
        )
        self.client.on_callback_query(
            filters.regex("^allbots_do_reduce_(\\d+)_(\\d+)_(\\d+)")
        )(self.handle(allbots_do_reduce_callback))
