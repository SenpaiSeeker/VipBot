from datetime import datetime, timedelta, timezone

import pyrogram
from pyrogram import filters

from helpers import parse_dt

from .. import command, ctx


@command(
    lambda ctx: filters.regex("^request_extend_duration\\s(\\d+)"),
    handler_type="callback",
)
async def request_extend_duration_callback(client, callback_query):
    bot_id_to_request = int(callback_query.data.split(" ", 1)[1])
    requester = callback_query.from_user
    bot_name = f"ID {bot_id_to_request}"

    try:
        bot_instance = ctx.manager.running_bots.get(bot_id_to_request)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    try:
        main_bot_client = ctx.manager.main_bot_client
        if not main_bot_client or not main_bot_client.is_connected:
            raise ConnectionError(
                "Bot utama sedang tidak aktif, tidak dapat mengirim notifikasi."
            )

        requester_name = (
            requester.full_name or requester.first_name or "Deleted Account"
        )
        requester_mention = f"[{requester_name}](tg://user?id={requester.id})"
        txt_owner = (
            f"**{main_bot_client.ns.emoji.md('bell')} Permintaan Perpanjangan Durasi**\n\n"
            f"**Pengguna:** {requester_mention} (`{requester.id}`)\n"
            f"**Bot:** **{bot_name}** (`{bot_id_to_request}`)\n\n"
            f"Setujui untuk menambah masa aktif bot ini sebanyak 30 hari."
        )

        layout_owner = [
            [
                {
                    "text": "✅ Setujui (+30 Hari)",
                    "callback_data": f"approve_extension {bot_id_to_request} {requester.id}",
                    "style": "green",
                    "emoji": main_bot_client.ns.emoji.id("white_check_mark"),
                },
                {
                    "text": "❌ Tolak Permintaan",
                    "callback_data": f"close_req {bot_id_to_request} {requester.id}",
                    "style": "red",
                    "emoji": main_bot_client.ns.emoji.id("cross_mark"),
                },
            ]
        ]
        btn_owner = main_bot_client.ns.telegram.button.build_button_grid(layout_owner)

        await main_bot_client.send_rich_message(
            ctx.owner_id,
            pyrogram.types.InputRichMessage(markdown=txt_owner),
            reply_markup=btn_owner,
        )
        await callback_query.answer(
            "✅ Permintaan perpanjangan telah dikirim ke Owner Utama. Anda akan dihubungi jika disetujui.",
            show_alert=True,
        )
    except Exception as e:
        await callback_query.answer(
            f"❌ Gagal mengirim permintaan ke Owner: {e}",
            show_alert=True,
        )


@command(
    lambda ctx: filters.regex("^approve_extension\\s(\\d+)\\s(\\d+)"),
    handler_type="callback",
)
async def owner_approve_extension_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa menyetujui permintaan ini.",
            show_alert=True,
        )

    try:
        _, bot_id_str, requester_id_str = callback_query.data.split()
        bot_id_to_extend, requester_id, days_to_add = (
            int(bot_id_str),
            int(requester_id_str),
            30,
        )

        exp_date_str = await ctx.db.getVars(bot_id_to_extend, "bot_expiration_date")
        current_exp_date = (
            parse_dt(exp_date_str)
            if exp_date_str
            else datetime.now(timezone.utc)
        )

        new_exp_date = current_exp_date + timedelta(days=days_to_add)
        await ctx.db.setVars(
            bot_id_to_extend,
            "bot_expiration_date",
            new_exp_date.isoformat(),
        )

        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Persetujuan Berhasil!**\n"
                    f"Durasi untuk bot `{bot_id_to_extend}` telah ditambah **{days_to_add} hari**."
                )
            )
        )

        try:
            bot_instance = ctx.manager.running_bots.get(bot_id_to_extend)
            bot_name = (
                bot_instance.me.first_name
                if bot_instance and bot_instance.is_connected
                else f"ID {bot_id_to_extend}"
            )

            await client.send_rich_message(
                requester_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('party_popper')} **Kabar Baik!**\n\n"
                        f"Permintaan perpanjangan Anda untuk bot **{bot_name}** telah disetujui dan diperpanjang."
                    )
                ),
            )
        except Exception as e:
            ctx.log.print(f"Gagal kirim notif persetujuan ke {requester_id}: {e}")
    except Exception as e:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} Gagal menyetujui permintaan: `{e}`"
            )
        )


@command(
    lambda ctx: filters.regex("^close_req\\s(\\d+)\\s(\\d+)"),
    handler_type="callback",
)
async def owner_close_request_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa melakukan ini.",
            show_alert=True,
        )

    try:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} Permintaan telah ditolak/ditutup oleh Owner Utama."
            )
        )
    except Exception:
        pass
