from helpers.modules import Modules
import pyrogram
from pyrogram import filters


async def confirm_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    bot_name = f"ID {bot_id_to_manage}"

    try:
        bot_instance = client.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    text = (
        f"**{client.ns.emoji.md('exclamation')} Konfirmasi Penghapusan**\n\n"
        f"Anda yakin ingin menghapus bot **{bot_name}** (`{bot_id_to_manage}`) secara permanen?\n\n"
        f"_Semua data (member, paket, pengaturan) bot ini akan hilang dan tindakan ini tidak dapat diurungkan._"
    )

    layout = [
        [
            {
                "text": "✅ Ya, Saya Yakin Hapus",
                "callback_data": f"do_delete_bot {bot_id_to_manage}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": "❌ Tidak, Batalkan",
                "callback_data": f"manage_bot {bot_id_to_manage}",
                "style": "green",
                "emoji": client.ns.emoji.id("white_check_mark"),
            },
        ]
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def do_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    owner_of_target_bot = await client.db.getVars(bot_id_to_manage, "owner_id") or 0

    if user_id != owner_of_target_bot and user_id != client.owner_id:
        return await callback_query.answer(
            "Anda tidak berhak menghapus bot ini.",
            show_alert=True,
        )

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('hourglass')} **Menghapus Bot**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Bot ID', f'`{bot_id_to_manage}`'], ['Status', 'Sedang dihentikan dan dihapus']])}"
            )
        )
    )

    try:
        await client.manager.stop_bot(bot_id_to_manage)
        await client.db.removeBot(bot_id_to_manage)
        await client.db.removeAllVars(bot_id_to_manage)

        layout = [
            [
                {
                    "text": "⬅️ Kembali ke Daftar Bot",
                    "callback_data": "list_my_bots_0",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Penghapusan Berhasil**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Bot ID', f'`{bot_id_to_manage}`'], ['Data', 'Bot dan seluruh datanya telah dihapus dari sistem']])}"
                )
            ),
            reply_markup=btn,
        )

    except Exception as e:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal Menghapus Bot**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Terjadi kesalahan'], ['Error', f'`{e}`']])}"
                )
            )
        )


class BotDeletion(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^confirm_delete_bot\\s(\\d+)"))(
            self.handle(confirm_delete_bot_callback)
        )
        self.client.on_callback_query(filters.regex("^do_delete_bot\\s(\\d+)"))(
            self.handle(do_delete_bot_callback)
        )
