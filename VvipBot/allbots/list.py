import pyrogram

from .. import *
from .helpers import invalidate_page_cache, send_allbots_list


@command(lambda ctx: filters.command("allbots") & filters.user(ctx.owner_id))
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


@command(lambda ctx: filters.regex("^allbots_(\\-?\\d+)"), handler_type="callback")
async def allbots_pagination_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    page = int(callback_query.data.split("_")[1])
    await send_allbots_list(client, callback_query, page)
