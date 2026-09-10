from .. import *

ITEMS_PER_PAGE = 5
JAKARTA_TIMEZONE = ZoneInfo("Asia/Jakarta")


def _back_to_settings_layout(client):
    return [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("key"),
            }
        ]
    ]


async def _reply(client, callback_query, text, btn):
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


async def _collect_platform_stats(client):
    all_bots_data = await ctx.db.getBots(is_token=True)
    total_bots = len(all_bots_data)
    unique_users = set()
    bot_user_counts = {}
    for bot_data in all_bots_data:
        bot_id = int(bot_data["name"])
        user_ids = await ctx.db.getListVars(bot_id, "user_ids") or []
        bot_user_counts[bot_id] = len(user_ids)
        unique_users.update(user_ids)

    top_bot_info = "N/A"
    if bot_user_counts:
        top_bot_id = max(bot_user_counts, key=bot_user_counts.get)
        top_bot_instance = ctx.manager.running_bots.get(top_bot_id)
        top_bot_name = (
            top_bot_instance.me.first_name if top_bot_instance else f"ID {top_bot_id}"
        )
        top_bot_info = f"{top_bot_name} ({bot_user_counts[top_bot_id]} pengguna)"

    return total_bots, len(unique_users), top_bot_info


async def _gather_server_stats(client):
    try:
        stats = await client.ns.server.monitor.get_detailed_stats()
        stats_data = {
            "cpu": stats.cpu["percent"],
            "ram": stats.ram["percent"],
            "disk": stats.disk["percent"],
        }
        server_stats_text = (
            f"- CPU: `[{stats.cpu['bar']}] {stats.cpu['percent']}%`\n"
            f"- RAM: `[{stats.ram['bar']}] {stats.ram['percent']}%`\n"
            f"- Disk: `[{stats.disk['bar']}] {stats.disk['percent']}%`"
        )
    except Exception as e:
        stats_data = {"cpu": 0, "ram": 0, "disk": 0}
        server_stats_text = f"Gagal mengambil statistik server: `{e}`"
    return stats_data, server_stats_text


@command(lambda ctx: filters.command("dashboard") & filters.user(ctx.owner_id))
async def dashboard_command_handler(client, message):
    msg = await message.reply_text(
        f"{client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar."
    )
    total_bots, total_users, top_bot_info = await _collect_platform_stats(client)
    stats_data, server_stats_text = await _gather_server_stats(client)

    dashboard_text = (
        f"**{client.ns.emoji.chart_bar} Dashboard Platform**\n\n"
        f"**Statistik Platform:**\n"
        f"- Total Bot Aktif: `{total_bots}`\n"
        f"- Total Pengguna Unik: `{total_users}`\n"
        f"- Bot Terpopuler: `{top_bot_info}`\n\n"
        f"**Kesehatan Server:**\n{server_stats_text}"
    )
    try:
        photo_stream = await client.ns.utils.dashboard.generate_dashboard(stats_data)
        await message.reply_photo(photo=photo_stream, caption=dashboard_text)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(dashboard_text + f"\n\nError Visualisasi: {e}")


@command(lambda ctx: filters.regex("^refund_stars_"), handler_type="callback")
async def refund_stars_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki izin untuk melakukan ini.", show_alert=True
        )
    db_key = ""
    try:
        refund_key = callback_query.data.split("_")[2]
        db_key = f"refund_{refund_key}"
        refund_data = await ctx.db.getVars(client.me.id, db_key)
        if not refund_data:
            await callback_query.edit_message_text(
                f"{callback_query.message.text}\n\n{client.ns.emoji.exclamation} **Gagal: Transaksi tidak ditemukan atau sudah di-refund.**"
            )
            return
        user_id_to_refund = refund_data["user_id"]
        charge_id = refund_data["charge_id"]
        await client.refund_star_payment(
            user_id=user_id_to_refund, telegram_payment_charge_id=charge_id
        )
        await callback_query.edit_message_text(
            text=f"{callback_query.message.text}\n\n{client.ns.emoji.white_check_mark} Donasi berhasil dikembalikan.",
            entities=callback_query.message.entities,
        )
        await client.send_message(
            user_id_to_refund,
            "ℹ️ **Informasi Donasi**\n\nDonasi Stars Anda telah dikembalikan oleh admin. Terima kasih atas pengertiannya.",
        )
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal merefund donasi: {e}")
        await callback_query.edit_message_text(
            f"{callback_query.message.text}\n\n{client.ns.emoji.cross_mark} **Gagal mengembalikan donasi:**\n`{e}`"
        )
    finally:
        if db_key:
            await ctx.db.removeVars(client.me.id, db_key)


def _describe_peer(peer_obj):
    if peer_obj and hasattr(peer_obj, "first_name"):
        return peer_obj.first_name
    return peer_obj.title if peer_obj else "sumber tidak dikenal"


@command(lambda ctx: filters.regex("^stats_(\\d+)"), handler_type="callback")
async def show_stars_stats(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    page = int(callback_query.data.split("_")[1])
    try:
        await callback_query.answer(
            "<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar."
        )
        peer = await client.resolve_peer(client.me.id)
        raw_result = await client.invoke(
            pyrogram.raw.functions.payments.GetStarsTransactions(
                peer=peer, offset="", limit=200
            )
        )
        transactions_history = (
            raw_result.history if hasattr(raw_result, "history") else []
        )
        if not transactions_history:
            text = "Belum ada transaksi Stars yang tercatat."
            btn = client.ns.telegram.button.build_button_grid(
                _back_to_settings_layout(client)
            )
            return await _reply(client, callback_query, text, btn)

        total_balance = raw_result.balance.amount
        total_income = sum(
            t.amount.amount for t in transactions_history if t.amount.amount > 0
        )
        total_refunds = sum(
            abs(t.amount.amount) for t in transactions_history if t.amount.amount < 0
        )
        total_transactions_count = len(transactions_history)
        peer_map = {p.id: p for p in raw_result.users + raw_result.chats}
        total_pages = math.ceil(total_transactions_count / ITEMS_PER_PAGE)
        paginated = transactions_history[
            page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE
        ]

        transactions_text_list = []
        for t in paginated:
            peer_id = (
                t.peer.peer.user_id
                if hasattr(t.peer.peer, "user_id")
                else t.peer.peer.channel_id
            )
            peer_mention = _describe_peer(peer_map.get(peer_id))
            amount = t.amount.amount
            amount_str = f"+{amount}" if amount > 0 else str(amount)
            transaction_date = datetime.fromtimestamp(
                t.date, tz=timezone.utc
            ).astimezone(JAKARTA_TIMEZONE)
            transactions_text_list.append(
                f"• `{transaction_date.strftime('%d %b, %H:%M %Z')}`: **{amount_str}{client.ns.emoji.star}** dari {peer_mention}"
            )

        history_details = "\n".join(transactions_text_list)
        text = (
            f"**{client.ns.emoji.chart_bar} Statistik Pendapatan Stars**\n\n"
            f"{client.ns.emoji.money_bag} **Saldo Saat Ini:** `{total_balance}` {client.ns.emoji.star}\n"
            f"{client.ns.emoji.chart_up} **Total Pemasukan:** `{total_income}` {client.ns.emoji.star}\n"
            f"{client.ns.emoji.chart_down} **Total Pengembalian:** `{total_refunds}` {client.ns.emoji.star}\n"
            f"{client.ns.emoji.repeat} **Total Transaksi (Tampil):** `{total_transactions_count}`\n\n"
            f"**{client.ns.emoji.open_book} Transaksi Terakhir ({page + 1}/{total_pages})**\n{history_details}"
        )
        layout = []
        if total_pages > 1:
            prev_page = page - 1 if page > 0 else total_pages - 1
            next_page = page + 1 if page < total_pages - 1 else 0
            layout.append(
                [
                    {
                        "text": "« Sebelumnya",
                        "callback_data": f"stats_{prev_page}",
                        "style": "blue",
                        "emoji": client.ns.emoji.id("back_arrow"),
                    },
                    {
                        "text": "Selanjutnya »",
                        "callback_data": f"stats_{next_page}",
                        "style": "blue",
                        "emoji": client.ns.emoji.id("right_pointing"),
                    },
                ]
            )
        layout.append(_back_to_settings_layout(client)[0])
        btn = client.ns.telegram.button.build_button_grid(layout)
        await _reply(client, callback_query, text, btn)
    except Exception as e:
        ctx.log.print(
            f"{ctx.log.RED} Error fetching stars stats: {e}\n{traceback.format_exc()}"
        )
        await callback_query.answer(f"Error: {e}", show_alert=True)


@command(lambda ctx: filters.regex("^total_users_count$"), handler_type="callback")
async def total_users_count_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True
        )
    user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
    total_count = len(user_ids)
    text = (
        f"**{client.ns.emoji.busts_in_silhouette} Total Pengguna Bot**\n\n"
        f"Jumlah keseluruhan pengguna yang pernah memulai bot ini adalah: **{total_count} pengguna**."
    )
    markup = client.ns.telegram.button.build_button_grid(
        _back_to_settings_layout(client)
    )
    try:
        await _reply(client, callback_query, text, markup)
    except pyrogram.errors.MessageNotModified:
        await callback_query.answer()
    except Exception:
        await callback_query.answer(
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>",
            show_alert=True,
        )