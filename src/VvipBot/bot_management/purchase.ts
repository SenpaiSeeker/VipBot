import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { calculate_bot_price, get_bot_purchase_panel } from "./pricing";
import { BACKUP_BOT } from "../../config";

export const MAX_BOTS = 25;

async function _edit_caption_or_text(
    callback_query: any,
    text: string,
    btn: any
): Promise<any> {
    if (callback_query.message && callback_query.message.photo) {
        return await callback_query.edit_message_caption(text, {
            reply_markup: btn,
        });
    }
    return await callback_query.edit_message_text(text, { reply_markup: btn });
}

async function _send_full_warning(
    client: TelegramClient,
    callback_query: any
): Promise<any> {
    const backup_text = BACKUP_BOT ? ` melalui @${BACKUP_BOT}` : "";
    const text_warning =
        `${client.ns.emoji.cross_mark} **Kapasitas Bot Penuh!**\n\n` +
        `Maaf, server saat ini sudah mencapai batas maksimal pembuatan bot (${MAX_BOTS} Bot). Silakan buat bot baru${backup_text}.`;
    const layout = [
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
    return await _edit_caption_or_text(callback_query, text_warning, btn);
}

async function _subscribed_panel(
    client: TelegramClient,
    callback_query: any
): Promise<any> {
    const text =
        `${client.ns.emoji.white_check_mark} **Anda Sudah Berlangganan!**\n\n` +
        "Anda sudah memiliki akses untuk membuat bot. " +
        "Tekan tombol di bawah untuk memulai proses pembuatan.";
    const layout = [
        [
            {
                text: "▶️ Lanjutkan Membuat Bot",
                callback_data: "start_creation_process",
                style: "green",
                emoji: client.ns.emoji.id("rocket"),
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
    return await _edit_caption_or_text(callback_query, text, btn);
}

export const create_bot_callback = command(
    (_c: any) => Filters.regex("^create_bot$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const all_bots_data = await ctx.db.getBots(true);
    if (all_bots_data.length >= MAX_BOTS) {
        return await _send_full_warning(client, callback_query);
    }

    const user_id = callback_query.from_user.id;
    const user_expiry_str = await ctx.db.getVars(user_id, "user_expiry_date");
    if (user_expiry_str) {
        const expiry_date = new Date(user_expiry_str);
        if (expiry_date.getTime() > Date.now()) {
            return await _subscribed_panel(client, callback_query);
        }
    }

    const [text, btn] = await get_bot_purchase_panel(client, user_id, 1);
    await callback_query.edit_message_caption(text, { reply_markup: btn });
});

export const adjust_bot_month_callback = command(
    (_c: any) => Filters.regex("^adjust_bot_month_(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const months = parseInt(callback_query.data_string.split("_").pop()!, 10);
    if (1 <= months && months <= 12) {
        const [text, btn] = await get_bot_purchase_panel(
            client,
            callback_query.from_user.id,
            months
        );
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else {
        await callback_query.answer(
            "Durasi minimal 1 bulan dan maksimal 12 bulan.",
            { show_alert: true }
        );
    }
});

export const proceed_bot_payment_callback = command(
    (_c: any) => Filters.regex("^pay_bot_qris_(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const user_id = callback_query.from_user.id;
    const months = parseInt(callback_query.data_string.split("_").pop()!, 10);

    await callback_query.edit_message_caption(
        `${client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.`
    );

    const saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID");
    if (!saweria_user_id) {
        return await callback_query.edit_message_caption(
            "Maaf, layanan pembayaran saat ini tidak tersedia."
        );
    }

    const [, , amount] = calculate_bot_price(months);
    const fakeinfo = client.ns.utils.faker.generate();

    try {
        const payment = await client.services.saweria.create_payment(
            saweria_user_id,
            Math.trunc(Number(amount)),
            `User-${user_id}`,
            fakeinfo.email,
            `Akses Buat Bot VVIP ${months} bulan`,
            client.me.username
        );
        const transaction_id: string = payment.transaction_id;
        const qr_image_stream: any = payment.qr_image_stream;
        const amount_raw: number = payment.amount_raw;

        const order_data = `${months}|${amount_raw}`;
        await ctx.db.setVars(client.me.id, transaction_id, order_data);

        const caption =
            `**${client.ns.emoji.white_check_mark} Pembayaran Siap Dilakukan!**\n\n` +
            "Silakan scan QRIS di atas untuk membayar. Setelah itu, " +
            "tekan tombol **Konfirmasi Pembayaran**.\n\n" +
            "╭─ **Detail Tagihan**\n" +
            "│\n" +
            `├─ ${client.ns.emoji.shopping_bags} **Produk:** Akses Buat Bot ${months} Bulan (Langganan)\n` +
            `├─ ${client.ns.emoji.gem} **Jumlah:** \`Rp ${amount_raw.toLocaleString("id-ID")}\`\n` +
            `├─ ${client.ns.emoji.id_card} **Order ID:** [${transaction_id}](https://saweria.co/qris/${transaction_id})\n` +
            "│\n" +
            `╰─ ${client.ns.emoji.down_pointing} **Jika sudah membayar, silakan klik tombol di bawah ini.**\n`;
        const layout = [
            [
                {
                    text: "✅ Konfirmasi Pembayaran",
                    callback_data: `confirm_bot_payment_${transaction_id}`,
                    style: "green",
                    emoji: client.ns.emoji.id("white_check_mark"),
                },
            ],
        ];
        const btn = client.ns.telegram.button.build_button_grid(layout);

        await callback_query.message.delete();
        await client.send_photo(user_id, qr_image_stream, {
            caption,
            reply_markup: btn,
        });
    } catch (e: any) {
        await client.send_message(
            user_id,
            `${client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>${e}</pre>`
        );
    }
});

export const confirm_bot_payment_callback = command(
    (_c: any) => Filters.regex("^confirm_bot_payment_(.+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const transaction_id = callback_query.data_string.split("_").pop()!;
    const user = callback_query.from_user;
    const order_data_str = await ctx.db.getVars(client.me.id, transaction_id);
    if (!order_data_str) {
        return await callback_query.answer(
            "<emoji id=6271786398404055377>⚠️</emoji> Invoice ini sudah tidak valid atau telah selesai.",
            { show_alert: true }
        );
    }

    const [months_str, amount_raw_str] = String(order_data_str).split("|");
    const months = parseInt(months_str, 10);
    const amount_raw = parseInt(amount_raw_str, 10);

    try {
        const is_paid = await client.services.saweria.check_paid_status(transaction_id);
        if (is_paid) {
            await ctx.db.removeVars(client.me.id, transaction_id);
            const expiry_date = new Date(
                Date.now() + 30 * months * 24 * 3600 * 1000
            );
            await ctx.db.setVars(user.id, "user_expiry_date", expiry_date.toISOString());
            await callback_query.message.delete();

            const success_text =
                `${client.ns.emoji.white_check_mark} **Pembayaran Berhasil!**\n\n` +
                `Terima kasih! Langganan Anda untuk membuat bot selama **${months} bulan** telah diaktifkan.`;
            const layout = [
                [
                    {
                        text: "▶️ Lanjutkan Membuat Bot",
                        callback_data: "start_creation_process",
                        style: "green",
                        emoji: client.ns.emoji.id("rocket"),
                    },
                ],
            ];
            const btn = client.ns.telegram.button.build_button_grid(layout);
            await client.send_message(user.id, success_text, { reply_markup: btn });

            const owner_mention = client.ns.telegram.arg.getMention(user);
            const formatted_amount = amount_raw.toLocaleString("id-ID");
            const owner_notif =
                `${client.ns.emoji.money_bag} **Langganan Akses Baru!**\n\n` +
                `**Pengguna:** ${owner_mention}\n` +
                `**Durasi:** ${months} bulan\n` +
                `**Jumlah:** \`Rp ${formatted_amount}\``;
            await client.send_message(ctx.owner_id, owner_notif);
        } else {
            await callback_query.answer(
                "❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah beberapa saat.",
                { show_alert: true }
            );
        }
    } catch (e: any) {
        await callback_query.answer(`❌ Terjadi kesalahan: ${e}`, {
            show_alert: true,
        });
    }
});