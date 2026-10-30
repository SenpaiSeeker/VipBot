from helpers.modules import Modules
import asyncio

import pyrogram
from pyrogram import filters

from .. import is_bot_owner, listen


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
            await client.db.removeVars(client.me.id, "notif_chat_id")

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
            await client.db.setVars(client.me.id, "notif_chat_id", chat_target)

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

            await client.db.setVars(client.me.id, "notif_chat_id", raw)

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


async def set_notif_payment_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    try:
        chat_target = int(callback_query.data.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        return await callback_query.answer("Chat ID tidak valid.", show_alert=True)

    await client.db.setVars(client.me.id, "notif_chat_id", chat_target)

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

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('white_check_mark')} **Notifikasi Payment Diaktifkan**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Semua notifikasi payment dialihkan ke chat tujuan'], ['Chat ID', f'`{chat_target}`']])}"
            )
        ),
        reply_markup=back_btn,
    )


class SettingsNotification(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^set_notif_chat$"))(
            self.handle(set_notif_chat_callback)
        )
        self.client.on_callback_query(filters.regex(r"^set_notif_payment\s(-?\d+)$"))(
            self.handle(set_notif_payment_callback)
        )
