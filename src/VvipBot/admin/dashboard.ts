import { Api, TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { is_bot_owner } from "../index";

const ITEMS_PER_PAGE = 5;

function _back_to_settings_layout(client: any): any[][] {
    return [
        [
            {
                text: "• Kembali ke Pengaturan •",
                callback_data: "settings",
                style: "blue",
                emoji: client.ns.emoji.id("key"),
            },
        ],
    ];
}

function _has_photo(msg: any): boolean {
    return Boolean(msg.photo || (msg.media && msg.media.photo));
}

async function _reply(client: any, callback_query: any, text: string, btn: any) {
    if (_has_photo(callback_query.message)) {
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else {
        await callback_query.edit_message_text(text, { reply_markup: btn });
    }
}

async function _collect_platform_stats(client: any) {
    const all_bots_data = await ctx.db.getBots(true);
    const total_bots = all_bots_data.length;
    let unique_users = new Set<string>();
    let bot_user_counts: Record<number, number> = {};
    for (const bot_data of all_bots_data) {
        const bot_id = Math.trunc(Number(bot_data["name"]));
        const user_ids =
            (await ctx.db.getListVars(bot_id, "user_ids")) || [];
        bot_user_counts[bot_id] = user_ids.length;
        for (const uid of user_ids) {
            unique_users.add(uid);
        }
    }

    let top_bot_info = "N/A";
    if (Object.keys(bot_user_counts).length) {
        let top_bot_id: number | undefined;
        let top_count = -1;
        for (const [bid, count] of Object.entries(bot_user_counts)) {
            if (count > top_count) {
                top_count = count;
                top_bot_id = Number(bid);
            }
        }
        if (top_bot_id !== undefined) {
            const top_bot_instance = ctx.manager.running_bots.get(top_bot_id);
            const top_bot_name = top_bot_instance
                ? top_bot_instance.me.firstName
                : `ID ${top_bot_id}`;
            top_bot_info = `${top_bot_name} (${top_count} pengguna)`;
        }
    }

    return [total_bots, unique_users.size, top_bot_info];
}

async function _gather_server_stats(client: any) {
    try {
        const stats = await client.ns.server.monitor.get_detailed_stats();
        const stats_data = {
            cpu: stats.cpu["percent"],
            ram: stats.ram["percent"],
            disk: stats.disk["percent"],
        };
        const server_stats_text = [
            `- CPU: \`[${stats.cpu["bar"]}] ${stats.cpu["percent"]}%\``,
            `- RAM: \`[${stats.ram["bar"]}] ${stats.ram["percent"]}%\``,
            `- Disk: \`[${stats.disk["bar"]}] ${stats.disk["percent"]}%\``,
        ].join("\n");
        return [stats_data, server_stats_text];
    } catch (e) {
        const stats_data = { cpu: 0, ram: 0, disk: 0 };
        return [
            stats_data,
            `Gagal mengambil statistik server: \`${e}\``,
        ];
    }
}

export const dashboard_command_handler = command(
    (_c: any) =>
        Filters.command("dashboard") &&
        Filters.user((_c2: any) => ctx.owner_id as any),
    "message"
)(async (client: TelegramClient, message: any) => {
    const msg = await message.reply_text(
        `${client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.`
    );
    const [total_bots, total_users, top_bot_info] =
        await _collect_platform_stats(client);
    const [stats_data, server_stats_text] = await _gather_server_stats(client);

    const dashboard_text =
        `**${client.ns.emoji.chart_bar} Dashboard Platform**\n\n` +
        `**Statistik Platform:**\n` +
        `- Total Bot Aktif: \`${total_bots}\`\n` +
        `- Total Pengguna Unik: \`${total_users}\`\n` +
        `- Bot Terpopuler: \`${top_bot_info}\`\n\n` +
        `**Kesehatan Server:**\n${server_stats_text}`;
    try {
        const photo_stream = await client.ns.utils.dashboard.generate_dashboard(
            stats_data
        );
        await message.reply_photo(photo_stream, {
            caption: dashboard_text,
        });
        await msg.delete();
    } catch (e) {
        await msg.edit_text(dashboard_text + `\n\nError Visualisasi: ${e}`);
    }
});

export const refund_stars_callback = command(
    (_c: any) => Filters.regex(/^refund_stars_/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return await callback_query.answer(
            "🚫 Anda tidak memiliki izin untuk melakukan ini.",
            { show_alert: true }
        );
    }
    let db_key = "";
    try {
        const refund_key = callback_query.data.split("_")[2];
        db_key = `refund_${refund_key}`;
        const refund_data = await ctx.db.getVars(client.me.id, db_key);
        if (!refund_data) {
            await callback_query.edit_message_text(
                `${callback_query.message.text}\n\n${client.ns.emoji.exclamation} **Gagal: Transaksi tidak ditemukan atau sudah di-refund.**`
            );
            return;
        }
        const user_id_to_refund = refund_data["user_id"];
        const charge_id = refund_data["charge_id"];
        await client.refund_star_payment({
            user_id: user_id_to_refund,
            telegram_payment_charge_id: charge_id,
        });
        await callback_query.edit_message_text({
            text: `${callback_query.message.text}\n\n${client.ns.emoji.white_check_mark} Donasi berhasil dikembalikan.`,
        });
        await client.send_message(
            user_id_to_refund,
            "ℹ️ **Informasi Donasi**\n\nDonasi Stars Anda telah dikembalikan oleh admin. Terima kasih atas pengertiannya."
        );
    } catch (e) {
        ctx.log.print(`${ctx.log.RED}Gagal merefund donasi: ${e}`);
        await callback_query.edit_message_text(
            `${callback_query.message.text}\n\n${client.ns.emoji.cross_mark} **Gagal mengembalikan donasi:**\n\`${e}\``
        );
    } finally {
        if (db_key) {
            await ctx.db.removeVars(client.me.id, db_key);
        }
    }
});

function _describe_peer(peer_obj: any): string {
    if (peer_obj) {
        if (peer_obj.firstName !== undefined) {
            return peer_obj.firstName;
        }
        return peer_obj.title || "sumber tidak dikenal";
    }
    return "sumber tidak dikenal";
}

function _fmt_transaction_date(ts: number): string {
    const d = new Date(ts * 1000);
    const fmt = new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Jakarta",
    });
    const parts: Record<string, string> = {};
    for (const p of fmt.formatToParts(d)) {
        parts[p.type] = p.value;
    }
    return `${parts["day"]} ${parts["month"]}, ${parts["hour"]}:${parts["minute"]} WIB`;
}

export const show_stars_stats = command(
    (_c: any) => Filters.regex(/^stats_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }
    const page = Math.trunc(Number(callback_query.data.split("_")[1]));
    try {
        await callback_query.answer({
            message:
                "<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar.",
        });
        const peer = await client.resolve_peer(client.me.id);
        const raw_result = await client.invoke(
            new Api.payments.GetStarsTransactions({
                peer: peer,
                offset: "",
                limit: 200,
            } as any)
        );
        const transactions_history = raw_result["history"] || [];
        if (!transactions_history.length) {
            const text = "Belum ada transaksi Stars yang tercatat.";
            const btn = client.ns.telegram.button.build_button_grid(
                _back_to_settings_layout(client)
            );
            return await _reply(client, callback_query, text, btn);
        }

        let total_balance = raw_result["balance"]
            ? Number(raw_result["balance"]["amount"])
            : 0;
        let total_income = 0;
        let total_refunds = 0;
        for (const t of transactions_history) {
            const amount = t.amount ? Number(t.amount.amount) : 0;
            if (amount > 0) {
                total_income += amount;
            } else {
                total_refunds += Math.abs(amount);
            }
        }
        const total_transactions_count = transactions_history.length;
        const peer_map: Record<number, any> = {};
        for (const u of raw_result["users"] || []) {
            peer_map[Number(u.id)] = u;
        }
        for (const c of raw_result["chats"] || []) {
            peer_map[Number(c.id)] = c;
        }
        const total_pages = Math.ceil(
            total_transactions_count / ITEMS_PER_PAGE
        );
        const paginated = transactions_history.slice(
            page * ITEMS_PER_PAGE,
            (page + 1) * ITEMS_PER_PAGE
        );

        const transactions_text_list: string[] = [];
        for (const t of paginated) {
            const tx_peer = t.peer ? (t.peer as any)["peer"] : undefined;
            const peer_id = tx_peer
                ? tx_peer.user_id !== undefined
                    ? Number(tx_peer.user_id)
                    : Number(tx_peer.channel_id)
                : undefined;
            const peer_mention = _describe_peer(
                peer_id !== undefined ? peer_map[peer_id] : undefined
            );
            const amount = t.amount ? Number(t.amount.amount) : 0;
            const amount_str = amount > 0 ? `+${amount}` : String(amount);
            transactions_text_list.push(
                `• \`${_fmt_transaction_date(t.date)}\`: **${amount_str}${client.ns.emoji.star}** dari ${peer_mention}`
            );
        }

        const history_details = transactions_text_list.join("\n");
        const text =
            `**${client.ns.emoji.chart_bar} Statistik Pendapatan Stars**\n\n` +
            `${client.ns.emoji.money_bag} **Saldo Saat Ini:** \`${total_balance}\` ${client.ns.emoji.star}\n` +
            `${client.ns.emoji.chart_up} **Total Pemasukan:** \`${total_income}\` ${client.ns.emoji.star}\n` +
            `${client.ns.emoji.chart_down} **Total Pengembalian:** \`${total_refunds}\` ${client.ns.emoji.star}\n` +
            `${client.ns.emoji.repeat} **Total Transaksi (Tampil):** \`${total_transactions_count}\`\n\n` +
            `**${client.ns.emoji.open_book} Transaksi Terakhir (${page + 1}/${total_pages})**\n${history_details}`;
        const layout: any[] = [];
        if (total_pages > 1) {
            const prev_page = page > 0 ? page - 1 : total_pages - 1;
            const next_page =
                page < total_pages - 1 ? page + 1 : 0;
            layout.push([
                {
                    text: "« Sebelumnya",
                    callback_data: `stats_${prev_page}`,
                    style: "blue",
                    emoji: client.ns.emoji.id("back_arrow"),
                },
                {
                    text: "Selanjutnya »",
                    callback_data: `stats_${next_page}`,
                    style: "blue",
                    emoji: client.ns.emoji.id("right_pointing"),
                },
            ]);
        }
        layout.push(_back_to_settings_layout(client)[0]);
        const btn = client.ns.telegram.button.build_button_grid(layout);
        await _reply(client, callback_query, text, btn);
    } catch (e) {
        ctx.log.print(
            `${ctx.log.RED} Error fetching stars stats: ${e}\n${e}`
        );
        await callback_query.answer(`Error: ${e}`, {
            show_alert: true,
        });
    }
});

export const total_users_count_callback = command(
    (_c: any) => Filters.regex(/^total_users_count$/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            { show_alert: true }
        );
    }
    const user_ids = (await ctx.db.getListVars(client.me.id, "user_ids")) || [];
    const total_count = user_ids.length;
    const text =
        `**${client.ns.emoji.busts_in_silhouette} Total Pengguna Bot**\n\n` +
        `Jumlah keseluruhan pengguna yang pernah memulai bot ini adalah: **${total_count} pengguna**.`;
    const markup = client.ns.telegram.button.build_button_grid(
        _back_to_settings_layout(client)
    );
    try {
        await _reply(client, callback_query, text, markup);
    } catch (e: any) {
        if (
            e &&
            e.message &&
            String(e.message).indexOf("MESSAGE_NOT_MODIFIED") !== -1
        ) {
            await callback_query.answer();
        } else {
            await callback_query.answer(
                "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>",
                { show_alert: true }
            );
        }
    }
});