import { TelegramClient } from "teleproto";

export const BASE_PRICE_BOT = 100000;

export function calculate_bot_price(months: number): [number, number, number] {
    const total = BASE_PRICE_BOT * months;
    let discount_percentage = 0;
    if (months >= 6) {
        discount_percentage = 0.2;
    } else if (months >= 3) {
        discount_percentage = 0.1;
    }
    const discount = Math.trunc(total * discount_percentage);
    const final_price = total - discount;
    return [total, discount, final_price];
}

export async function get_bot_purchase_panel(
    client: TelegramClient,
    user_id: any,
    months = 1
): Promise<[string, any]> {
    const [total, discount, final_price] = calculate_bot_price(months);

    const formatted_price = BASE_PRICE_BOT.toLocaleString("id-ID");
    const formatted_total = total.toLocaleString("id-ID");
    const formatted_discount = `-Rp ${discount.toLocaleString("id-ID")}`;
    const formatted_final = final_price.toLocaleString("id-ID");

    const text =
        `**${client.ns.emoji.gem} Beli Akses Pembuatan Bot**\n\n` +
        "Dapatkan akses untuk membuat bot VVIP Anda sendiri dengan berlangganan.\n\n" +
        `Harga: \`Rp ${formatted_price}/bulan\`\n\n` +
        "**Diskon:**\n" +
        "• 3+ Bulan: 10%\n" +
        "• 6+ Bulan: 20%\n\n" +
        "**Pilihan Anda:**\n" +
        `• Durasi: **${months} bulan**\n` +
        `• Harga Normal: \`Rp ${formatted_total}\`\n` +
        `• Diskon: \`${formatted_discount}\`\n` +
        `• **Total Bayar: \`Rp ${formatted_final}\`**`;

    const layout = [
        [
            {
                text: "➖",
                callback_data: `adjust_bot_month_${months - 1}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
            {
                text: `${months} Bulan`,
                callback_data: "noop",
                style: "blue",
            },
            {
                text: "➕",
                callback_data: `adjust_bot_month_${months + 1}`,
                style: "green",
                emoji: client.ns.emoji.id("plus"),
            },
        ],
        [
            {
                text: `Bayar via QRIS (Rp ${formatted_final})`,
                callback_data: `pay_bot_qris_${months}`,
                style: "green",
                emoji: client.ns.emoji.id("gem"),
            },
        ],
        [
            {
                text: "• Kembali •",
                callback_data: "start",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    return [text, btn];
}