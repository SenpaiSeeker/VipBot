import { TelegramClient } from "teleproto";
import { command, ctx, is_bot_owner } from "../index";
import { Filters } from "../filters";
import { toId } from "../../types";

type Any = any;

async function _owner_only(
    client: TelegramClient,
    callback_query: Any
): Promise<boolean> {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return true;
    }
    return false;
}

async function _unwrap_user(client: Any, user_id: Any): Promise<Any | undefined> {
    const users = await client.get_users(toId(user_id));
    return Array.isArray(users) ? users[0] : users;
}

function _back_to_settings(client: Any): Any {
    return {
        text: "• Kembali ke Pengaturan •",
        callback_data: "settings",
        style: "blue",
        emoji: client.ns.emoji.id("toolbox"),
    };
}

function _back_to_group_selection(client: Any): Any {
    return {
        text: "• Kembali ke Pemilihan Grup •",
        callback_data: "check_active_menu_init",
        style: "blue",
        emoji: client.ns.emoji.id("back_arrow"),
    };
}

async function _reply(client: Any, callback_query: Any, text: string, btn: Any): Promise<Any> {
    if (callback_query.message.photo) {
        return await callback_query.edit_message_caption(text, { reply_markup: btn });
    }
    return await callback_query.edit_message_text(text, { reply_markup: btn });
}

function _fmt_full(d: Date): string {
    const fmt = new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Jakarta",
    });
    const parts: Record<string, string> = {};
    for (const p of fmt.formatToParts(d)) {
        parts[p.type] = p.value;
    }
    return `${parts["day"]} ${parts["month"]} ${parts["year"]}, ${parts["hour"]}:${parts["minute"]} WIB`;
}

function _title(s: Any): string {
    return String(s).replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function _button_name(user: Any): string {
    return String(user.firstName || user.id).slice(0, 15);
}

function _shuffle<T>(arr: T[]): T[] {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

export const list_members_callback = command(
    (_c: any) => Filters.regex(/^list_members_(\-?\d+)$/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (await _owner_only(client, callback_query)) {
        return;
    }

    const members_list =
        (await ctx.db.getListVars(client.me.id, "vvip_members")) || [];
    const back_row = [_back_to_settings(client)];

    if (!members_list.length) {
        const text = `${client.ns.emoji.white_check_mark} Tidak ada member VVIP yang tercatat di database.`;
        const btn = client.ns.telegram.button.build_button_grid([back_row]);
        return await _reply(client, callback_query, text, btn);
    }

    const total_pages = members_list.length;
    let page = 0;
    try {
        page = Math.trunc(
            Number(callback_query.data.split("_")[callback_query.data.split("_").length - 1])
        );
        page = ((page + total_pages) % total_pages + total_pages) % total_pages;
    } catch {
        page = 0;
    }

    const member_data = members_list[page];
    let user_id: Any;
    let vvip_name: Any;
    let join_date_iso: Any;
    let pay_type: Any;
    let user: Any;
    try {
        user_id = member_data["user_id"];
        vvip_name = member_data["vvip_name"];
        join_date_iso = member_data["join_date"];
        pay_type = member_data["payment_type"];
        user = await _unwrap_user(client, user_id);
    } catch (e: Any) {
        const text_error =
            `Data member ini tampaknya rusak atau pengguna tidak dapat diakses lagi.\n` +
            `\`Error: ${e}\`\n\n` +
            "Entri ini telah dihapus dari daftar untuk menjaga kebersihan data.";
        const btn_back = client.ns.telegram.button.build_button_grid(back_row);
        await _reply(client, callback_query, text_error, btn_back);
        await ctx.db.removeListVars(client.me.id, "vvip_members", member_data);
        return;
    }

    let expiry_date_str = "Permanen";
    const expiry_raw = member_data["expiry_date"];
    if (expiry_raw) {
        expiry_date_str = _fmt_full(new Date(expiry_raw));
    }

    const mention_str = client.ns.telegram.arg.getMention(user);
    const join_str = _fmt_full(new Date(join_date_iso));
    const text =
        `**${client.ns.emoji.busts_in_silhouette} Daftar Member VVIP (${page + 1}/${total_pages})**\n\n` +
        `**Nama:** ${mention_str}\n` +
        `**ID:** \`${user.id}\`\n` +
        `**Kategori:** \`${vvip_name}\` (${_title(pay_type)})\n` +
        `**Bergabung:** \`${join_str}\`\n` +
        `**Kedaluwarsa:** \`${expiry_date_str}\``;
    const button_name = _button_name(user);

    const layout: Any[] = [];
    if (total_pages > 1) {
        const prev_page = ((page - 1 + total_pages) % total_pages + total_pages) % total_pages;
        const next_page = (page + 1) % total_pages;
        layout.push([
            {
                text: "« Sebelumnya",
                callback_data: `list_members_${prev_page}`,
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
            {
                text: "Selanjutnya »",
                callback_data: `list_members_${next_page}`,
                style: "blue",
                emoji: client.ns.emoji.id("right_pointing"),
            },
        ]);
    }

    layout.push([
        {
            text: `🚨 Tendang ${button_name}`,
            callback_data: `kick_${user.id}_${vvip_name}`,
            style: "red",
            emoji: client.ns.emoji.id("minus"),
        },
    ]);
    layout.push(back_row);
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});

export const confirm_kick_member_callback = command(
    (_c: any) => Filters.regex(/^kick_(\d+)_(.+)/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (await _owner_only(client, callback_query)) {
        return;
    }
    const match = callback_query.matches[0];
    const user_id_str = match.group(1);
    const vvip_name = match.group(2);
    const user = await _unwrap_user(client, Math.trunc(Number(user_id_str)));
    const mention_str = client.ns.telegram.arg.getMention(user);

    const text =
        `**${client.ns.emoji.exclamation} Konfirmasi Penendangan**\n\n` +
        `Anda yakin ingin menendang **${mention_str}** dari grup VVIP **${vvip_name}**?\n\n` +
        "Pengguna akan dikeluarkan dari grup dan data keanggotaannya akan dihapus.";
    const layout = [
        [
            {
                text: "✅ Ya, Tendang",
                callback_data: `do_kick_${user_id_str}_${vvip_name}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
            {
                text: "❌ Tidak",
                callback_data: "list_members_0",
                style: "green",
                emoji: client.ns.emoji.id("white_check_mark"),
            },
        ],
    ];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});

export const do_kick_member_callback = command(
    (_c: any) => Filters.regex(/^do_kick_(\d+)_(.+)/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (await _owner_only(client, callback_query)) {
        return;
    }
    const match = callback_query.matches[0];
    const user_id = Math.trunc(Number(match.group(1)));
    const vvip_name = match.group(2);

    const members_list =
        (await ctx.db.getListVars(client.me.id, "vvip_members")) || [];
    let record: Any = undefined;
    for (const r of members_list) {
        if (
            Number(r["user_id"]) === user_id &&
            String(r["vvip_name"]) === String(vvip_name)
        ) {
            record = r;
            break;
        }
    }
    if (!record) {
        return await callback_query.edit_message_caption(
            `${client.ns.emoji.cross_mark} **Gagal:** Record keanggotaan tidak ditemukan di database.`
        );
    }

    const chat_id_kick = record["chat_id_kick"];
    if (!chat_id_kick) {
        return await callback_query.edit_message_caption(
            `${client.ns.emoji.cross_mark} **Gagal:** Chat ID untuk menendang member tidak valid atau belum diatur di paket VVIP.`
        );
    }

    await callback_query.edit_message_caption(
        `${client.ns.emoji.hourglass} \`Memproses penendangan member dari grup...\``
    );
    try {
        const chat_id_kick_num = Math.trunc(Number(chat_id_kick));
        await client.ban_chat_member(chat_id_kick_num, user_id);
        await new Promise((r) => setTimeout(r, 1000));
        await client.unban_chat_member(chat_id_kick_num, user_id);
        await ctx.db.removeListVars(client.me.id, "vvip_members", record);

        const user_to_kick = await _unwrap_user(client, user_id);
        const mention_str = client.ns.telegram.arg.getMention(user_to_kick);
        const layout = [[_back_to_settings(client)]];
        const btn_back = client.ns.telegram.button.build_button_grid(layout);
        await callback_query.edit_message_caption(
            `${client.ns.emoji.white_check_mark} **Sukses!**\n` +
                `Pengguna ${mention_str} telah ditendang dari **${vvip_name}** dan dihapus dari daftar.`,
            { reply_markup: btn_back }
        );
    } catch (e: Any) {
        await callback_query.edit_message_caption(
            `${client.ns.emoji.cross_mark} **Gagal Menendang:** \`${e}\``
        );
    }
});

export const check_active_menu_callback = command(
    (_c: any) => Filters.regex(/^check_active_menu/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (await _owner_only(client, callback_query)) {
        return;
    }

    if ((callback_query.data_string || "").indexOf("init") !== -1) {
        ctx.ACTIVE_MEMBERS_CACHE = {};
    }

    const vvip_list = (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    const layout: Any[] = [];
    let button_row: Any[] = [];
    for (const item of vvip_list) {
        const name = item["name"];
        const chat_id_norm = item["chat_id_normal"];
        const chat_id_promo = item["chat_id_promo"];
        if (name && chat_id_norm) {
            button_row.push({
                text: `👥 Cek '${name}' Normal`,
                callback_data: `list_active_${chat_id_norm}_0`,
                style: "blue",
                emoji: client.ns.emoji.id("busts_in_silhouette"),
            });
        }
        if (name && chat_id_promo) {
            button_row.push({
                text: `👥 Cek '${name}' Promo`,
                callback_data: `list_active_${chat_id_promo}_0`,
                style: "blue",
                emoji: client.ns.emoji.id("busts_in_silhouette"),
            });
        }
        if (button_row.length === 2) {
            layout.push(button_row);
            button_row = [];
        }
    }
    if (button_row.length) {
        layout.push(button_row);
    }

    const back_row = [_back_to_settings(client)];
    if (!layout.length) {
        const text =
            "Tidak ada VVIP dengan Chat ID valid yang terkonfigurasi. Silakan atur terlebih dahulu.";
        const btn = client.ns.telegram.button.build_button_grid([back_row]);
        return await _reply(client, callback_query, text, btn);
    }

    layout.push(back_row);
    const text =
        `**${client.ns.emoji.mag} Cek Member Aktif Real-time**\n\n` +
        "Pilih grup yang ingin Anda periksa untuk melihat daftar anggotanya saat ini.";
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});

export const list_active_members_callback = command(
    (_c: any) => Filters.regex(/^list_active_(\-?\d+)_(\-?\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (await _owner_only(client, callback_query)) {
        return;
    }

    let chat_id: number;
    let page: number;
    try {
        const parts = callback_query.data.split("_");
        chat_id = Math.trunc(Number(parts[2]));
        page = Math.trunc(Number(parts[3]));
    } catch {
        return await callback_query.answer("Data callback tidak valid.");
    }

    if (!(chat_id in ctx.ACTIVE_MEMBERS_CACHE)) {
        try {
            await callback_query.answer({
                message:
                    "<emoji id=5451732530048802485>⏳</emoji> " +
                    "Mengambil data member dari server Telegram, mohon tunggu...",
            });
            const raw_members = await client.get_chat_members(chat_id);
            const members = raw_members.filter((m: Any) => m.user && !m.user.bot);
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = _shuffle(members);
        } catch (e: Any) {
            await callback_query.edit_message_caption(
                `${client.ns.emoji.cross_mark} **Gagal Mengambil Daftar Member:**\n\`${e}\``
            );
            return;
        }
    }

    const all_members = ctx.ACTIVE_MEMBERS_CACHE[chat_id] || [];
    if (!all_members.length) {
        return await callback_query.edit_message_caption(
            "Tidak ada anggota (non-bot) yang ditemukan di dalam grup ini."
        );
    }

    const total = all_members.length;
    page = ((page + total) % total + total) % total;
    const member = all_members[page];
    const user = member.user;

    const mention_str = client.ns.telegram.arg.getMention(user);
    const text =
        `**${client.ns.emoji.mag} Member Aktif (${page + 1}/${total})**\n\n` +
        `**Nama:** ${mention_str}\n` +
        `**ID:** \`${user.id}\`\n` +
        `**Status:** \`${_title((member.status && member.status.name) || "MemberStatusMember")}\``;
    const button_name = _button_name(user);

    const layout: Any[] = [];
    if (total > 1) {
        const prev_p = ((page - 1 + total) % total + total) % total;
        const next_p = (page + 1) % total;
        layout.push([
            {
                text: "«",
                callback_data: `list_active_${chat_id}_${prev_p}`,
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
            {
                text: "»",
                callback_data: `list_active_${chat_id}_${next_p}`,
                style: "blue",
                emoji: client.ns.emoji.id("right_pointing"),
            },
        ]);
    }

    layout.push(
        [
            {
                text: `🚨 Tendang ${button_name}`,
                callback_data: `kick_active_${chat_id}_${user.id}_${page}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
        ],
        [_back_to_group_selection(client)]
    );
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});

export const confirm_kick_active_callback = command(
    (_c: any) => Filters.regex(/^kick_active_(\-?\d+)_(\d+)_(\-?\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (await _owner_only(client, callback_query)) {
        return;
    }

    const parts = callback_query.data.split("_");
    const chat_id_str = parts[2];
    const user_id_str = parts[3];
    const page_str = parts[4];
    const user = await _unwrap_user(client, Math.trunc(Number(user_id_str)));
    const mention_str = client.ns.telegram.arg.getMention(user);

    const text =
        `**${client.ns.emoji.exclamation} Konfirmasi**\n\n` +
        `Anda yakin ingin menendang **${mention_str}** dari grup?`;
    const layout = [
        [
            {
                text: "✅ Ya, Tendang",
                callback_data: `do_kick_active_${chat_id_str}_${user_id_str}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
            {
                text: "❌ Tidak, Batalkan",
                callback_data: `list_active_${chat_id_str}_${page_str}`,
                style: "green",
                emoji: client.ns.emoji.id("white_check_mark"),
            },
        ],
    ];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});

export const do_kick_active_callback = command(
    (_c: any) => Filters.regex(/^do_kick_active_(\-?\d+)_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (await _owner_only(client, callback_query)) {
        return;
    }

    const parts = callback_query.data.split("_");
    const chat_id = Math.trunc(Number(parts[3]));
    const user_id = Math.trunc(Number(parts[4]));

    try {
        await callback_query.edit_message_caption(
            `${client.ns.emoji.hourglass} \`Memproses penendangan pengguna...\``
        );
        await client.ban_chat_member(chat_id, user_id);
        await client.unban_chat_member(chat_id, user_id);

        const members_list =
            (await ctx.db.getListVars(client.me.id, "vvip_members")) || [];
        let record: Any = undefined;
        for (const r of members_list) {
            if (
                Number(r["user_id"]) === user_id &&
                Number(r["chat_id_kick"]) === chat_id
            ) {
                record = r;
                break;
            }
        }
        if (record) {
            await ctx.db.removeListVars(client.me.id, "vvip_members", record);
        }

        if (chat_id in ctx.ACTIVE_MEMBERS_CACHE) {
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = ctx.ACTIVE_MEMBERS_CACHE[
                chat_id
            ].filter((m: Any) => {
                const muid = m.user && m.user.id;
                return Number(muid) !== user_id;
            });
        }

        const user = await _unwrap_user(client, user_id);
        const mention_str = client.ns.telegram.arg.getMention(user);
        const text =
            `${client.ns.emoji.white_check_mark} **Sukses!**\n` +
            `Pengguna **${mention_str}** telah ditendang dari grup.`;
        const layout = [[_back_to_group_selection(client)]];
        const btn = client.ns.telegram.button.build_button_grid(layout);
        await _reply(client, callback_query, text, btn);
    } catch (e: Any) {
        await callback_query.edit_message_caption(
            `${client.ns.emoji.cross_mark} **Gagal Menendang:** \`${e}\``
        );
    }
});