import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { toId } from "../../types";

async function _get_bot_status(
    client: TelegramClient,
    bot_id: number
): Promise<[string, string]> {
    let bot_name = `ID ${bot_id} (Offline)`;
    let bot_username = "N/A";
    try {
        const bot_instance = ctx.manager.running_bots.get(bot_id);
        if (bot_instance && bot_instance.is_connected) {
            bot_name = bot_instance.me.firstName;
            bot_username = bot_instance.me.username;
        }
    } catch {
        bot_name = `ID ${bot_id} (Error)`;
    }
    return [bot_name, bot_username];
}

async function _reply(
    client: TelegramClient,
    callback_query: any,
    text: string,
    btn: any
): Promise<void> {
    if (callback_query.message && callback_query.message.photo) {
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else {
        await callback_query.edit_message_text(text, { reply_markup: btn });
    }
}

function _daysLeft(exp_date_str: string | null): number | string | null {
    if (!exp_date_str) {
        return null;
    }
    const ms = new Date(exp_date_str).getTime() - Date.now();
    return Math.floor(ms / (24 * 3600 * 1000));
}

export const list_my_bots_callback = command(
    (_c: any) => Filters.regex("^list_my_bots(_\\d+)?$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const user_id = callback_query.from_user.id;
    const all_bots_data = await ctx.db.getBots(true);

    const my_bots = [];
    for (const b of all_bots_data) {
        const owner = await ctx.db.getVars(Number(b.name), "owner_id");
        if ((owner || 0) == user_id) {
            my_bots.push(b);
        }
    }

    if (!my_bots.length) {
        return await callback_query.answer(
            "Anda belum memiliki bot. Tekan 'Buat Bot' untuk memulai.",
            { show_alert: true }
        );
    }

    const parts = callback_query.data_string.split("_");
    let page =
        parts.length > 2 && /^\d+$/.test(parts[parts.length - 1])
            ? parseInt(parts[parts.length - 1], 10)
            : 0;
    const total_pages = my_bots.length;
    page = (page + total_pages) % total_pages;

    const bot_data = my_bots[page];
    const bot_id = Number(bot_data.name);
    const [bot_name, bot_username] = await _get_bot_status(client, bot_id);

    const exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date");
    const days_left = _daysLeft(exp_date_str);

    const text =
        `**${client.ns.emoji.folder} Daftar Bot Saya (${page + 1}/${total_pages})**\n\n` +
        `• **Nama Bot:** ${bot_name}\n` +
        `• **ID Bot:** \`${bot_id}\`\n` +
        `• **Username Bot:** @${bot_username}\n` +
        `• **Sisa Masa Aktif:** \`${days_left === null ? "N/A" : days_left}\` hari`;

    const layout: any[] = [];
    if (total_pages > 1) {
        const prev_page = (page - 1 + total_pages) % total_pages;
        const next_page = (page + 1) % total_pages;
        layout.push([
            {
                text: "« Sebelumnya",
                callback_data: `list_my_bots_${prev_page}`,
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
            {
                text: "Selanjutnya »",
                callback_data: `list_my_bots_${next_page}`,
                style: "blue",
                emoji: client.ns.emoji.id("right_pointing"),
            },
        ]);
    }

    layout.push(
        [
            {
                text: `⚙️ Kelola ${bot_name}`,
                callback_data: `manage_bot ${bot_id}`,
                style: "blue",
                emoji: client.ns.emoji.id("toolbox"),
            },
        ],
        [
            {
                text: "• Kembali •",
                callback_data: "start",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ]
    );
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});

export const manage_bot_callback = command(
    (_c: any) => Filters.regex("^manage_bot\\s(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const bot_id_to_manage = Math.trunc(
        Number(callback_query.data_string.split(" ", 2)[1])
    );
    const user_id = callback_query.from_user.id;
    const owner_of_target_bot =
        (await ctx.db.getVars(bot_id_to_manage, "owner_id")) || 0;

    if (toId(user_id) !== toId(owner_of_target_bot) && toId(user_id) !== ctx.owner_id) {
        return await callback_query.answer("Ini bukan bot milik Anda.", {
            show_alert: true,
        });
    }

    let bot_name = `ID ${bot_id_to_manage}`;
    try {
        const bot_instance = ctx.manager.running_bots.get(bot_id_to_manage);
        if (bot_instance && bot_instance.is_connected) {
            bot_name = bot_instance.me.firstName;
        }
    } catch {
        // ignore
    }

    const exp_date_str = await ctx.db.getVars(bot_id_to_manage, "bot_expiration_date");
    let days_left_text = "Tidak diatur";
    if (exp_date_str) {
        const days_left = _daysLeft(exp_date_str);
        days_left_text = `${days_left} hari`;
    }

    const layout = [
        [
            {
                text: "➕ Minta Perpanjangan",
                callback_data: `request_extend_duration ${bot_id_to_manage}`,
                style: "green",
                emoji: client.ns.emoji.id("plus"),
            },
        ],
        [
            {
                text: "🗑️ Hapus Bot Ini",
                callback_data: `confirm_delete_bot ${bot_id_to_manage}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
        ],
        [
            {
                text: "⬅️ Kembali ke Daftar Bot",
                callback_data: "list_my_bots_0",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];

    const text =
        `**${client.ns.emoji.toolbox} Kelola Bot: ${bot_name}**\n\n` +
        `**ID Bot:** \`${bot_id_to_manage}\`\n` +
        `**Sisa Masa Aktif:** \`${days_left_text}\`\n\n` +
        "Pilih tindakan yang ingin Anda lakukan:";
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});