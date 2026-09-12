import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { toId } from "../../types";
import { invalidate_page_cache, send_allbots_list } from "./helpers";

function _expiry_delta_layout(
    client: any,
    bot_id: number,
    page: number,
    sign: string,
    days: number
): any {
    const callback_prefix =
        sign === "+" ? "allbots_do_extend" : "allbots_do_reduce";
    const style = sign === "+" ? "green" : "red";
    const emoji =
        sign === "+"
            ? client.ns.emoji.id("plus")
            : client.ns.emoji.id("minus");
    return {
        text: `${sign}${days} hari`,
        callback_data: `${callback_prefix}_${bot_id}_${days}_${page}`,
        style: style,
        emoji: emoji,
    };
}

export const allbots_duration_callback = command(
    (_c: any) => Filters.regex(/^allbots_duration_(\d+)_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const bot_id = Math.trunc(Number(callback_query.matches[0].group(1)));
    const page = Math.trunc(Number(callback_query.matches[0].group(2)));
    const layout = [
        [
            {
                text: "➕ Tambah Masa Aktif",
                callback_data: `allbots_extend_${bot_id}_${page}`,
                style: "green",
                emoji: client.ns.emoji.id("plus"),
            },
        ],
        [
            {
                text: "➖ Kurangi Masa Aktif",
                callback_data: `allbots_reduce_${bot_id}_${page}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
        ],
        [
            {
                text: "• Kembali •",
                callback_data: `allbots_back_${page}`,
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
    await callback_query.edit_message_text(
        `**${client.ns.emoji.calendar} Kelola Masa Aktif untuk Bot \`${bot_id}\`**`,
        { reply_markup: client.ns.telegram.button.build_button_grid(layout) }
    );
});

export const allbots_extend_callback = command(
    (_c: any) => Filters.regex(/^allbots_extend_(\d+)_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const bot_id = Math.trunc(Number(callback_query.matches[0].group(1)));
    const page = Math.trunc(Number(callback_query.matches[0].group(2)));
    const buttons = [7, 30, 90].map((days) =>
        _expiry_delta_layout(client, bot_id, page, "+", days)
    );
    const layout = [
        buttons,
        [
            {
                text: "• Kembali •",
                callback_data: `allbots_duration_${bot_id}_${page}`,
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
    await callback_query.edit_message_text(
        `Pilih durasi untuk ditambahkan ke Bot \`${bot_id}\`:`,
        { reply_markup: client.ns.telegram.button.build_button_grid(layout) }
    );
});

export const allbots_do_extend_callback = command(
    (_c: any) => Filters.regex(/^allbots_do_extend_(\d+)_(\d+)_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const bot_id = Math.trunc(Number(callback_query.matches[0].group(1)));
    const days = Math.trunc(Number(callback_query.matches[0].group(2)));
    const page = Math.trunc(Number(callback_query.matches[0].group(3)));
    const current_expiry_str = await ctx.db.getVars(
        bot_id,
        "bot_expiration_date"
    );
    let start_date = new Date();
    if (current_expiry_str) {
        const current_expiry = new Date(current_expiry_str);
        if (current_expiry.getTime() > start_date.getTime()) {
            start_date = current_expiry;
        }
    }
    await ctx.db.setVars(
        bot_id,
        "bot_expiration_date",
        new Date(start_date.getTime() + days * 86400000).toISOString()
    );
    await callback_query.answer({
        message: `${days} hari berhasil ditambahkan ke bot ${bot_id}.`,
        show_alert: true,
    });
    invalidate_page_cache(page);
    await send_allbots_list(client, callback_query, page, true);
});

export const allbots_reduce_callback = command(
    (_c: any) => Filters.regex(/^allbots_reduce_(\d+)_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const bot_id = Math.trunc(Number(callback_query.matches[0].group(1)));
    const page = Math.trunc(Number(callback_query.matches[0].group(2)));
    const buttons = [7, 30, 90].map((days) =>
        _expiry_delta_layout(client, bot_id, page, "-", days)
    );
    const layout = [
        buttons,
        [
            {
                text: "• Kembali •",
                callback_data: `allbots_duration_${bot_id}_${page}`,
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
    await callback_query.edit_message_text(
        `Pilih durasi untuk dikurangi dari Bot \`${bot_id}\`:`,
        { reply_markup: client.ns.telegram.button.build_button_grid(layout) }
    );
});

export const allbots_do_reduce_callback = command(
    (_c: any) => Filters.regex(/^allbots_do_reduce_(\d+)_(\d+)_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const bot_id = Math.trunc(Number(callback_query.matches[0].group(1)));
    const days = Math.trunc(Number(callback_query.matches[0].group(2)));
    const page = Math.trunc(Number(callback_query.matches[0].group(3)));
    const current_expiry_str = await ctx.db.getVars(
        bot_id,
        "bot_expiration_date"
    );
    if (!current_expiry_str) {
        await callback_query.answer({
            message: "Bot ini tidak memiliki tanggal kedaluwarsa untuk dikurangi.",
            show_alert: true,
        });
        return;
    }
    const new_expiry_date = new Date(
        new Date(current_expiry_str).getTime() - days * 86400000
    );
    await ctx.db.setVars(
        bot_id,
        "bot_expiration_date",
        new_expiry_date.toISOString()
    );
    await callback_query.answer({
        message: `Masa aktif bot ${bot_id} berhasil dikurangi ${days} hari.`,
        show_alert: true,
    });
    invalidate_page_cache(page);
    await send_allbots_list(client, callback_query, page, true);
});