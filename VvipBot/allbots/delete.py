from telethon import events
from .. import command, ctx


@command(lambda ctx: events.CallbackQuery(pattern=b"^allbots_confirm_delete_"))
async def allbots_confirm_delete_callback(client, event):
    em = client.ns.emoji
    payload = event.data.decode("utf-8")
    bot_id = int(payload.split("_")[3])

    text = (
        f"{em.anger} <b>Konfirmasi Penghapusan</b>\n\n"
        f"Anda yakin ingin menghapus bot <code>{bot_id}</code> secara permanen?\n\n"
        f"<i>Semua data bot ini akan hilang dan tindakan ini tidak dapat diurungkan.</i>"
    )

    layout = [
        [
            {"text": "✅ Ya, Hapus",    "callback_data": f"allbots_do_delete_{bot_id}", "style": "success", "emoji": 5427009714745517609},
            {"text": "❌ Tidak",        "callback_data": f"allbots_detail_{bot_id}_0", "style": "danger",  "emoji": 5465665476971471368},
        ]
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^allbots_do_delete_"))
async def allbots_do_delete_callback(client, event):
    em = client.ns.emoji
    payload = event.data.decode("utf-8")
    bot_id = int(payload.split("_")[3])

    try:
        await ctx.manager.stop_bot(bot_id)
        await ctx.db.removeBot(bot_id)
        await ctx.db.removeAllVars(bot_id)

        await event.answer("✅ Bot berhasil dihapus.", alert=True)
        event.data = b"allbots_list_0"
        from .list import allbots_list_callback
        await allbots_list_callback(client, event)
    except Exception as e:
        await event.answer(f"❌ Gagal menghapus bot: {e}", alert=True)
