import asyncio

from pyrogram import filters

from .. import command, ctx, is_bot_owner, listen


def _back_to_settings_layout(client):
    return [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]


@command(
    lambda ctx: filters.regex("^set_notif_chat$"),
    handler_type="callback",
)
async def set_notif_chat_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    back_btn = client.ns.telegram.button.build_button_grid(
        _back_to_settings_layout(client)
    )
    try:
        prompt = (
            f"**{client.ns.emoji.bell} Atur Tempat Notifikasi**\n\n"
            "Kirim ID chat atau @username tempat notifikasi pembayaran akan dikirim.\n\n"
            "Ketik `/none` untuk kembali ke default (dikirim ke owner_id).\n\n"
            "Ketik `/batal` untuk membatalkan."
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=600)

        if not ask_msg.text:
            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.cross_mark} **Gagal:** Pesan bukan teks.",
                reply_markup=back_btn,
            )
        if ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        if ask_msg.text.lower() == "/none":
            await ctx.db.removeVars(client.me.id, "notif_chat_id")
            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.white_check_mark} **Sukses!** Notifikasi kembali ke default (owner_id).",
                reply_markup=back_btn,
            )

        await ctx.db.setVars(client.me.id, "notif_chat_id", ask_msg.text)
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} **Sukses!** Tempat notifikasi diatur ke `{ask_msg.text}`.",
            reply_markup=back_btn,
        )
    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
            reply_markup=back_btn,
        )