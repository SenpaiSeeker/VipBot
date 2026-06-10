import re

from telethon import events

from .. import command, ctx
from .helpers import invalidate_page_cache, send_allbots_list


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/allbots(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def allbots_command_handler(client, event):
    invalidate_page_cache()
    em = client.ns.emoji
    msg_process = await event.respond(
        f"{em.repeat} Sedang memproses mengumpulkan bot",
        parse_mode="html",
    )

    await send_allbots_list(client, event, 0, force_refresh=True)
    await msg_process.delete()


@command(lambda ctx: events.CallbackQuery(pattern=re.compile(b"^allbots_-?\\d+$")))
async def allbots_pagination_callback(client, event):
    sender = await event.get_sender()

    if sender.id != ctx.owner_id:
        return

    payload = event.data.decode("utf-8")
    page = int(payload.split("_")[1])

    await send_allbots_list(client, event, page)
