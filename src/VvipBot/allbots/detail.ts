import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { toId } from "../../types";
import { _resolve_owner_text, send_allbots_list } from "./helpers";

async function _build_detail_text(client: any, bot_id: number): Promise<string> {
    let bot_username = "Offline";
    let bot_name = `Bot ID ${bot_id}`;
    try {
        const bot_instance = ctx.manager.running_bots.get(bot_id);
        if (bot_instance && bot_instance.is_connected) {
            bot_name = bot_instance.me.firstName;
            bot_username = bot_instance.me.username || "Tidak Ada";
        }
    } catch {
        // ignore
    }

    const owner_id = await ctx.db.getVars(bot_id, "owner_id");
    const owner_text = await _resolve_owner_text(client, owner_id);

    const exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date");
    let days_left: any = "N/A";
    if (exp_date_str) {
        const diff_ms = new Date(exp_date_str).getTime() - Date.now();
        days_left = Math.floor(diff_ms / 86400000);
    }

    const text =
        `**${client.ns.emoji.toolbox} Kelola Bot Spesifik**\n\n` +
        `• **Nama Bot:** ${bot_name}\n` +
        `• **ID Bot:** \`${bot_id}\`\n` +
        `• **Username Bot:** @${bot_username}\n` +
        `• **Pemilik:** ${owner_text}\n` +
        `• **Sisa Aktif:** \`${days_left}\` hari`;
    return text;
}

function _build_detail_layout(client: any, bot_id: number, page: number): any[][] {
    return [
        [
            {
                text: "🗑️ Hapus Bot",
                callback_data: `allbots_confirm_delete_${bot_id}_${page}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
        ],
        [
            {
                text: "🗓️ Kelola Masa Aktif",
                callback_data: `allbots_duration_${bot_id}_${page}`,
                style: "blue",
                emoji: client.ns.emoji.id("calendar"),
            },
        ],
        [
            {
                text: "🔙 Kembali ke Daftar",
                callback_data: `allbots_back_${page}`,
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
}

export const allbots_detail_callback = command(
    (_c: any) => Filters.regex(/^allbots_detail_(\d+)_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const bot_id = Math.trunc(
        Number(callback_query.matches[0].group(1))
    );
    const page = Math.trunc(Number(callback_query.matches[0].group(2)));
    const text = await _build_detail_text(client, bot_id);
    const layout = _build_detail_layout(client, bot_id, page);
    await callback_query.edit_message_text(text, {
        reply_markup: client.ns.telegram.button.build_button_grid(layout),
    });
});

export const allbots_back_callback = command(
    (_c: any) => Filters.regex(/^allbots_back_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const page = Math.trunc(Number(callback_query.matches[0].group(1)));
    await send_allbots_list(client, callback_query, page);
});