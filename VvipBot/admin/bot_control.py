from helpers import parse_dt

import pyrogram

from .. import *


@command(lambda ctx: filters.command("extend") & filters.user(ctx.owner_id))
async def extend_command_handler(client, message):
    bot_id, days_str = await client.ns.telegram.arg.getReasonAndId(message)
    if not bot_id or not days_str:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Gunakan', '`/extend <bot_id/@username> <jumlah_hari>` atau reply ke pesan bot'], ['Contoh', '`/extend 12345678 30` atau `/extend @namabot 30`']])}"
                )
            )
        )
    try:
        days_to_add = int(days_str.strip())
    except ValueError:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Detail', '`jumlah_hari` harus berupa angka bulat'], ['Contoh', '`/extend 12345678 30`']])}"
                )
            )
        )
    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    current_exp_date = (
        parse_dt(exp_date_str)
        if exp_date_str
        else datetime.now(timezone.utc)
    )
    new_exp_date = current_exp_date + timedelta(days=days_to_add)
    await ctx.db.setVars(bot_id, "bot_expiration_date", new_exp_date.isoformat())

    formatted_new_date = new_exp_date.strftime("%d %b %Y")
    await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=f"{client.ns.emoji.md('white_check_mark')} **Sukses!** Durasi bot `{bot_id}` berhasil diubah. Masa aktif baru: `{formatted_new_date}`."
        )
    )
    owner_bot_id = await ctx.db.getVars(bot_id, "owner_id")
    if owner_bot_id:
        try:
            bot_instance = ctx.manager.running_bots.get(bot_id)
            bot_name = bot_instance.me.first_name if bot_instance else f"ID {bot_id}"
            await client.send_rich_message(
                owner_bot_id,
                pyrogram.types.InputRichMessage(
                    markdown=f"{client.ns.emoji.md('party_popper')} **Kabar Baik!**\n\nMasa aktif bot Anda **{bot_name}** telah diperpanjang oleh Owner Utama."
                ),
            )
        except Exception:
            pass


@command(lambda ctx: filters.command("broadcast_owners") & filters.user(ctx.owner_id))
async def broadcast_owners_handler(client, message):
    broadcast_msg = client.ns.telegram.arg.getMessage(message)
    if not broadcast_msg:
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Gunakan', '`/broadcast_owners <pesan>` atau balas ke sebuah pesan']])}"
                )
            )
        )
    all_bots_data = await ctx.db.getBots(is_token=True)
    owner_ids = set()
    for bot in all_bots_data:
        owner_id = await ctx.db.getVars(int(bot["name"]), "owner_id")
        if owner_id:
            owner_ids.add(owner_id)
    if not owner_ids:
        empty_rows = [
            ["Jumlah Pemilik Bot", "`0`"],
            ["Status", "Tidak ada pemilik bot terdaftar"],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Broadcast ke Pemilik Bot**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], empty_rows)}"
                )
            )
        )

    total_owners = len(owner_ids)
    progress_msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('white_check_mark')} **Memulai Siaran**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Siaran dimulai'], ['Jumlah', f'`{total_owners}` pengguna']])}"
            )
        )
    )
    success_count = 0
    fail_count = 0
    for owner_id in owner_ids:
        try:
            await broadcast_msg.copy(owner_id)
            success_count += 1
        except Exception as e:
            ctx.log.print(f"{ctx.log.RED}Gagal broadcast ke owner {owner_id}: {e}")
            fail_count += 1
        await asyncio.sleep(0.2)

    await progress_msg.edit(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=f"**{client.ns.emoji.md('loudspeaker')} Siaran Selesai!**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Selesai'], ['Terkirim', f'`{success_count}`'], ['Gagal', f'`{fail_count}`']])}"
        )
    )
