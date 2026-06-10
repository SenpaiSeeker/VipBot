import math
from zoneinfo import ZoneInfo

from telethon import events
from telethon.tl import functions

from .. import command, ctx, is_bot_owner


@command(
    lambda ctx: events.NewMessage(
        incoming=True,
        pattern=r"^/dashboard(\s|$)",
        func=lambda e: e.sender_id == ctx.owner_id,
    )
)
async def dashboard_command_handler(client, event):
    em = client.ns.emoji
    msg = await event.respond(
        f"{em.hourglass} <b>Sedang Memproses...</b>\nMohon tunggu sebentar.",
        parse_mode="html",
    )

    all_bots_data = await ctx.db.getBots(is_token=True)
    total_bots = len(all_bots_data)
    unique_users = set()
    bot_user_counts = {}

    for bot_data in all_bots_data:
        bot_id = int(bot_data["name"])
        user_ids = await ctx.db.getListVars(bot_id, "user_ids") or []
        bot_user_counts[bot_id] = len(user_ids)
        for user_id in user_ids:
            unique_users.add(user_id)

    total_users = len(unique_users)
    top_bot_id = (
        max(bot_user_counts, key=bot_user_counts.get) if bot_user_counts else None
    )
    top_bot_info = "N/A"

    if top_bot_id:
        top_bot_instance = ctx.manager.running_bots.get(top_bot_id)
        top_bot_name = f"ID {top_bot_id}"
        if top_bot_instance:
            top_bot_name = top_bot_instance.me.first_name
        top_bot_info = f"{top_bot_name} ({bot_user_counts[top_bot_id]} pengguna)"

    try:
        stats = await client.ns.server.monitor.get_detailed_stats()
        stats_data = {
            "cpu": stats.cpu["percent"],
            "ram": stats.ram["percent"],
            "disk": stats.disk["percent"],
        }
        server_stats_text = (
            f"- CPU: <code>[{stats.cpu['bar']}] {stats.cpu['percent']}%</code>\n"
            f"- RAM: <code>[{stats.ram['bar']}] {stats.ram['percent']}%</code>\n"
            f"- Disk: <code>[{stats.disk['bar']}] {stats.disk['percent']}%</code>"
        )
    except Exception as e:
        stats_data = {"cpu": 0, "ram": 0, "disk": 0}
        server_stats_text = f"Gagal mengambil statistik server: <code>{e}</code>"

    dashboard_text = (
        f"{em.chart_bar} <b>Dashboard Platform</b>\n\n"
        f"<b>Statistik Platform:</b>\n"
        f"- Total Bot Aktif: <code>{total_bots}</code>\n"
        f"- Total Pengguna Unik: <code>{total_users}</code>\n"
        f"- Bot Terpopuler: <code>{top_bot_info}</code>\n\n"
        f"<b>Kesehatan Server:</b>\n{server_stats_text}"
    )

    try:
        photo_stream = await client.ns.utils.dashboard.generate_dashboard(stats_data)
        await client.send_message(
            event.chat_id, dashboard_text, file=photo_stream, parse_mode="html"
        )
        await msg.delete()
    except Exception as e:
        await msg.edit(
            dashboard_text + f"\n\nError Visualisasi: {e}", parse_mode="html"
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^refund_stars_"))
async def refund_stars_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return await event.answer(
            "⛔ Anda tidak memiliki izin untuk melakukan ini.",
            alert=True,
        )

    payload = event.data.decode("utf-8")
    refund_key = payload.split("_")[2]
    db_key = f"refund_{refund_key}"
    bot_id = client.uid

    refund_data = await ctx.db.getVars(bot_id, db_key)

    if not refund_data:
        msg_obj = await event.get_message()
        return await event.edit(
            msg_obj.message
            + f"\n\n{em.anger} <b>Gagal: Transaksi tidak ditemukan atau sudah di-refund.</b>",
            parse_mode="html",
        )

    user_id_to_refund = refund_data["user_id"]
    charge_id = refund_data["charge_id"]

    try:
        await client(
            functions.payments.RefundStarsChargeRequest(
                user_id=await client.get_input_entity(user_id_to_refund),
                charge_id=charge_id,
            )
        )

        msg_obj = await event.get_message()
        await event.edit(
            msg_obj.message
            + f"\n\n{em.white_check_mark} Donasi berhasil dikembalikan.",
            parse_mode="html",
        )

        await client.send_message(
            user_id_to_refund,
            f"{em.bulb} <b>Informasi Donasi</b>\n\n"
            "Donasi Stars Anda telah dikembalikan oleh admin. Terima kasih atas pengertiannya.",
            parse_mode="html",
        )
    except Exception as e:
        ctx.log.print(f"Gagal merefund donasi: {e}")
        msg_obj = await event.get_message()
        await event.edit(
            msg_obj.message
            + f"\n\n{em.cross_mark} <b>Gagal mengembalikan donasi:</b>\n<code>{e}</code>",
            parse_mode="html",
        )
    finally:
        await ctx.db.removeVars(bot_id, db_key)


@command(lambda ctx: events.CallbackQuery(pattern=b"^stats_"))
async def show_stars_stats(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    payload = event.data.decode("utf-8")
    page = int(payload.split("_")[1])
    items_per_page = 5

    try:
        await event.answer("⏳ Memproses data transaksi...")

        peer = await client.get_input_entity("me")
        raw_result = await client(
            functions.payments.GetStarsTransactionsRequest(
                peer=peer,
                offset="",
                limit=200,
            )
        )

        transactions_history = (
            raw_result.history if hasattr(raw_result, "history") else []
        )
        layout = [[{"text": "◀️ Kembali ke Pengaturan", "callback_data": "settings", "style": "primary", "emoji": 5373098009640836781}]]
        btn = client.ns.telegram.button.build_button_grid(layout)

        if not transactions_history:
            return await event.edit(
                "Belum ada transaksi Stars yang tercatat.", buttons=btn
            )

        total_balance = (
            raw_result.balance.amount
            if hasattr(raw_result.balance, "amount")
            else raw_result.balance
        )
        total_income = sum(
            t.amount.amount for t in transactions_history if t.amount.amount > 0
        )
        total_refunds = sum(
            abs(t.amount.amount) for t in transactions_history if t.amount.amount < 0
        )
        total_transactions_count = len(transactions_history)

        users_list = raw_result.users if hasattr(raw_result, "users") else []
        chats_list = raw_result.chats if hasattr(raw_result, "chats") else []
        peer_map = {p.id: p for p in users_list + chats_list if hasattr(p, "id")}

        total_pages = math.ceil(total_transactions_count / items_per_page)
        paginated_transactions = transactions_history[
            page * items_per_page : (page + 1) * items_per_page
        ]

        jakarta_timezone = ZoneInfo("Asia/Jakarta")
        transactions_text_list = []

        for t in paginated_transactions:
            peer_id = None
            if hasattr(t.peer, "user_id"):
                peer_id = t.peer.user_id
            elif hasattr(t.peer, "channel_id"):
                peer_id = t.peer.channel_id

            peer_obj = peer_map.get(peer_id) if peer_id else None
            peer_mention = "sumber tidak dikenal"

            if peer_obj:
                if hasattr(peer_obj, "first_name"):
                    peer_mention = peer_obj.first_name
                elif hasattr(peer_obj, "title"):
                    peer_mention = peer_obj.title

            amount = t.amount.amount
            amount_str = f"+{amount}" if amount > 0 else str(amount)
            transaction_date = t.date.astimezone(jakarta_timezone)

            transactions_text_list.append(
                f"• <code>{transaction_date.strftime('%d %b, %H:%M %Z')}</code>: "
                f"<b>{amount_str}{em.glowing_star}</b> dari {peer_mention}"
            )

        text = (
            f"{em.chart_bar} <b>Statistik Pendapatan Stars</b>\n\n"
            f"{em.money_bag} <b>Saldo Saat Ini:</b> <code>{total_balance}</code> {em.glowing_star}\n"
            f"{em.chart_up} <b>Total Pemasukan:</b> <code>{total_income}</code> {em.glowing_star}\n"
            f"{em.chart_down} <b>Total Pengembalian:</b> <code>{total_refunds}</code> {em.glowing_star}\n"
            f"{em.repeat} <b>Total Transaksi (Tampil):</b> <code>{total_transactions_count}</code>\n\n"
            f"{em.open_book} <b>Transaksi Terakhir ({page + 1}/{total_pages})</b>\n"
            + "\n".join(transactions_text_list)
        )

        layout = []
        if total_pages > 1:
            prev_page = page - 1 if page > 0 else total_pages - 1
            next_page = page + 1 if page < total_pages - 1 else 0
            layout.append(
                [
                    {"text": "« Sebelumnya", "callback_data": f"stats_{prev_page}", "style": "primary", "emoji": 5373098009640836781},
                    {"text": "Selanjutnya »", "callback_data": f"stats_{next_page}", "style": "primary", "emoji": 5373098009640836781},
                ]
            )

        layout.append(
            [{"text": "◀️ Kembali ke Pengaturan", "callback_data": "settings", "style": "primary", "emoji": 5373098009640836781}]
        )
        btn = client.ns.telegram.button.build_button_grid(layout)

        await event.edit(text, buttons=btn, parse_mode="html")

    except Exception as e:
        ctx.log.print(f"Error fetching stars stats: {e}")
        await event.answer(f"Error: {e}", alert=True)


@command(lambda ctx: events.CallbackQuery(pattern=b"^total_users_count$"))
async def total_users_count_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return await event.answer(
            "⛔ Anda tidak memiliki akses ke menu ini.", alert=True
        )

    user_ids = await ctx.db.getListVars(client.uid, "user_ids") or []
    text = (
        f"{em.busts_in_silhouette} <b>Total Pengguna Bot</b>\n\n"
        f"Jumlah keseluruhan pengguna yang pernah memulai bot ini adalah: "
        f"<b>{len(user_ids)} pengguna</b>."
    )

    markup = client.ns.telegram.button.build_button_grid(
        [[{"text": "◀️ Kembali ke Pengaturan", "callback_data": "settings", "style": "primary", "emoji": 5373098009640836781}]]
    )

    await event.edit(text, buttons=markup, parse_mode="html")
