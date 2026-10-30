from helpers.modules import Modules
import asyncio

import pyrogram

from .. import *

_refund_lock = asyncio.Lock()


async def dashboard_command_handler(client, message):
    msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=f"{client.ns.emoji.md('hourglass')} **Sedang Memproses...**\nMohon tunggu sebentar."
        )
    )
    all_bots_data = await client.db.getBots(is_token=True)
    total_bots = len(all_bots_data)
    unique_users = set()
    bot_user_counts = {}
    for bot_data in all_bots_data:
        try:
            bot_id = int(bot_data["name"])
            user_ids = await client.db.getListVars(bot_id, "user_ids") or []
        except (KeyError, TypeError, ValueError):
            continue
        bot_user_counts[bot_id] = len(user_ids)
        for user_id in user_ids:
            unique_users.add(user_id)
    total_users = len(unique_users)
    top_bot_id = (
        max(bot_user_counts, key=bot_user_counts.get) if bot_user_counts else None
    )
    top_bot_info = "N/A"
    if top_bot_id:
        top_bot_instance = client.manager.running_bots.get(top_bot_id)
        top_bot_name = (
            top_bot_instance.me.first_name if top_bot_instance else f"ID {top_bot_id}"
        )
        top_bot_info = f"{top_bot_name} ({bot_user_counts[top_bot_id]} pengguna)"
    try:
        stats = await client.ns.server.monitor.get_detailed_stats()
        stats_data = {
            "cpu": stats.cpu["percent"],
            "ram": stats.ram["percent"],
            "disk": stats.disk["percent"],
        }
        cpu_bar = stats.cpu["bar"]
        cpu_pct = stats.cpu["percent"]
        ram_bar = stats.ram["bar"]
        ram_pct = stats.ram["percent"]
        disk_bar = stats.disk["bar"]
        disk_pct = stats.disk["percent"]
        server_rows = [
            ["CPU", f"`[{cpu_bar}] {cpu_pct}%`"],
            ["RAM", f"`[{ram_bar}] {ram_pct}%`"],
            ["Disk", f"`[{disk_bar}] {disk_pct}%`"],
        ]
        server_stats_text = client.ns.table.md(["Komponen", "Penggunaan"], server_rows)
    except Exception as e:
        stats_data = {"cpu": 0, "ram": 0, "disk": 0}
        server_stats_text = f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Gagal mengambil statistik server'], ['Error', f'`{e}`']])}"

    platform_rows = [
        ["Total Bot Aktif", f"`{total_bots}`"],
        ["Total Pengguna Unik", f"`{total_users}`"],
        [f"{client.ns.emoji.md('trophy')} Bot Terpopuler", f"`{top_bot_info}`"],
    ]

    dashboard_text = (
        f"{client.ns.emoji.md('chart_bar')} **Dashboard Platform**\n\n"
        f"**Statistik Platform**\n\n"
        f"{client.ns.table.md(['Komponen', 'Isi'], platform_rows)}\n\n"
        f"**Kesehatan Server**\n\n"
        f"{server_stats_text}"
    )
    photo_stream = None
    try:
        photo_stream = await client.ns.utils.dashboard.generate_dashboard(stats_data)
        await message.reply_rich(
            client.ns.table.rich_photo(
                photo=photo_stream, markdown=dashboard_text, alias="dashboard"
            )
        )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{dashboard_text}\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Error Visualisasi'], ['Detail', f'`{e}`']])}"
                )
            )
        )
    finally:
        if photo_stream is not None:
            photo_stream.close()


async def refund_stars_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki izin untuk melakukan ini.", show_alert=True
        )
    db_key = ""
    try:
        refund_key = callback_query.data.split("_")[2]
        db_key = f"refund_{refund_key}"
        refund_data = await client.db.getVars(client.me.id, db_key)
        if not refund_data:
            await callback_query.edit_message_text(
                rich_message=pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{callback_query.message.text}\n\n"
                        f"{client.ns.table.md(['Status', 'Keterangan'], [['Gagal', 'Transaksi tidak ditemukan atau sudah di-refund']])}"
                    )
                )
            )
            return
        user_id_to_refund = refund_data["user_id"]
        charge_id = refund_data["charge_id"]
        refunded_key = f"refunded_{charge_id}"

        async with _refund_lock:
            if await client.db.getVars(client.me.id, refunded_key):
                await client.db.removeVars(client.me.id, db_key)
                return await callback_query.answer(
                    "Donasi ini sudah dikembalikan.",
                    show_alert=True,
                )

            await client.refund_star_payment(
                user_id=user_id_to_refund,
                telegram_payment_charge_id=charge_id,
            )
            await client.db.setVars(client.me.id, refunded_key, True)

        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{callback_query.message.text}\n\n"
                    f"{client.ns.table.md(['Status', 'Keterangan'], [['Berhasil', 'Donasi Stars telah dikembalikan']])}"
                )
            ),
        )
        await client.send_rich_message(
            user_id_to_refund,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('information_source')} **Informasi Donasi**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Donasi Stars Anda telah dikembalikan oleh admin'], ['Catatan', 'Terima kasih atas pengertian Anda']])}"
                )
            ),
        )
    except Exception as e:
        client.log.print(f"{client.log.RED}Gagal merefund donasi: {e}")
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{callback_query.message.text}\n\n"
                    f"{client.ns.table.md(['Status', 'Keterangan'], [['Gagal', 'Gagal mengembalikan donasi'], ['Error', f'`{e}`']])}"
                )
            )
        )
    finally:
        if db_key:
            await client.db.removeVars(client.me.id, db_key)


async def show_stars_stats(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    page = int(callback_query.data.split("_")[1])
    items_per_page = 5
    table = client.ns.table
    try:
        await callback_query.answer(
            "⏳ **Sedang Memproses...**\nMohon tunggu sebentar."
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
            layout = [
                [
                    {
                        "text": "• Kembali ke Pengaturan •",
                        "callback_data": "settings",
                        "style": "blue",
                        "emoji": client.ns.emoji.id("key"),
                    }
                ]
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            empty_rows = [
                ["Total Transaksi", "`0`"],
                ["Status", "Belum ada transaksi Stars"],
            ]
            text = (
                f"{client.ns.emoji.md('chart_bar')} **Statistik Pendapatan Stars**\n\n"
                f"{table.md(['Info', 'Nilai'], empty_rows)}"
            )
            await callback_query.edit_message_text(
                rich_message=pyrogram.types.InputRichMessage(markdown=text),
                reply_markup=btn,
            )
            return
        total_balance = raw_result.balance.amount
        total_income = sum(
            t.amount.amount for t in transactions_history if t.amount.amount > 0
        )
        total_refunds = sum(
            abs(t.amount.amount) for t in transactions_history if t.amount.amount < 0
        )
        total_transactions_count = len(transactions_history)
        peer_map = {p.id: p for p in raw_result.users + raw_result.chats}
        total_pages = math.ceil(total_transactions_count / items_per_page)
        page = max(0, min(page, total_pages - 1))
        paginated_transactions = transactions_history[
            page * items_per_page : (page + 1) * items_per_page
        ]
        jakarta_timezone = ZoneInfo("Asia/Jakarta")
        transactions_rows = []
        for t in paginated_transactions:
            peer_id = (
                t.peer.peer.user_id
                if hasattr(t.peer.peer, "user_id")
                else t.peer.peer.channel_id
            )
            peer_obj = peer_map.get(peer_id)
            peer_mention = (
                peer_obj.first_name
                if peer_obj and hasattr(peer_obj, "first_name")
                else (peer_obj.title if peer_obj else "sumber tidak dikenal")
            )
            amount = t.amount.amount
            amount_str = f"+{amount}" if amount > 0 else str(amount)
            transaction_date = datetime.fromtimestamp(
                t.date, tz=timezone.utc
            ).astimezone(jakarta_timezone)
            formatted_date = transaction_date.strftime("%d %b, %H:%M %Z")
            transactions_rows.append(
                [
                    f"`{formatted_date}`",
                    f"**{amount_str}{client.ns.emoji.md('star')}**",
                    peer_mention,
                ]
            )

        summary_rows = [
            [
                f"{client.ns.emoji.md('money_bag')} Saldo Saat Ini",
                f"`{total_balance}` {client.ns.emoji.md('star')}",
            ],
            [
                f"{client.ns.emoji.md('chart_up')} Total Pemasukan",
                f"`{total_income}` {client.ns.emoji.md('star')}",
            ],
            [
                f"{client.ns.emoji.md('chart_down')} Total Pengembalian",
                f"`{total_refunds}` {client.ns.emoji.md('star')}",
            ],
            [
                f"{client.ns.emoji.md('repeat')} Total Transaksi (Tampil)",
                f"`{total_transactions_count}`",
            ],
        ]
        summary_text = table.md(["Aspek", "Nilai"], summary_rows)
        text = (
            f"{client.ns.emoji.md('chart_bar')} **Statistik Pendapatan Stars**\n\n"
            f"{summary_text}\n\n"
            f"**{client.ns.emoji.md('open_book')} Transaksi Terakhir ({page + 1}/{total_pages})**\n\n"
            f"{table.md(['Tanggal', 'Jumlah', 'Sumber'], transactions_rows)}"
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
        layout.append(
            [
                {
                    "text": "• Kembali ke Pengaturan •",
                    "callback_data": "settings",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("key"),
                }
            ]
        )
        btn = client.ns.telegram.button.build_button_grid(layout)
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=btn,
        )
    except Exception as e:
        client.log.print(
            f"{client.log.RED} Error fetching stars stats: {e}\n{traceback.format_exc()}"
        )
        await callback_query.answer(f"Error: {e}", show_alert=True)


async def total_users_count_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.", show_alert=True
        )
    user_ids = await client.db.getListVars(client.me.id, "user_ids") or []
    total_count = len(user_ids)
    text = (
        f"{client.ns.emoji.md('busts_in_silhouette')} **Total Pengguna Bot**\n\n"
        f"{client.ns.table.md(['Aspek', 'Nilai'], [['Jumlah Pengguna', f'`{total_count}`']])}\n\n"
        f"Jumlah keseluruhan pengguna yang pernah memulai bot ini adalah **{total_count} pengguna**."
    )
    markup = client.ns.telegram.button.build_button_grid(
        [
            [
                {
                    "text": "• Kembali ke Pengaturan •",
                    "callback_data": "settings",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("key"),
                }
            ]
        ]
    )
    try:
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=markup,
        )
    except pyrogram.errors.MessageNotModified:
        await callback_query.answer()
    except Exception:
        await callback_query.answer(
            "❌ **Terjadi Kesalahan**\n\n`{e}`".format(e=e),
            show_alert=True,
        )


class AdminDashboard(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_message(
            filters.command("dashboard") & filters.user(self.client.owner_id)
        )(self.handle(dashboard_command_handler))
        self.client.on_callback_query(filters.regex("^refund_stars_"))(
            self.handle(refund_stars_callback)
        )
        self.client.on_callback_query(filters.regex("^stats_(\\d+)"))(
            self.handle(show_stars_stats)
        )
        self.client.on_callback_query(filters.regex("^total_users_count$"))(
            self.handle(total_users_count_callback)
        )
