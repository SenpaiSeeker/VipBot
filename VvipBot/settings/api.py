import asyncio

from pyrogram import filters

from services import initialize_bot_services

from .. import command, ctx, is_bot_owner, listen


def _back_to_api_layout(client):
    return [
        [
            {
                "text": "• Kembali ke Pengaturan API •",
                "callback_data": "api_settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]


async def _reply(client, callback_query, text, btn):
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^api_settings$"),
    handler_type="callback",
)
async def api_settings_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID")
    saweria_status = (
        f"{client.ns.emoji.white_check_mark} Aktif"
        if saweria_user_id
        else f"{client.ns.emoji.cross_mark} Belum Diatur"
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
    text = (
        f"**{client.ns.emoji.key} Pengelola Kunci API untuk {client.me.mention}**\n\n"
        "Atur koneksi pembayaran Saweria untuk bot Anda.\n\n"
        "**Status Layanan:**\n"
        f"- `Gateway Pembayaran (Saweria)`: **{saweria_status}**\n\n"
        "Pilih tindakan:"
    )
    btn = client.ns.telegram.button.build_button_grid(layout)
    await _reply(client, callback_query, text, btn)


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

    back_btn = client.ns.telegram.button.build_button_grid(_back_to_api_layout(client))
    try:
        def ask(p):
            return client.ask(
                chat_id,
                f"{p}\n\nKetik `/batal` untuk membatalkan.",
                timeout=600,
            )

        if key_name == "SAWERIA":
            username_msg = await ask(f"**2/2:** Kirim **Username Saweria** Anda.")
            if username_msg.text and username_msg.text.lower() == "/batal":
                raise listen.UserCancelled

            processing_msg = await client.send_message(
                chat_id,
                f"{client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.",
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
                await client.send_message(
                    chat_id,
                    f"{client.ns.emoji.white_check_mark} **Sukses!**\nKunci Saweria berhasil disimpan.",
                    reply_markup=back_btn,
                )
            except Exception as e:
                await processing_msg.edit_text(
                    f"{client.ns.emoji.cross_mark} **Gagal!**\n`Error: {e}`",
                    reply_markup=back_btn,
                )
                return
        else:
            await client.send_message(
                chat_id,
                "Fitur tidak didukung.",
                reply_markup=back_btn,
            )
            return

        await initialize_bot_services(client, ctx.db)
    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
            reply_markup=back_btn,
        )


@command(
    lambda ctx: filters.regex("^del_api_confirm$"),
    handler_type="callback",
)
async def confirm_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    text = (
        f"**{client.ns.emoji.exclamation} Konfirmasi**\n\n"
        "Anda yakin ingin menghapus **SEMUA** kunci API?"
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
    await _reply(client, callback_query, text, btn)


@command(
    lambda ctx: filters.regex("^do_del_api$"),
    handler_type="callback",
)
async def do_delete_api_keys(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    await ctx.db.removeVars(client.me.id, "SAWERIA_USER_ID")
    await initialize_bot_services(client, ctx.db)

    await callback_query.answer(
        "Semua kunci API untuk bot ini telah berhasil dihapus.",
        show_alert=True,
    )
    await api_settings_callback(client, callback_query)