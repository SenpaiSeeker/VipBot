import asyncio

import pyrogram
from pyrogram import filters

from .. import command, ctx, is_bot_owner, listen
from helpers.income_template import INCOME_TEMPLATE_VARIABLES

TEMPLATE_EXAMPLE = (
    "{mention} baru saja membeli **{item_name}**\n\n"
    "Total Bayar: **{total}**\n"
    "Durasi: {item_duration}\n"
    "Order ID: {order_id}\n"
    "Waktu: {time}"
)


def _back_button(client):
    return client.ns.telegram.button.build_button_grid(
        [
            [
                {
                    "text": "• Kembali ke Pengaturan •",
                    "callback_data": "settings",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ]
        ]
    )


@command(
    lambda ctx: filters.regex("^set_income_text$"),
    handler_type="callback",
)
async def set_income_text_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer("🚫 Akses ditolak", show_alert=True)

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()
    back_btn = _back_button(client)

    current = await ctx.db.getVars(client.me.id, "income_text_template")
    status = "Kustom (aktif)" if current else "Default (bawaan)"
    var_rows = [[f"`{name}`", desc] for name, desc in INCOME_TEMPLATE_VARIABLES]

    try:
        prompt = (
            f"{client.ns.emoji.md('pencil')} **Atur Teks Notifikasi Pemasukan**\n\n"
            f"Status saat ini: **{status}**\n\n"
            f"Kirim teks baru untuk notifikasi pemasukan. Variabel yang tersedia:\n\n"
            f"{client.ns.table.md(['Variabel', 'Keterangan'], var_rows)}\n\n"
            f"Contoh template:\n"
            f"```\n{TEMPLATE_EXAMPLE}\n```\n\n"
            f"Ketik `/empty` untuk kembali ke default (tampilan tabel bawaan).\n"
            f"Ketik `/batal` untuk membatalkan."
        )
        ask_text_msg = await client.ask(chat_id, prompt, timeout=600)

        if not ask_text_msg.text:
            return await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=f"{client.ns.emoji.md('cross_mark')} **Gagal:** Pesan bukan teks."
                ),
                reply_markup=back_btn,
            )

        if ask_text_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        if ask_text_msg.text.lower() == "/empty":
            await ctx.db.removeVars(client.me.id, "income_text_template")

            return await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('white_check_mark')} **Sukses!** "
                        f"Teks notifikasi pemasukan kembali ke default."
                    )
                ),
                reply_markup=back_btn,
            )

        await ctx.db.setVars(
            client.me.id,
            "income_text_template",
            ask_text_msg.text.markdown,
        )

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Sukses!** "
                    f"Teks notifikasi pemasukan berhasil diperbarui."
                )
            ),
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Proses Dibatalkan**"
            ),
            reply_markup=back_btn,
        )
