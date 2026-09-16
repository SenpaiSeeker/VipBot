from pyrogram import filters

from .. import command, ctx


@command(
    lambda ctx: filters.regex("^confirm_delete_bot\\s(\\d+)"),
    handler_type="callback",
)
async def confirm_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    bot_name = f"ID {bot_id_to_manage}"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_manage)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    text = (
        f"**{client.ns.emoji.exclamation} Konfirmasi Penghapusan**\n\n"
        f"Anda yakin ingin menghapus bot **{bot_name}** (`{bot_id_to_manage}`) secara permanen?\n\n"
        f"__Semua data (member, paket, pengaturan) bot ini akan hilang dan tindakan ini tidak dapat diurungkan.__"
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

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^do_delete_bot\\s(\\d+)"),
    handler_type="callback",
)
async def do_delete_bot_callback(client, callback_query):
    bot_id_to_manage = int(callback_query.data.split(" ", 1)[1])
    user_id = callback_query.from_user.id
    owner_of_target_bot = await ctx.db.getVars(bot_id_to_manage, "owner_id") or 0

    if user_id != owner_of_target_bot and user_id != ctx.owner_id:
        return await callback_query.answer(
            "Anda tidak berhak menghapus bot ini.",
            show_alert=True,
        )

    await callback_query.edit_message_caption(
        f"{client.ns.emoji.hourglass} Sedang menghentikan dan menghapus bot `{bot_id_to_manage}`..."
    )

    try:
        await ctx.manager.stop_bot(bot_id_to_manage)
        await ctx.db.removeBot(bot_id_to_manage)
        await ctx.db.removeAllVars(bot_id_to_manage)

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

        await callback_query.edit_message_caption(
            f"{client.ns.emoji.white_check_mark} **Penghapusan Berhasil!**\n"
            f"Bot `{bot_id_to_manage}` beserta datanya telah dihapus dari sistem.",
            reply_markup=btn,
        )

    except Exception as e:
        await callback_query.edit_message_caption(
            f"{client.ns.emoji.cross_mark} Terjadi kesalahan saat menghapus bot: `{e}`"
        )
