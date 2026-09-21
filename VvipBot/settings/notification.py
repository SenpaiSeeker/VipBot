import asyncio

from pyrogram import filters

from .. import command, ctx, is_bot_owner, listen


@command(
    lambda ctx: filters.regex("^set_notif_chat$"),
    handler_type="callback",
)
async def set_notif_chat_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        prompt = (
            f"**{client.ns.emoji.bell} Atur Tempat Notifikasi**\n\n"
            f"Kirim ID chat atau @username tempat notifikasi pembayaran akan dikirim.\n\n"
            f"Ketik `/none` untuk kembali ke default (dikirim ke owner_id).\n\n"
            f"Ketik `/batal` untuk membatalkan."
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=600)

        if not ask_msg.text:
            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.cross_mark} **Gagal:** Pesan bukan teks.",
                reply_markup=back_btn,
            )

        raw = ask_msg.text.strip()

        if raw.lower() == "/batal":
            raise listen.UserCancelled

        if raw.lower() == "/none":
            await ctx.db.removeVars(client.me.id, "notif_chat_id")

            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.white_check_mark} **Sukses!** Notifikasi kembali ke default (owner_id).",
                reply_markup=back_btn,
            )

        if raw.lstrip("-").isdigit():
            chat_target = int(raw)
            await ctx.db.setVars(client.me.id, "notif_chat_id", chat_target)

            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.white_check_mark} **Sukses!** Tempat notifikasi diatur ke `{chat_target}`.",
                reply_markup=back_btn,
            )

        if raw.startswith("@") and len(raw) > 1:
            try:
                await client.resolve_peer(raw)
            except Exception:
                return await client.send_message(
                    chat_id,
                    f"{client.ns.emoji.cross_mark} **Gagal:** Username `{raw}` tidak valid atau bot tidak dapat menjangkau target tersebut.",
                    reply_markup=back_btn,
                )

            await ctx.db.setVars(client.me.id, "notif_chat_id", raw)

            return await client.send_message(
                chat_id,
                f"{client.ns.emoji.white_check_mark} **Sukses!** Tempat notifikasi diatur ke `{raw}`.",
                reply_markup=back_btn,
            )

        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Gagal:** Format tidak valid.\n\n"
            f"Gunakan **ID chat** (angka), **@username**, atau `/none` untuk kembali ke default.",
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
            reply_markup=back_btn,
        )
