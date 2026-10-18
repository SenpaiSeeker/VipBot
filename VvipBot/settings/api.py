import asyncio

import pyrogram
from pyrogram import filters

from .. import command, ctx, is_bot_owner, listen


@command(
    lambda ctx: filters.regex("^api_settings$"),
    handler_type="callback",
)
async def api_settings_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    saweria_status = (
        f"{client.ns.emoji.md('white_check_mark')} Ativ"
        if saweria_user_id
        else f"{client.ns.emoji.md('cross_mark')} Belum Diatur"
    )

    layout = [
        [
            {
                "text": "💳 Atur Kunci Saweria",
                "callback_data": "set_api SAWERIA",
                "style": "green",
                "emoji": client.ns.emoji.id("gem"),
            }
        ],
        [
            {
                "text": "🗑️ Hapus Semua Kunci",
                "callback_data": "del_api_confirm",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ],
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]

    status_rows = [
        [
            "`Gateway Pembayaran (Saweria)`",
            f"**{saweria_status}**" if saweria_user_id else "Belum Diatur",
        ],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('key')} **Pengelola Kunci API untuk {client.ns.telegram.arg.getMention(client.me, md=True)}**\n\n"
        f"{table.md(['Layanan', 'Status'], status_rows)}\n\n"
        f"Pilih tindakan:"
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


@command(
    lambda ctx: filters.regex("^set_api\\s(.+)"),
    handler_type="callback",
)
async def set_api_key_prompt(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    _, key_name = callback_query.data.split(" ", 1)
    await callback_query.message.delete()

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan API •",
                "callback_data": "api_settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:

        def ask(p):
            return client.ask(
                chat_id,
                f"{p}\n\nKetik `/batal` untuk membatalkan.",
                timeout=600,
            )

        if key_name == "SAWERIA":
            username_msg = await ask(
                f"**2/2: Username Saweria**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Isi', 'Kirim **Username Saweria** Anda']])}"
            )
            if username_msg.text and username_msg.text.lower() == "/batal":
                raise listen.UserCancelled

            processing_msg = await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('hourglass')} **Sedang Memproses**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Sedang memproses'], ['Keterangan', 'Mohon tunggu sebentar']])}"
                    )
                ),
            )

            try:
                saweria_temp = client.ns.payment.SaweriaScraper()
                user_id_saweria = await saweria_temp.get_user_id(
                    username=username_msg.text
                )

                if not user_id_saweria:
                    raise Exception("Username Saweria tidak ditemukan.")

                await ctx.db.setVars(
                    client.me.id,
                    "SAWERIA_USER_ID",
                    user_id_saweria,
                )

                await processing_msg.delete()

                await client.send_rich_message(
                    chat_id,
                    pyrogram.types.InputRichMessage(
                        markdown=(
                            f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n\n"
                            f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Kunci Saweria berhasil disimpan']])}"
                        )
                    ),
                    reply_markup=back_btn,
                )

            except Exception as e:
                await processing_msg.edit_text(
                    rich_message=pyrogram.types.InputRichMessage(
                        markdown=(
                            f"{client.ns.emoji.md('cross_mark')} **Gagal!**\n\n"
                            f"{client.ns.table.md(['Info', 'Isi'], [['Status', 'Gagal menyimpan API'], ['Error', f'`{e}`']])}"
                        )
                    ),
                    reply_markup=back_btn,
                )
                return
        else:
            await client.send_rich_message(
                chat_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('cross_mark')} **Fitur Tidak Didukung**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Fitur tidak didukung'], ['Aksi', 'Kembali ke pengaturan']])}"
                    )
                ),
                reply_markup=back_btn,
            )
            return

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


@command(
    lambda ctx: filters.regex("^del_api_confirm$"),
    handler_type="callback",
)
async def confirm_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    confirm_rows = [
        ["Tindakan", "Hapus SEMUA kunci API"],
        ["Target", "Saweria Gateway"],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('exclamation')} **Konfirmasi**\n\n"
        f"{table.md(['Detail', 'Keterangan'], confirm_rows)}"
    )
    layout = [
        [
            {
                "text": "✅ Ya, Hapus Semua",
                "callback_data": "do_del_api",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": "❌ Tidak, Batalkan",
                "callback_data": "api_settings",
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


@command(
    lambda ctx: filters.regex("^do_del_api$"),
    handler_type="callback",
)
async def do_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    await ctx.db.removeVars(client.me.id, "SAWERIA_USER_ID")

    await callback_query.answer(
        "Semua kunci API untuk bot ini telah berhasil dihapus.",
        show_alert=True,
    )
    await api_settings_callback(client, callback_query)
