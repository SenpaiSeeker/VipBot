from telethon import events
from .. import command, ctx


@command(lambda ctx: events.CallbackQuery(pattern=b"^allbots_duration_"))
async def allbots_duration_callback(client, event):
    em = client.ns.emoji
    payload = event.data.decode("utf-8")
    bot_id = int(payload.split("_")[2])

    layout = [
        [
            {"text": "➕ Tambah Masa Aktif", "callback_data": f"allbots_extend_{bot_id}", "style": "success", "emoji": 5226945370684140473},
            {"text": "➖ Kurangi Masa Aktif", "callback_data": f"allbots_reduce_{bot_id}", "style": "danger",  "emoji": 5229113891081956317},
        ],
        [{"text": "◀️ Kembali", "callback_data": f"allbots_detail_{bot_id}_0", "style": "primary", "emoji": 5373098009640836781}],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(
        f"{em.hourglass} <b>Kelola Masa Aktif Bot</b>\n\n"
        f"Bot ID: <code>{bot_id}</code>\n\n"
        f"Pilih tindakan yang ingin dilakukan:",
        buttons=btn,
        parse_mode="html",
    )


@command(lambda ctx: events.CallbackQuery(pattern=b"^allbots_extend_"))
async def allbots_extend_callback(client, event):
    em = client.ns.emoji
    payload = event.data.decode("utf-8")
    bot_id = int(payload.split("_")[2])

    day_options = [1, 3, 7, 14, 30, 60, 90, 180, 365]
    layout = []
    row = []

    for days in day_options:
        row.append({
            "text": f"➕{days} hari",
            "callback_data": f"allbots_do_extend_{bot_id}_{days}",
            "style": "success",
            "emoji": 5226945370684140473,
        })
        if len(row) == 3:
            layout.append(row)
            row = []

    if row:
        layout.append(row)

    layout.append([{"text": "◀️ Kembali", "callback_data": f"allbots_duration_{bot_id}", "style": "primary", "emoji": 5373098009640836781}])
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit(
        f"{em.hourglass} <b>Tambah Masa Aktif</b>\n\nBot ID: <code>{bot_id}</code>",
        buttons=btn,
        parse_mode="html",
    )


@command(lambda ctx: events.CallbackQuery(pattern=b"^allbots_do_extend_"))
async def allbots_do_extend_callback(client, event):
    em = client.ns.emoji
    payload = event.data.decode("utf-8")
    parts = payload.split("_")
    bot_id = int(parts[3])
    days = int(parts[4])

    from datetime import datetime, timedelta, timezone
    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    current_exp = (
        datetime.fromisoformat(exp_date_str)
        if exp_date_str
        else datetime.now(timezone.utc)
    )
    new_exp = current_exp + timedelta(days=days)
    await ctx.db.setVars(bot_id, "bot_expiration_date", new_exp.isoformat())

    await event.answer(f"✅ {days} hari berhasil ditambahkan ke bot {bot_id}.", alert=True)
    event.data = f"allbots_duration_{bot_id}".encode("utf-8")
    await allbots_duration_callback(client, event)


@command(lambda ctx: events.CallbackQuery(pattern=b"^allbots_reduce_"))
async def allbots_reduce_callback(client, event):
    em = client.ns.emoji
    payload = event.data.decode("utf-8")
    bot_id = int(payload.split("_")[2])

    day_options = [1, 3, 7, 14, 30, 60, 90, 180, 365]
    layout = []
    row = []

    for days in day_options:
        row.append({
            "text": f"➖{days} hari",
            "callback_data": f"allbots_do_reduce_{bot_id}_{days}",
            "style": "danger",
            "emoji": 5229113891081956317,
        })
        if len(row) == 3:
            layout.append(row)
            row = []

    if row:
        layout.append(row)

    layout.append([{"text": "◀️ Kembali", "callback_data": f"allbots_duration_{bot_id}", "style": "primary", "emoji": 5373098009640836781}])
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit(
        f"{em.hourglass} <b>Kurangi Masa Aktif</b>\n\nBot ID: <code>{bot_id}</code>",
        buttons=btn,
        parse_mode="html",
    )


@command(lambda ctx: events.CallbackQuery(pattern=b"^allbots_do_reduce_"))
async def allbots_do_reduce_callback(client, event):
    em = client.ns.emoji
    payload = event.data.decode("utf-8")
    parts = payload.split("_")
    bot_id = int(parts[3])
    days = int(parts[4])

    from datetime import datetime, timedelta, timezone
    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    current_exp = (
        datetime.fromisoformat(exp_date_str)
        if exp_date_str
        else datetime.now(timezone.utc)
    )
    new_exp = current_exp - timedelta(days=days)
    await ctx.db.setVars(bot_id, "bot_expiration_date", new_exp.isoformat())

    await event.answer(f"✅ Masa aktif bot {bot_id} berhasil dikurangi {days} hari.", alert=True)
    event.data = f"allbots_duration_{bot_id}".encode("utf-8")
    await allbots_duration_callback(client, event)
