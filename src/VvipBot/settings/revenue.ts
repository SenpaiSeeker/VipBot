import { TelegramClient } from "teleproto";
import { command, ctx, is_bot_owner } from "../index";
import { Filters } from "../filters";

const TIMEZONE = "Asia/Jakarta";
const OFFSET_PLUS7 = 7 * 3600 * 1000;

function _back_to_revenue_layout(client: TelegramClient): any[] {
    return [
        [
            {
                text: "• Kembali •",
                callback_data: "vip_revenue_menu",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
}

async function _reply(
    client: TelegramClient,
    callback_query: any,
    text: string,
    btn: any
): Promise<void> {
    if (callback_query.message.photo) {
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else {
        await callback_query.edit_message_text(text, { reply_markup: btn });
    }
}

export const vip_revenue_menu_callback = command(
    (_c: any) => Filters.regex("^vip_revenue_menu$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const text =
        `**${client.ns.emoji.money_bag} Cek Pendapatan VIP**\n\n` +
        "Pilih periode waktu untuk melihat total pendapatan dari penjualan paket VIP.";
    const layout = [
        [
            {
                text: "📅 Harian (Hari Ini)",
                callback_data: "show_revenue_daily",
                style: "blue",
                emoji: client.ns.emoji.id("calendar"),
            },
            {
                text: "🗓️ Mingguan (7 Hari)",
                callback_data: "show_revenue_weekly",
                style: "blue",
                emoji: client.ns.emoji.id("calendar"),
            },
        ],
        [
            {
                text: "📆 Bulanan (Bulan Ini)",
                callback_data: "show_revenue_monthly",
                style: "blue",
                emoji: client.ns.emoji.id("calendar"),
            },
        ],
        [
            {
                text: "• Kembali •",
                callback_data: "settings",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});

function _wibNow(): Date {
    return new Date(Date.now() + OFFSET_PLUS7);
}

function _include_record(period: string, record_date: Date, now: Date): boolean {
    if (period === "daily") {
        return (
            record_date.getUTCFullYear() === now.getUTCFullYear() &&
            record_date.getUTCMonth() === now.getUTCMonth() &&
            record_date.getUTCDate() === now.getUTCDate()
        );
    }
    if (period === "weekly") {
        const weekMs = 7 * 24 * 3600 * 1000;
        return now.getTime() - weekMs <= record_date.getTime();
    }
    if (period === "monthly") {
        return (
            record_date.getUTCFullYear() === now.getUTCFullYear() &&
            record_date.getUTCMonth() === now.getUTCMonth()
        );
    }
    return false;
}

export const show_vip_revenue_callback = command(
    (_c: any) => Filters.regex("^show_revenue_(daily|weekly|monthly)$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const period = callback_query.matches[0].group(1);
    const revenue_history =
        (await ctx.db.getListVars(client.me.id, "vip_revenue_history")) || [];

    const now = _wibNow();
    let total_amount = 0;
    let transaction_count = 0;
    for (const record of revenue_history) {
        try {
            const record_date = new Date(
                new Date(record["date"]).getTime() + OFFSET_PLUS7
            );
            if (_include_record(period, record_date, now)) {
                total_amount += Math.trunc(Number(record["amount"]));
                transaction_count += 1;
            }
        } catch {
            continue;
        }
    }

    const period_text = { daily: "Harian", weekly: "Mingguan", monthly: "Bulanan" }[
        period as "daily" | "weekly" | "monthly"
    ] || "Harian";

    const text =
        `**${client.ns.emoji.chart_bar} Laporan Pendapatan VIP**\n\n` +
        `**Periode:** ${period_text}\n\n` +
        `${client.ns.emoji.money_bag} **Total Pendapatan:** \`Rp ${total_amount.toLocaleString("id-ID")}\`\n` +
        `${client.ns.emoji.repeat} **Jumlah Transaksi:** \`${transaction_count}\``;
    const btn = client.ns.telegram.button.build_button_grid(
        _back_to_revenue_layout(client)
    );
    await _reply(client, callback_query, text, btn);
});