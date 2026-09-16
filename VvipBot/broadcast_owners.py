from . import *


@command(lambda ctx: filters.command("broadcast_owners") & filters.user(ctx.owner_id))
async def broadcast_owners_handler(client, message):
    broadcast_msg = client.ns.telegram.arg.getMessage(message)
    if not broadcast_msg:
        return await message.reply_text(
            "Gunakan: `/broadcast_owners <pesan>` atau balas ke sebuah pesan."
        )
    all_bots_data = await ctx.db.getBots(is_token=True)
    owner_ids = set()
    for bot in all_bots_data:
        owner_id = await ctx.db.getVars(int(bot["name"]), "owner_id")
        if owner_id:
            owner_ids.add(owner_id)
    if not owner_ids:
        return await message.reply_text("Tidak ada pemilik bot yang bisa di-broadcast.")

    total_owners = len(owner_ids)
    progress_msg = await message.reply_text(
        f"{client.ns.emoji.white_check_mark} Memulai siaran ke `{total_owners}` pengguna..."
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
        f"**{client.ns.emoji.loudspeaker} Siaran Selesai!**\n"
        f"{client.ns.emoji.white_check_mark} **Terkirim:** `{success_count}`\n"
        f"{client.ns.emoji.cross_mark} **Gagal:** `{fail_count}`"
    )
