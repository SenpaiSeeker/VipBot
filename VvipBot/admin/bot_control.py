import asyncio
from datetime import datetime, timedelta, timezone

from telethon import events

from .. import command, ctx


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/extend(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def extend_command_handler(client, event):
    bot_id, days_str = await client.ns.telegram.arg.getReasonAndId(event)

    em = client.ns.emoji

    if not bot_id or not days_str:
        return await event.respond(
            f"{em.cross_mark} <b>Format salah.</b>\n"
            f"Gunakan: <code>/extend &lt;bot_id/@username&gt; &lt;jumlah_hari&gt;</code> atau reply ke pesan bot.\n"
            f"Contoh: <code>/extend 12345678 30</code> atau <code>/extend @namabot 30</code>",
            parse_mode="html",
        )

    try:
        days_to_add = int(days_str.strip())
    except ValueError:
        return await event.respond(
            f"{em.cross_mark} <b>Format salah.</b> <code>jumlah_hari</code> harus berupa angka bulat.\n"
            f"Contoh: <code>/extend 12345678 30</code>",
            parse_mode="html",
        )

    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    current_exp_date = (
        datetime.fromisoformat(exp_date_str)
        if exp_date_str
        else datetime.now(timezone.utc)
    )
    new_exp_date = current_exp_date + timedelta(days=days_to_add)

    await ctx.db.setVars(bot_id, "bot_expiration_date", new_exp_date.isoformat())

    await event.respond(
        f"{em.white_check_mark} <b>Sukses!</b> Durasi bot <code>{bot_id}</code> berhasil diubah. "
        f"Masa aktif baru: <code>{new_exp_date.strftime('%d %b %Y')}</code>.",
        parse_mode="html",
    )

    owner_bot_id = await ctx.db.getVars(bot_id, "owner_id")

    if owner_bot_id:
        try:
            bot_instance = ctx.manager.running_bots.get(bot_id)
            bot_name = f"ID {bot_id}"
            if bot_instance:
                bot_name = bot_instance.me.first_name

            await client.send_message(
                owner_bot_id,
                f"{em.party_popper} <b>Kabar Baik!</b>\n\n"
                f"Masa aktif bot Anda <b>{bot_name}</b> telah diperpanjang oleh Owner Utama.",
                parse_mode="html",
            )
        except Exception:
            pass


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/broadcast_owners(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def broadcast_owners_handler(client, event):
    broadcast_msg = await client.ns.telegram.arg.getMessage(event)
    em = client.ns.emoji

    if not broadcast_msg:
        return await event.respond(
            f"Gunakan: <code>/broadcast_owners &lt;pesan&gt;</code> atau balas ke sebuah pesan.",
            parse_mode="html",
        )

    all_bots_data = await ctx.db.getBots(is_token=True)
    owner_ids = set()

    for bot in all_bots_data:
        owner_id = await ctx.db.getVars(int(bot["name"]), "owner_id")
        if owner_id:
            owner_ids.add(owner_id)

    if not owner_ids:
        return await event.respond("Tidak ada pemilik bot yang bisa di-broadcast.")

    progress_msg = await event.respond(
        f"{em.white_check_mark} Memulai siaran ke <code>{len(owner_ids)}</code> pengguna...",
        parse_mode="html",
    )

    success_count = 0
    fail_count = 0

    for owner_id in owner_ids:
        try:
            if isinstance(broadcast_msg, str):
                await client.send_message(owner_id, broadcast_msg, parse_mode="html")
            else:
                await client.forward_messages(owner_id, broadcast_msg, drop_author=True)
            success_count += 1
        except Exception as e:
            ctx.log.print(f"Gagal broadcast ke owner {owner_id}: {e}")
            fail_count += 1
        await asyncio.sleep(0.2)

    await progress_msg.edit(
        f"{em.loudspeaker} <b>Siaran Selesai!</b>\n"
        f"{em.white_check_mark} <b>Terkirim:</b> <code>{success_count}</code>\n"
        f"{em.cross_mark} <b>Gagal:</b> <code>{fail_count}</code>",
        parse_mode="html",
    )
