from helpers import parse_dt

import pyrogram

from .. import *


@command(lambda ctx: filters.command("extend") & filters.user(ctx.owner_id))
async def extend_command_handler(client, message):
    bot_id = client.me.id
    text, btn = await build_extend_panel(client, bot_id)
    return await message.reply_rich(
        pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def build_extend_panel(client, bot_id):
    try:
        bot_id = int(bot_id)
    except (TypeError, ValueError):
        pass
    bot_instance = ctx.manager.running_bots.get(bot_id)
    if bot_id == client.me.id:
        bot_name = client.me.first_name
    elif bot_instance and bot_instance.me:
        bot_name = bot_instance.me.first_name
    else:
        bot_name = f"ID {bot_id}"

    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    current_exp_date = parse_dt(exp_date_str) if exp_date_str else None
    expiry_text = (
        f"`{current_exp_date.strftime('%d %b %Y')}`"
        if current_exp_date
        else "Belum diatur"
    )

    text = (
        f"{client.ns.emoji.md('calendar')} **Perpanjang Masa Aktif**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', f'**{bot_name}** (`{bot_id}`)'], ['Masa Aktif', f'{expiry_text}'], ['Pilih', 'Tambah 1-12 bulan (1 bulan = 30 hari)']])}"
    )

    layout = []
    row = []
    for m in range(1, 13):
        row.append(
            {
                "text": f"{m} Bulan",
                "callback_data": f"extend_month_{bot_id}_{m}",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            }
        )
        if len(row) == 3:
            layout.append(row)
            row = []
    if row:
        layout.append(row)

    btn = client.ns.telegram.button.build_button_grid(layout)
    return text, btn


async def apply_extend_duration(client, bot_id, days_to_add):
    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    current_exp_date = (
        parse_dt(exp_date_str)
        if exp_date_str
        else datetime.now(timezone.utc)
    )
    new_exp_date = current_exp_date + timedelta(days=days_to_add)
    await ctx.db.setVars(bot_id, "bot_expiration_date", new_exp_date.isoformat())
    return new_exp_date.strftime("%d %b %Y")


async def notify_extend_owner(client, bot_id):
    owner_bot_id = await ctx.db.getVars(bot_id, "owner_id")
    if not owner_bot_id:
        return
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        bot_name = bot_instance.me.first_name if bot_instance else f"ID {bot_id}"
        await client.send_rich_message(
            owner_bot_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('party_popper')} **Kabar Baik!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', f'**{bot_name}**'], ['Status', 'Masa aktif bot Anda telah diperpanjang oleh Owner Utama']])}"
                )
            ),
        )
    except Exception:
        pass


@command(
    lambda ctx: filters.regex("^extend_month_(\\d+)_(\\d+)$"),
    handler_type="callback",
)
async def extend_month_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )
    bot_id = int(callback_query.matches[0].group(1))
    months = int(callback_query.matches[0].group(2))
    days_to_add = months * 30

    formatted_new_date = await apply_extend_duration(client, bot_id, days_to_add)
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', f'`{bot_id}`'], ['Tambahan', f'`{months}` bulan (`{days_to_add}` hari)'], ['Masa Aktif Baru', f'`{formatted_new_date}`']])}"
            )
        )
    )
    await notify_extend_owner(client, bot_id)


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
