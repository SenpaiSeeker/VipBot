from datetime import datetime, timedelta, timezone

import pyrogram
from pyrogram import filters

from .. import command, ctx

EXTEND_DAYS = 30


async def _get_bot_display_name(client, bot_id: int) -> str:
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            return bot_instance.me.first_name
    except Exception:
        pass
    return f"ID {bot_id}"


@command(
    lambda ctx: filters.regex("^request_extend_duration\\s(\\d+)"),
    handler_type="callback",
)
async def request_extend_duration_callback(client, callback_query):
    bot_id_to_request = int(callback_query.data.split(" ", 1)[1])
    requester = callback_query.from_user
    bot_name = await _get_bot_display_name(client, bot_id_to_request)

    try:
        main_bot_client = ctx.manager.main_bot_client
        if not main_bot_client or not main_bot_client.is_connected:
            raise ConnectionError(
                "Bot utama sedang tidak aktif, tidak dapat mengirim notifikasi."
            )

        requester_mention = main_bot_client.ns.telegram.arg.getMention(requester)
        txt_owner = (
            f"**{main_bot_client.ns.emoji.bell} Permintaan Perpanjangan Durasi**\n\n"
            f"**Pengguna:** {requester_mention} (`{requester.id}`)\n"
            f"**Bot:** **{bot_name}** (`{bot_id_to_request}`)\n\n"
            f"Setujui untuk menambah masa aktif bot ini sebanyak {EXTEND_DAYS} hari."
        )
        layout_owner = [
            [
                {
                    "text": f"✅ Setujui (+{EXTEND_DAYS} Hari)",
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
        await main_bot_client.send_message(
            ctx.owner_id, txt_owner, reply_markup=btn_owner
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
        bot_id_to_extend = int(bot_id_str)
        requester_id = int(requester_id_str)

        exp_date_str = await ctx.db.getVars(bot_id_to_extend, "bot_expiration_date")
        current_exp_date = (
            datetime.fromisoformat(exp_date_str)
            if exp_date_str
            else datetime.now(timezone.utc)
        )
        new_exp_date = current_exp_date + timedelta(days=EXTEND_DAYS)
        await ctx.db.setVars(
            bot_id_to_extend,
            "bot_expiration_date",
            new_exp_date.isoformat(),
        )

        await callback_query.edit_message_text(
            f"{client.ns.emoji.white_check_mark} **Persetujuan Berhasil!**\n"
            f"Durasi untuk bot `{bot_id_to_extend}` telah ditambah **{EXTEND_DAYS} hari**."
        )

        try:
            bot_instance = ctx.manager.running_bots.get(bot_id_to_extend)
            bot_name = (
                bot_instance.me.first_name
                if bot_instance and bot_instance.is_connected
                else f"ID {bot_id_to_extend}"
            )
            await client.send_message(
                requester_id,
                f"{client.ns.emoji.party_popper} **Kabar Baik!**\n\n"
                f"Permintaan perpanjangan Anda untuk bot **{bot_name}** telah disetujui dan diperpanjang.",
            )
        except Exception as e:
            ctx.log.print(f"Gagal kirim notif persetujuan ke {requester_id}: {e}")
    except Exception as e:
        await callback_query.edit_message_text(
            f"{client.ns.emoji.cross_mark} Gagal menyetujui permintaan: `{e}`"
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
            f"{client.ns.emoji.cross_mark} Permintaan telah ditolak/ditutup oleh Owner Utama."
        )
    except Exception:
        pass