import { TelegramClient } from "teleproto";
import { command, ctx, seller_only } from "../index";
import { Filters, and_ } from "../filters";
import { toId } from "../../types";

type Any = any;

async function _unwrap_user(client: Any, user_id: Any): Promise<Any | undefined> {
    const users = await client.get_users(user_id);
    return Array.isArray(users) ? users[0] : users;
}

async function _build_seller_list(client: Any): Promise<[string | null, Any]> {
    const seller_list =
        (await ctx.db.getListVars(ctx.owner_id, "seller_id_list")) || [];
    if (!seller_list.length) {
        return [null, "Belum ada seller yang terdaftar."];
    }
    let text = `**${client.ns.emoji.bust_in_silhouette} Daftar Seller Aktif**\n\n`;
    const keyboard: Any[] = [];
    let index = 0;
    for (const user_id of seller_list) {
        index += 1;
        let mention: string;
        try {
            const user_obj = await _unwrap_user(client, user_id);
            mention = client.ns.telegram.arg.getMention(user_obj);
        } catch {
            mention = `ID: \`${user_id}\``;
        }
        text += `${index}. ${mention}\n`;
        keyboard.push([
            {
                text: `Hapus Seller 🗑️ (${user_id})`,
                callback_data: `del_sell_${user_id}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
        ]);
    }
    const btn = client.ns.telegram.button.build_button_grid(keyboard);
    return [text, btn];
}

async function _build_access_list(client: Any): Promise<[string | null, Any]> {
    const user_ids = (await ctx.db.getListVars(client.me.id, "user_ids")) || [];
    const access_users: Any[] = [];
    for (const uid of user_ids) {
        const exp = await ctx.db.getVars(uid, "user_expiry_date");
        if (exp) {
            access_users.push(uid);
        }
    }
    if (!access_users.length) {
        return [null, "Tidak ada pengguna yang memiliki akses aktif saat ini."];
    }
    let text = `**${client.ns.emoji.key} Daftar Pengguna Berakses**\n\n`;
    const keyboard: Any[] = [];
    let index = 0;
    for (const uid of access_users) {
        index += 1;
        let mention: string;
        try {
            const user_obj = await _unwrap_user(client, uid);
            mention = client.ns.telegram.arg.getMention(user_obj);
        } catch {
            mention = `ID: \`${uid}\``;
        }
        text += `${index}. ${mention}\n`;
        keyboard.push([
            {
                text: `Cabut Akses 🚫 (${uid})`,
                callback_data: `del_acc_${uid}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
        ]);
    }
    const btn = client.ns.telegram.button.build_button_grid(keyboard);
    return [text, btn];
}

function _fmt_jakarta_long(d: Date): string {
    const fmt = new Intl.DateTimeFormat("id-ID", {
        day: "2-digit",
        month: "long",
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

export const access_command_handler = command(
    (_c: any) => Filters.command("akses")
)(seller_only(async (client: TelegramClient, message: Any) => {
    const [user_id_target] = await client.ns.telegram.arg.getReasonAndId(
        message
    );
    if (!user_id_target) {
        return await message.reply_text(
            "**Format Salah.**\nGunakan: `/akses <user_id atau @username>`"
        );
    }
    try {
        const target_user = await _unwrap_user(client, user_id_target);
        let has_access = false;
        const user_expiry_str = await ctx.db.getVars(
            target_user.id,
            "user_expiry_date"
        );
        if (user_expiry_str) {
            const expiry_date = new Date(user_expiry_str);
            if (expiry_date.getTime() > Date.now()) {
                has_access = true;
            }
        }
        const status_text = has_access
            ? `${client.ns.emoji.white_check_mark} Memiliki Akses`
            : `${client.ns.emoji.cross_mark} Tidak Memiliki Akses`;
        const text =
            `**${client.ns.emoji.key} Kelola Akses Pembuatan Bot**\n\n` +
            `**Pengguna:** ${client.ns.telegram.arg.getMention(target_user)}\n` +
            `**ID:** \`${target_user.id}\`\n` +
            `**Status:** \`${status_text}\`\n\n` +
            "Pilih tindakan untuk pengguna ini:";
        const layout = [
            [
                {
                    text: "✅ Beri Akses",
                    callback_data: `give_access_${target_user.id}`,
                    style: "green",
                    emoji: client.ns.emoji.id("white_check_mark"),
                },
                {
                    text: "❌ Cabut Akses",
                    callback_data: `revoke_access_${target_user.id}`,
                    style: "red",
                    emoji: client.ns.emoji.id("cross_mark"),
                },
            ],
        ];
        const btn = client.ns.telegram.button.build_button_grid(layout);
        await message.reply_text(text, { reply_markup: btn });
    } catch (e: Any) {
        await message.reply_text(`Gagal memproses. Error: \`${e}\``);
    }
}));

export const give_access_callback = command(
    (_c: any) => Filters.regex(/^give_access_(\d+)/),
    "callback"
)(seller_only(async (client: TelegramClient, callback_query: Any) => {
    const target_id = callback_query.data.split("_").pop();
    const layout = [
        [1, 3, 6, 12].map((m) => ({
            text: `${m} Bulan`,
            callback_data: `do_give_${target_id}_${m}`,
            style: "blue",
            emoji: client.ns.emoji.id("calendar"),
        })),
        [
            {
                text: "• Kembali •",
                callback_data: "close_panel",
                style: "red",
                emoji: client.ns.emoji.id("cross_mark"),
            },
        ],
    ];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await callback_query.edit_message_text(
        "Pilih durasi akses yang ingin diberikan:",
        { reply_markup: btn }
    );
}));

export const do_give_access_callback = command(
    (_c: any) => Filters.regex(/^do_give_(\d+)_(\d+)/),
    "callback"
)(seller_only(async (client: TelegramClient, callback_query: Any) => {
    const data = callback_query.data.split("_");
    const target_id = Math.trunc(Number(data[2]));
    const months_to_add = Math.trunc(Number(data[3]));
    try {
        const target_user = await _unwrap_user(client, target_id);
        const current_expiry_str = await ctx.db.getVars(
            target_id,
            "user_expiry_date"
        );
        let start_date = new Date();
        if (current_expiry_str) {
            const current_expiry = new Date(current_expiry_str);
            if (current_expiry.getTime() > start_date.getTime()) {
                start_date = current_expiry;
            }
        }
        const new_expiry_date = new Date(
            start_date.getTime() + 30 * months_to_add * 24 * 3600 * 1000
        );
        await ctx.db.setVars(
            target_id,
            "user_expiry_date",
            new_expiry_date.toISOString()
        );

        const mention_str = client.ns.telegram.arg.getMention(target_user);
        const formatted_jakarta_date = _fmt_jakarta_long(new_expiry_date);
        await callback_query.edit_message_text(
            `${client.ns.emoji.white_check_mark} **Akses Diberikan!**\n\n` +
                `Pengguna ${mention_str} sekarang memiliki akses untuk membuat bot selama **${months_to_add} bulan**.\n\n` +
                `Masa aktif akses hingga: \`${formatted_jakarta_date}\``
        );
        await callback_query.answer({
            message: `<emoji id=6296367896398399651>✅</emoji> Akses berhasil diberikan kepada ${target_id}`,
        });
    } catch (e: Any) {
        await callback_query.answer(`Gagal memproses. Error: \`${e}\``, {
            show_alert: true,
        });
    }
}));

export const revoke_access_callback = command(
    (_c: any) => Filters.regex(/^revoke_access_(\d+)/),
    "callback"
)(seller_only(async (client: TelegramClient, callback_query: Any) => {
    const target_id = callback_query.data.split("_").pop();
    try {
        const target_user = await _unwrap_user(client, target_id);
        const mention = client.ns.telegram.arg.getMention(target_user);
        await ctx.db.removeVars(target_id, "user_expiry_date");
        await callback_query.answer({
            message: `<emoji id=6298671811345254603>❌</emoji> Akses berhasil dicabut dari ${target_id}`,
        });
        await callback_query.edit_message_text(
            `${client.ns.emoji.cross_mark} **Akses Dicabut!**\n\n` +
                `Pengguna ${mention} tidak lagi memiliki hak untuk membuat bot.`
        );
    } catch (e: Any) {
        await callback_query.answer(`Gagal memproses. Error: \`${e}\``, {
            show_alert: true,
        });
    }
}));

export const add_seller_handler = command(
    (_c: any) =>
        and_(
            Filters.command("addseller"),
            Filters.user((_c2: any) => ctx.owner_id as Any)
        ),
    "message"
)(async (client: TelegramClient, message: Any) => {
    const [user_id_target] = await client.ns.telegram.arg.getReasonAndId(
        message
    );
    if (!user_id_target) {
        return await message.reply_text(
            `${client.ns.emoji.cross_mark} Pengguna tidak ditemukan. Pastikan ID/Username benar atau balas pesan pengguna.`
        );
    }
    try {
        const target_user = await _unwrap_user(client, user_id_target);
        const seller_list =
            (await ctx.db.getListVars(ctx.owner_id, "seller_id_list")) || [];
        if (toId(target_user.id) === toId(ctx.owner_id)) {
            return;
        }
        if (
            seller_list.some((s: Any) => toId(s) === toId(target_user.id))
        ) {
            return await message.reply_text(
                `${client.ns.emoji.cross_mark} User \`${target_user.id}\` sudah terdaftar sebagai seller.`
            );
        }
        await ctx.db.setListVars(
            ctx.owner_id,
            "seller_id_list",
            target_user.id
        );
        const user_mention = client.ns.telegram.arg.getMention(target_user);
        await message.reply_text(
            `${client.ns.emoji.white_check_mark} Berhasil menambahkan \`${user_mention}\` sebagai seller.`
        );
    } catch (e: Any) {
        await message.reply_text(
            `${client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>${e}</pre>`
        );
    }
});

export const list_seller_handler = command(
    (_c: any) =>
        and_(
            Filters.command("listseller"),
            Filters.user((_c2: any) => ctx.owner_id as Any)
        ),
    "message"
)(async (client: TelegramClient, message: Any) => {
    const [text, btn] = await _build_seller_list(client);
    if (text === null) {
        return await message.reply_text(btn);
    }
    await message.reply_text(text, { reply_markup: btn });
});

export const delete_seller_callback = command(
    (_c: any) => Filters.regex(/^del_sell_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const target_id = callback_query.matches[0].group(1);
    await ctx.db.removeListVars(ctx.owner_id, "seller_id_list", target_id);
    await callback_query.answer({
        message: `Seller \`${target_id}\` berhasil dihapus.`,
        show_alert: true,
    });
    const [text, btn] = await _build_seller_list(client);
    if (text === null) {
        return await callback_query.edit_message_text(btn);
    }
    await callback_query.edit_message_text(text, { reply_markup: btn });
});

export const list_akses_handler = command(
    (_c: any) =>
        and_(
            Filters.command("listakses"),
            Filters.user((_c2: any) => ctx.owner_id as Any)
        ),
    "message"
)(async (client: TelegramClient, message: Any) => {
    const [text, btn] = await _build_access_list(client);
    if (text === null) {
        return await message.reply_text(btn);
    }
    await message.reply_text(text, { reply_markup: btn });
});

export const delete_access_callback = command(
    (_c: any) => Filters.regex(/^del_acc_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const target_id = callback_query.matches[0].group(1);
    await ctx.db.removeVars(target_id, "user_expiry_date");
    await callback_query.answer({
        message: `Akses untuk \`${target_id}\` telah dicabut.`,
        show_alert: true,
    });
    const [text, btn] = await _build_access_list(client);
    if (text === null) {
        return await callback_query.edit_message_text(btn);
    }
    await callback_query.edit_message_text(text, { reply_markup: btn });
});