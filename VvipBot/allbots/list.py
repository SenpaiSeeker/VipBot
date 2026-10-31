import pyrogram

from helpers.modules import Modules

from .. import *
from .helpers import invalidate_page_cache, send_allbots_list


async def allbots_command_handler(client, message):
    invalidate_page_cache()
    msg_process = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('repeat')} **Memproses**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Sedang memproses mengumpulkan bot']])}"
            )
        )
    )
    await send_allbots_list(client, message, 0, force_refresh=True)
    await msg_process.delete()


async def allbots_pagination_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    page = int(callback_query.data.split("_")[1])
    await send_allbots_list(client, callback_query, page)


class AllBotsList(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_message(
            filters.command("allbots") & filters.user(self.client.owner_id)
        )(self.handle(allbots_command_handler))
        self.client.on_callback_query(filters.regex("^allbots_(\\-?\\d+)"))(
            self.handle(allbots_pagination_callback)
        )
