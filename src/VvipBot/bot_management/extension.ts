import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { toId } from "../../types";

export const EXTEND_DAYS = 30;

async function _get_bot_display_name(
    client: TelegramClient,
    bot_id: number
): Promise<string> {
    try {
        const bot_instance = ctx.manager.running_bots.get(bot_id);
        if (bot_instance && bot_instance.is_connected) {
            return bot_instance.me.firstName;
        }
    } catch {
        // ignore
    }
    return `ID ${bot_id}`;
}

export const request_extend_duration_callback = command(
    (_c: any) => Filters.regex("^request_extend_duration\\s(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const bot_id_to_request = Math.trunc(
        Number(callback_query.data_string.split(" ", 2)[1])
    );
    const requester = callback_query.from_user;
    const bot_name = await _get_bot_display_name(client, bot_id_to_request);

    try {
        const main_bot_client = ctx.manager.main_bot_client;
        if (!main_bot_client || !main_bot_client.is_connected) {
            throw new Error(
                "Bot utama sedang tidak aktif, tidak dapat mengirim notifikasi."
            );
        }

        const requester_mention =
            main_bot_client.ns.telegram.arg.getMention(requester);
        const txt_owner =
            `**${main_bot_client.ns.emoji.bell} Permintaan Perpanjangan Durasi**\n\n` +
            `**Pengguna:** ${requester_mention} (\`${requester.id}\`)\n` +
            `**Bot:** **${bot_name}** (\`${bot_id_to_request}\`)\n\n` +
            `Setujui untuk menambah masa aktif bot ini sebanyak ${EXTEND_DAYS} hari.`;
        const layout_owner = [
            [
                {
                    text: `✅ Setujui (+${EXTEND_DAYS} Hari)`,
                    callback_data: `approve_extension ${bot_id_to_request} ${requester.id}`,
                    style: "green",
                    emoji: main_bot_client.ns.emoji.id("white_check_mark"),
                },
                {
                    text: "❌ Tolak Permintaan",
                    callback_data: `close_req ${bot_id_to_request} ${requester.id}`,
                    style: "red",
                    emoji: main_bot_client.ns.emoji.id("cross_mark"),
                },
            ],
        ];
        const btn_owner =
            main_bot_client.ns.telegram.button.build_button_grid(layout_owner);
        await main_bot_client.send_message(ctx.owner_id, txt_owner, {
            reply_markup: btn_owner,
        });
        await callback_query.answer(
            "✅ Permintaan perpanjangan telah dikirim ke Owner Utama. Anda akan dihubungi jika disetujui.",
            { show_alert: true }
        );
    } catch (e: any) {
        await callback_query.answer(`❌ Gagal mengirim permintaan ke Owner: ${e}`, {
            show_alert: true,
        });
    }
});

export const owner_approve_extension_callback = command(
    (_c: any) => Filters.regex("^approve_extension\\s(\\d+)\\s(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== ctx.owner_id) {
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa menyetujui permintaan ini.",
            { show_alert: true }
        );
    }

    try {
        const parts = callback_query.data_string.split(/\s+/);
        const bot_id_to_extend = parseInt(parts[1], 10);
        const requester_id = parseInt(parts[2], 10);

        const exp_date_str = await ctx.db.getVars(
            bot_id_to_extend,
            "bot_expiration_date"
        );
        const current_exp_date = exp_date_str
            ? new Date(exp_date_str)
            : new Date();
        const new_exp_date = new Date(
            current_exp_date.getTime() + EXTEND_DAYS * 24 * 3600 * 1000
        );
        await ctx.db.setVars(
            bot_id_to_extend,
            "bot_expiration_date",
            new_exp_date.toISOString()
        );

        await callback_query.edit_message_text(
            `${client.ns.emoji.white_check_mark} **Persetujuan Berhasil!**\n` +
                `Durasi untuk bot \`${bot_id_to_extend}\` telah ditambah **${EXTEND_DAYS} hari**.`
        );

        try {
            const bot_instance = ctx.manager.running_bots.get(bot_id_to_extend);
            const bot_name =
                bot_instance && bot_instance.is_connected
                    ? bot_instance.me.firstName
                    : `ID ${bot_id_to_extend}`;
            await client.send_message(
                requester_id,
                `${client.ns.emoji.party_popper} **Kabar Baik!**\n\n` +
                    `Permintaan perpanjangan Anda untuk bot **${bot_name}** telah disetujui dan diperpanjang.`
            );
        } catch (e) {
            ctx.log.print(`Gagal kirim notif persetujuan ke ${requester_id}: ${e}`);
        }
    } catch (e: any) {
        await callback_query.edit_message_text(
            `${client.ns.emoji.cross_mark} Gagal menyetujui permintaan: \`${e}\``
        );
    }
});

export const owner_close_request_callback = command(
    (_c: any) => Filters.regex("^close_req\\s(\\d+)\\s(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== ctx.owner_id) {
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa melakukan ini.",
            { show_alert: true }
        );
    }
    try {
        await callback_query.edit_message_text(
            `${client.ns.emoji.cross_mark} Permintaan telah ditolak/ditutup oleh Owner Utama.`
        );
    } catch {
        // ignore
    }
});