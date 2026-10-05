import asyncio

import pyrogram
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
            f"{client.ns.emoji.md('bell')} **Atur Tempat Notifikasi**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Instruksi', 'Kirim ID chat atau @username tempat notifikasi pembayaran akan dikirim'], ['Default', 'Ketik `/none` untuk kembali ke default (dikirim ke owner_id)'], ['Batal', 'Ketik `/batal` untuk membatalkan']])}"
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=600)

        if not ask_msg.text:
            return await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Gagal**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal'], ['Keterangan', 'Pesan bukan teks']])}"
                    )
                ),
                reply_markup=back_btn,
            )

        raw = ask_msg.text.strip()

        if raw.lower() == "/batal":
            raise listen.UserCancelled

        if raw.lower() == "/none":
            await ctx.db.removeVars(client.me.id, "notif_chat_id")

            return await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Notifikasi kembali ke default'], ['Tujuan', 'owner_id']])}"
                    )
                ),
                reply_markup=back_btn,
            )

        if raw.lstrip("-").isdigit():
            chat_target = int(raw)
            await ctx.db.setVars(client.me.id, "notif_chat_id", chat_target)

            return await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Tempat notifikasi diperbarui'], ['Tujuan', f'`{chat_target}`']])}"
                    )
                ),
                reply_markup=back_btn,
            )

        if raw.startswith("@") and len(raw) > 1:
            try:
                await client.resolve_peer(raw)
            except Exception:
                return await client.send_rich_message(
                    chat_id,
                    pyrogram.types.InputRichMessage(
                        markdown=(
                            f"{client.ns.emoji.md('cross_mark')} **Gagal**\n\n"
                            f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal'], ['Keterangan', f'Username `{raw}` tidak valid atau bot tidak dapat menjangkau target tersebut']])}"
                        )
                    ),
                    reply_markup=back_btn,
                )

            await ctx.db.setVars(client.me.id, "notif_chat_id", raw)

            return await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Tempat notifikasi diperbarui'], ['Tujuan', f'`{raw}`']])}"
                    )
                ),
                reply_markup=back_btn,
            )

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal'], ['Keterangan', 'Format tidak valid'], ['Format', 'Gunakan **ID chat** (angka), **@username**, atau `/none` untuk kembali ke default']])}"
                )
            ),
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Proses Dibatalkan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Dibatalkan']])}"
                )
            ),
            reply_markup=back_btn,
        )
