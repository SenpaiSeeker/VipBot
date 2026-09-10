from datetime import datetime, timedelta

from pyrogram import filters
from zoneinfo import ZoneInfo

from .. import command, ctx, is_bot_owner

TIMEZONE = ZoneInfo("Asia/Jakarta")


def _back_to_revenue_layout(client):
    return [
        [
            {
                "text": "• Kembali •",
                "callback_data": "vip_revenue_menu",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]


async def _reply(client, callback_query, text, btn):
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^vip_revenue_menu$"),
    handler_type="callback",
)
async def vip_revenue_menu_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    text = (
        f"**{client.ns.emoji.money_bag} Cek Pendapatan VIP**\n\n"
        "Pilih periode waktu untuk melihat total pendapatan dari penjualan paket VIP."
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
    await _reply(client, callback_query, text, btn)


def _include_record(period, record_date, now):
    if period == "daily":
        return record_date.date() == now.date()
    if period == "weekly":
        return now - timedelta(days=7) <= record_date <= now
    if period == "monthly":
        return record_date.year == now.year and record_date.month == now.month
    return False


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

    now = datetime.now(TIMEZONE)
    total_amount = 0
    transaction_count = 0
    for record in revenue_history:
        try:
            record_date = datetime.fromisoformat(record["date"]).astimezone(TIMEZONE)
            if _include_record(period, record_date, now):
                total_amount += int(record["amount"])
                transaction_count += 1
        except Exception:
            continue

    period_text = {
        "daily": "Harian",
        "weekly": "Mingguan",
        "monthly": "Bulanan",
    }.get(period, "Harian")

    text = (
        f"**{client.ns.emoji.chart_bar} Laporan Pendapatan VIP**\n\n"
        f"**Periode:** {period_text}\n\n"
        f"{client.ns.emoji.money_bag} **Total Pendapatan:** `Rp {total_amount:,}`\n"
        f"{client.ns.emoji.repeat} **Jumlah Transaksi:** `{transaction_count}`"
    )
    btn = client.ns.telegram.button.build_button_grid(_back_to_revenue_layout(client))
    await _reply(client, callback_query, text, btn)