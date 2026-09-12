import { randomBytes } from "crypto";
import { TelegramClient } from "teleproto";
import { command, ctx, get_notification_target } from "../index";
import { Filters } from "../filters";
import { toId } from "../../types";

type Any = any;

export const successful_donation_handler = command(
    (_c: Any) => Filters.successful_payment
)(async (client: TelegramClient, message: Any) => {
    const payment = message.successful_payment;
    if (!payment || !payment.invoice_payload.startsWith("donation_")) {
        return;
    }

    const user = message.from_user;
    const stars_donated = payment.total_amount;
    const charge_id = payment.telegram_payment_charge_id;
    const current_bot_id = client.me.id;
    const super_admin_id = ctx.owner_id;

    await client.send_message(
        user.id,
        `${client.ns.emoji.party_popper} **Terima Kasih Banyak, ${user.firstName}!**\n\n` +
            `Kami telah menerima donasi Anda sebesar **${stars_donated} Stars (${client.ns.emoji.star})**.\n` +
            "Dukungan Anda adalah bahan bakar semangat bagi kami. Semoga hari Anda menyenangkan!"
    );

    const owner_of_this_bot = await get_notification_target(client);
    const main_bot_client = ctx.manager.main_bot_client;

    try {
        const user_mention_str = client.ns.telegram.arg.getMention(user);
        const bot_mention_str = client.me.mention;
        const notification_text =
            `${client.ns.emoji.sparkles} **Donasi Baru Diterima!**\n\n` +
            `**Jumlah:** \`${stars_donated}\` Stars (${client.ns.emoji.star})\n` +
            `**Dari:** ${user_mention_str} (\`${user.id}\`)\n` +
            `**Melalui Bot:** ${bot_mention_str}`;

        const refund_key = randomBytes(8).toString("hex");
        const refund_data = {
            user_id: toId(user.id),
            charge_id,
        };
        await ctx.db.setVars(current_bot_id, `refund_${refund_key}`, refund_data);

        const refund_callback_data = `refund_stars_${refund_key}`;
        const layout = [
            [
                {
                    text: "🔙 Kembalikan Donasi",
                    callback_data: refund_callback_data,
                    style: "red",
                    emoji: client.ns.emoji.id("minus"),
                },
            ],
        ];
        const refund_btn = client.ns.telegram.button.build_button_grid(layout);

        await client.send_message(owner_of_this_bot, notification_text, {
            reply_markup: refund_btn,
        });
    } catch (e: any) {
        if (e?.errorMessage === "USER_IS_BLOCKED") {
            if (main_bot_client && toId(owner_of_this_bot) !== toId(super_admin_id)) {
                const user_mention_str = client.ns.telegram.arg.getMention(user);
                await main_bot_client.send_message(
                    super_admin_id,
                    `${client.ns.emoji.exclamation} **Notifikasi Gagal Terkirim**\n\n` +
                        `Notifikasi donasi sebesar \`${stars_donated}\` Stars dari ${user_mention_str} ` +
                        `gagal dikirim ke owner bot \`${client.me.firstName}\` karena bot diblokir olehnya.`
                );
            }
        } else {
            ctx.log.print(`Gagal mengirim notifikasi donasi: ${e}`);
        }
    }
});