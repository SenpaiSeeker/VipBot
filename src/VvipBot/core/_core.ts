import { TelegramClient } from "teleproto";
import {
    command,
    ctx,
    is_bot_owner,
    check_new_user,
} from "../index";
import { Filters, and_ } from "../filters";
import { toId, dget } from "../../types";

type Any = any;

const DEFAULT_START_PHOTOS: Record<string, string> = {
    main: "https://files.catbox.moe/ozzvtz.jpg",
    donate: "https://files.catbox.moe/1f9j10.jpg",
};

const MAIN_BOT_TEXT =
    "{emoji} **Selamat Datang, {mention}!**\n\n" +
    "Saya adalah asisten utama untuk membuat dan mengelola " +
    " {gem} **Bot VVIP** Anda sendiri. " +
    "Jelajahi semua fitur yang tersedia melalui tombol di bawah ini.";

const SECONDARY_BOT_TEXT =
    "{emoji} **Selamat Datang, {mention}!**\n\n" +
    "Saya adalah asisten pribadi Anda untuk mengakses konten eksklusif. " +
    "Jelajahi semua fitur yang tersedia melalui tombol di bawah ini.";

function _get_back_button(client: TelegramClient): Any {
    return {
        text: "• Kembali ke Menu Utama •",
        callback_data: "start",
        style: "blue",
        emoji: client.ns.emoji.id("back_arrow"),
    };
}

async function _send_or_edit_photo(
    client: TelegramClient,
    callback_query: Any,
    text: string,
    btn: Any,
    photo_url?: string
): Promise<void> {
    const message = callback_query.message;
    if (message && message.photo) {
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else if (photo_url) {
        if (message) {
            try {
                await message.delete();
            } catch {
                // ignore
            }
        }
        await client.send_photo(callback_query.from_user.id, photo_url, {
            caption: text,
            reply_markup: btn,
        });
    } else {
        await callback_query.edit_message_text(text, { reply_markup: btn });
    }
}

async function get_start_keyboard_and_content(
    client: TelegramClient,
    user: Any
): Promise<[Any, string, string]> {
    const is_owner = await is_bot_owner(client, user.id);
    const is_main_bot = toId(client.me.id) === toId(ctx.manager.main_bot_id);

    let text_template = is_main_bot
        ? MAIN_BOT_TEXT
        : SECONDARY_BOT_TEXT;

    const db_text = await ctx.db.getVars(client.me.id, "start_text_template");
    if (db_text != null) {
        text_template = db_text;
    }

    const db_photo = await ctx.db.getVars(client.me.id, "start_photo_id");
    const photo_id =
        db_photo != null ? db_photo : DEFAULT_START_PHOTOS["main"];

    let welcome_text = text_template;
    if (is_main_bot) {
        welcome_text = welcome_text
            .split("{emoji}")
            .join(client.ns.emoji.waving)
            .split("{gem}")
            .join(client.ns.emoji.gem)
            .split("{mention}")
            .join(client.ns.telegram.arg.getMention(user));
    } else {
        welcome_text = welcome_text
            .split("{emoji}")
            .join(client.ns.emoji.waving)
            .split("{mention}")
            .join(client.ns.telegram.arg.getMention(user));
    }

    const layout: Any[] = [];
    if (is_main_bot) {
        layout.push([
            {
                text: "🤖 Buat Bot",
                callback_data: "create_bot",
                style: "green",
                emoji: client.ns.emoji.id("robot"),
            },
            {
                text: "📦 Bot Saya",
                callback_data: "list_my_bots_0",
                style: "blue",
                emoji: client.ns.emoji.id("folder"),
            },
        ]);
    }

    if (is_owner) {
        layout.push([
            {
                text: "⚙️ Panel Pengaturan ⚙️",
                callback_data: "settings",
                style: "blue",
                emoji: client.ns.emoji.id("toolbox"),
            },
        ]);
    }

    layout.push(
        [
            {
                text: "📚 Lihat Daftar VVIP 📚",
                callback_data: "list_vvip",
                style: "blue",
                emoji: client.ns.emoji.id("books"),
            },
        ],
        [
            {
                text: "ℹ️ About",
                callback_data: "about_bot",
                style: "blue",
                emoji: client.ns.emoji.id("open_book"),
            },
            {
                text: "Donasi ❤️",
                callback_data: "donate_stars",
                style: "green",
                emoji: client.ns.emoji.id("red_heart"),
            },
        ]
    );

    const btn = client.ns.telegram.button.build_button_grid(layout);
    return [btn, welcome_text, photo_id];
}

export const start_bot = command((_c: Any) =>
    and_(Filters.command("start"), Filters.private)
)(async (client: TelegramClient, message: Any) => {
    const [btn, txt, photo_id] = await get_start_keyboard_and_content(
        client,
        message.from_user
    );
    await message.reply_photo(photo_id, {
        caption: txt,
        reply_markup: btn,
    });
    await check_new_user(client, message);
});

export const start_callback = command(
    (_c: Any) => Filters.regex("^start$"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const [btn, txt, photo_id] = await get_start_keyboard_and_content(
        client,
        callback_query.from_user
    );
    const message = callback_query.message;
    if (message && message.photo) {
        await callback_query.edit_message_caption(txt, { reply_markup: btn });
    } else {
        if (message) {
            try {
                await message.delete();
            } catch {
                // ignore
            }
        }
        await client.send_photo(callback_query.from_user.id, photo_id, {
            caption: txt,
            reply_markup: btn,
        });
    }
});

export const about_bot_callback = command(
    (_c: Any) => Filters.regex("^about_bot$"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const text =
        `${client.ns.emoji.glowing_star} **Tentang Bot VVIP Ini**\n\n` +
        "Selamat datang! Saya adalah asisten otomatis yang dirancang untuk " +
        "memberikan Anda kemudahan dalam mengakses grup VVIP.\n\n" +
        `${client.ns.emoji.robot} **Fungsi Utama Saya:**\n` +
        "Saya menyediakan sistem pembayaran otomatis yang aman via QRIS, " +
        "memastikan Anda mendapatkan akses instan ke konten premium " +
        "setelah transaksi berhasil.\n\n" +
        `${client.ns.emoji.rocket} **Alur Penggunaan:**\n` +
        "1. **Pilih Paket:** Jelajahi daftar VVIP yang tersedia.\n" +
        "2. **Lakukan Pembayaran:** Scan QRIS yang saya berikan.\n" +
        "3. **Akses Instan:** Link undangan akan otomatis terkirim setelah " +
        "pembayaran terkonfirmasi.\n\n" +
        "Semua proses dirancang agar cepat, aman, dan tanpa perlu " +
        "menunggu konfirmasi manual!";
    const layout = [[_get_back_button(client)]];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    const message = callback_query.message;
    if (message && message.photo) {
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else {
        await callback_query.edit_message_text(text, { reply_markup: btn });
    }
});

export const close_panel_callback = command(
    (_c: Any) => Filters.regex("^close_panel$"),
    "callback"
)(async (_client: TelegramClient, callback_query: Any) => {
    try {
        await callback_query.message.delete();
    } catch {
        await callback_query.answer("Done.");
    }
});

export const list_vvip_bot = command(
    (_c: Any) => Filters.regex("^list_vvip$"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const vvip_list = (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    const layout: Any[] = [];
    if (!vvip_list.length) {
        const text = `${client.ns.emoji.card_index_dividers} Saat ini belum ada paket VVIP yang tersedia.`;
        layout.push([_get_back_button(client)]);
        const btn = client.ns.telegram.button.build_button_grid(layout);
        if (callback_query.message.photo) {
            return await callback_query.edit_message_caption(text, {
                reply_markup: btn,
            });
        }
        return await callback_query.edit_message_text(text, {
            reply_markup: btn,
        });
    }

    for (let index = 0; index < vvip_list.length; index++) {
        const item = vvip_list[index];
        const name = dget(item, "name", "N/A");
        const promo_price = dget(item, "promo_price", 0);
        const button_row: Any[] = [
            {
                text: `📂 ${name}`,
                callback_data: `notes_${index}`,
                style: "blue",
                emoji: client.ns.emoji.id("open_folder"),
            },
        ];
        if (promo_price > 0) {
            button_row.push({
                text: `🎉 Promo ${name}`,
                callback_data: `promo_detail_${index}`,
                style: "green",
                emoji: client.ns.emoji.id("party_popper"),
            });
        }
        layout.push(button_row);
    }

    layout.push([
        {
            text: "🛒 Ambil Semua VIP",
            callback_data: "pay_all_vvip",
            style: "green",
            emoji: client.ns.emoji.id("shopping_cart"),
        },
    ]);
    layout.push([_get_back_button(client)]);
    const btn = client.ns.telegram.button.build_button_grid(layout);
    const text =
        `${client.ns.emoji.books} **Daftar VVIP Bot: ${client.me.mention}**\n\n` +
        "Berikut adalah daftar paket eksklusif yang kami tawarkan. " +
        "Klik pada salah satu paket untuk melihat detail lengkap " +
        "dan penawaran spesial.";
    if (callback_query.message.photo) {
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else {
        await callback_query.edit_message_text(text, { reply_markup: btn });
    }
});

export const donate_callback = command(
    (_c: Any) => Filters.regex("^donate_stars$"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const photo_url = DEFAULT_START_PHOTOS["donate"];
    const text =
        `${client.ns.emoji.red_heart} **Dukung Kami dengan Telegram Stars!**\n\n` +
        "Donasi Anda sangat berarti untuk membantu kami terus mengembangkan " +
        "dan memelihara bot ini.\n\n" +
        "Setiap Star yang Anda berikan memberikan kami semangat untuk terus " +
        "berinovasi. Pilih jumlah donasi di bawah ini untuk memulai.\n\n" +
        "Terima kasih atas dukungan Anda!";
    const star_buttons: Any[][] = [
        [25, 50].map((amount) => ({
            text: `${amount} ⭐`,
            callback_data: `donate_pay_${amount}`,
            style: "blue",
            emoji: client.ns.emoji.id("star"),
        })),
        [75, 100].map((amount) => ({
            text: `${amount} ⭐`,
            callback_data: `donate_pay_${amount}`,
            style: "blue",
            emoji: client.ns.emoji.id("star"),
        })),
    ];
    star_buttons.push([_get_back_button(client)]);
    const btn = client.ns.telegram.button.build_button_grid(star_buttons);
    try {
        await _send_or_edit_photo(client, callback_query, text, btn, photo_url);
    } catch {
        try {
            await callback_query.message.delete();
        } catch {
            // ignore
        }
        await client.send_photo(callback_query.from_user.id, photo_url, {
            caption: text,
            reply_markup: btn,
        });
    }
});

export const process_donation_callback = command(
    (_c: Any) => Filters.regex("^donate_pay_(\\d+)$"),
    "callback"
)(async (_client: TelegramClient, callback_query: Any) => {
    let star_amount: number;
    try {
        star_amount = parseInt(
            callback_query.data_string.split("_")[2],
            10
        );
    } catch {
        return await callback_query.answer("Jumlah donasi tidak valid!", {
            show_alert: true,
        });
    }
    if (Number.isNaN(star_amount)) {
        return await callback_query.answer("Jumlah donasi tidak valid!", {
            show_alert: true,
        });
    }
    await callback_query.answer("Mempersiapkan invoice donasi...");
    const invoice = {
        title: "Donasi untuk Pengembangan Bot",
        description: `Dukungan Anda sebesar ${star_amount} Bintang (Stars) sangat kami hargai. Terima kasih!`,
        payload: `donation_${star_amount}_${toId(callback_query.from_user.id)}_${Math.floor(Date.now() / 1000)}`,
        currency: "XTR",
        prices: [{ label: `Donasi ${star_amount} Stars`, amount: star_amount }],
    };
    try {
        const client = callback_query._client as TelegramClient;
        await client.send_invoice(callback_query.from_user.id, invoice);
    } catch (e) {
        ctx.log.print(`Gagal mengirim invoice Stars: ${e}`);
        await callback_query.answer("Gagal membuat invoice donasi. Coba lagi nanti.", {
            show_alert: true,
        });
    }
});