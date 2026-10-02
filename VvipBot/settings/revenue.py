from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pyrogram
from pyrogram import filters

from .. import command, ctx, is_bot_owner


@command(
    lambda ctx: filters.regex("^vip_revenue_menu$"),
    handler_type="callback",
)
async def vip_revenue_menu_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    period_rows = [
        ["Harian", "Hari ini"],
        ["Mingguan", "7 hari terakhir"],
        ["Bulanan", "Bulan berjalan"],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('money_bag')} **Cek Pendapatan VIP**\n\n"
        f"{table.md(['Periode', 'Rentang Waktu'], period_rows)}\n\n"
        f"Pilih periode di bawah untuk melihat rekap pendapatan."
    )
    layout = [
        [
            {
                "text": "📅 Harian (Hari Ini)",
                "callback_data": "show_revenue_daily",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            },
            {
                "text": "🗓️ Mingguan (7 Hari)",
                "callback_data": "show_revenue_weekly",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            },
        ],
        [
            {
                "text": "📆 Bulanan (Bulan Ini)",
                "callback_data": "show_revenue_monthly",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


@command(
    lambda ctx: filters.regex("^show_revenue_(daily|weekly|monthly)$"),
    handler_type="callback",
)
async def show_vip_revenue_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    period = callback_query.matches[0].group(1)
    revenue_history = (
        await ctx.db.getListVars(client.me.id, "vip_revenue_history") or []
    )

    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    total_amount = 0
    transaction_count = 0

    for record in revenue_history:
        try:
            record_date = datetime.fromisoformat(record["date"]).astimezone(
                ZoneInfo("Asia/Jakarta")
            )
            include_record = False

            if period == "daily":
                if record_date.date() == now.date():
                    include_record = True
            elif period == "weekly":
                if now - timedelta(days=7) <= record_date <= now:
                    include_record = True
            elif period == "monthly":
                if record_date.year == now.year and record_date.month == now.month:
                    include_record = True

            if include_record:
                total_amount += int(record["amount"])
                transaction_count += 1
        except Exception:
            continue

    period_text = {
        "daily": "Harian",
        "weekly": "Mingguan",
        "monthly": "Bulanan",
    }.get(period, "Harian")

    table = client.ns.table
    report_rows = [
        ["Periode", period_text],
        [f"{client.ns.emoji.md('money_bag')} Total Pendapatan", f"`Rp {total_amount:,}`"],
        [f"{client.ns.emoji.md('repeat')} Jumlah Transaksi", f"`{transaction_count}`"],
    ]

    text = (
        f"{client.ns.emoji.md('chart_bar')} **Laporan Pendapatan VIP**\n\n"
        f"{table.md(['Info', 'Nilai'], report_rows)}"
    )

    layout = [
        [
            {
                "text": "• Kembali •",
                "callback_data": "vip_revenue_menu",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )
