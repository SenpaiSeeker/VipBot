from helpers.modules import Modules
import pyrogram

from .. import *
from ..admin.cache import _user_cache
from .helpers import invalidate_page_cache, send_allbots_list


async def allbots_confirm_delete_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))
    layout = [
        [
            {
                "text": "✅ Ya, Hapus",
                "callback_data": f"allbots_do_delete_{bot_id}_{page}",
                "style": "red",
                "emoji": client.ns.emoji.id("white_check_mark"),
            },
            {
                "text": "❌ Tidak",
                "callback_data": f"allbots_back_{page}",
                "style": "green",
                "emoji": client.ns.emoji.id("cross_mark"),
            },
        ]
    ]

    text = (
        f"**{client.ns.emoji.md('warning')} Konfirmasi Penghapusan**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], [['Bot ID', f'`{bot_id}`'], ['Aksi', 'Anda yakin ingin menghapus bot ini secara permanen?']])}"
    )
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


async def allbots_do_delete_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('hourglass')} **Menghapus Bot**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Menghapus bot']])}"
            )
        )
    )
    try:
        owner_id_to_invalidate = await client.db.getVars(bot_id, "owner_id")
        await client.manager.stop_bot(bot_id)
        await asyncio.sleep(1)
        await client.db.removeBot(bot_id)
        await client.db.removeAllVars(bot_id)
        if owner_id_to_invalidate:
            _user_cache.invalidate(owner_id_to_invalidate)
        invalidate_page_cache(page)
        await send_allbots_list(client, callback_query, page, force_refresh=True)
        await callback_query.answer("✅ Bot berhasil dihapus.", show_alert=True)
    except Exception as e:
        await callback_query.answer(
            "❌Gagal menghapus bot: {e}".format(e=e), show_alert=True
        )
        await send_allbots_list(client, callback_query, 0, force_refresh=True)


class AllBotsDelete(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(
            filters.regex("^allbots_confirm_delete_(\\d+)_(\\d+)")
        )(self.handle(allbots_confirm_delete_callback))
        self.client.on_callback_query(
            filters.regex("^allbots_do_delete_(\\d+)_(\\d+)")
        )(self.handle(allbots_do_delete_callback))
