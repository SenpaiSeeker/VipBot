import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { _create_all_vvip_payment_invoice, _create_payment_invoice } from "./invoice";
import { _get_all_vvip_items } from "./verifier";
import { dget } from "../../types";
import { UserCancelledError, WaitTimeoutError, ValueError } from "../../types";

type Any = any;

async function _reply_caption_or_text(
    callback_query: Any,
    text: string,
    btn: Any
): Promise<Any> {
    if (callback_query.message && callback_query.message.photo) {
        return await callback_query.edit_message_caption(text, { reply_markup: btn });
    }
    return await callback_query.edit_message_text(text, { reply_markup: btn });
}

function _resolve_item_index(callback_query: Any, item_id: string): number | Any | null {
    if (/^\d+$/.test(item_id)) {
        return parseInt(item_id, 10);
    }
    if (!ctx.vip_list || !(item_id in ctx.vip_list)) {
        return null;
    }
    return ctx.vip_list[item_id];
}

function _build_back_row(client: TelegramClient): Any[] {
    return [
        {
            text: "• Kembali ke Daftar VVIP •",
            callback_data: "list_vvip",
            style: "blue",
            emoji: client.ns.emoji.id("back_arrow"),
        },
    ];
}

export const pay_all_vvip_callback = command(
    (_c: Any) => Filters.regex("^pay_all_vvip$"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const vvip_list =
        (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    const selected_items = _get_all_vvip_items(vvip_list);
    if (!selected_items.length) {
        return await callback_query.answer(
            "❌ Tidak ada paket VIP valid untuk pembelian semua VIP.",
            { show_alert: true }
        );
    }

    if (callback_query.message && callback_query.message.photo) {
        await callback_query.message.delete();
    } else {
        await callback_query.edit_message_text(
            `${client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.`
        );
    }

    const total_amount = selected_items.reduce(
        (acc: number, item: Any) => acc + dget(item, "price", 0),
        0
    );
    await _create_all_vvip_payment_invoice(
        client,
        callback_query.from_user,
        selected_items,
        total_amount
    );
});

export const notes_data = command(
    (_c: Any) => Filters.regex("^notes_(.+)"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const item_id = callback_query.matches[0].group(1);
    const item_index = _resolve_item_index(callback_query, item_id);
    if (item_index === null || item_index === undefined) {
        return await callback_query.answer(
            "Sesi kedaluwarsa, silakan muat ulang menu.",
            { show_alert: true }
        );
    }

    const vvip_list =
        (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    const back_row = _build_back_row(client);
    let item: Any;
    try {
        item = vvip_list[item_index as number];
    } catch {
        item = null;
    }

    if (item) {
        const name = dget(item, "name");
        const price_val = dget(item, "price", 0);
        const normal_text = dget(item, "normal_text", "");
        const formatted_price = Number(price_val).toLocaleString("id-ID");

        let desc: string;
        if (normal_text) {
            desc = normal_text
                .split("{name}")
                .join(name)
                .split("{price}")
                .join(formatted_price);
        } else {
            desc =
                `╭─ **${client.ns.emoji.sparkles} Detail Paket VVIP**\n` +
                "│\n" +
                `├─ ${client.ns.emoji.open_folder} **Nama Paket:** \`${name}\`\n` +
                `├─ ${client.ns.emoji.pencil} **Deskripsi:** Dapatkan akses instan ke konten premium dan eksklusif setelah pembayaran berhasil.\n` +
                "│\n" +
                `├─ ${client.ns.emoji.gem} **Harga Normal:** \`Rp ${formatted_price}\`\n` +
                "│\n" +
                "╰─ Silakan klik tombol 'Bayar' di bawah untuk melanjutkan!\n";
        }
        const layout = [
            [
                {
                    text: "💸 Bayar Harga Normal",
                    callback_data: `paynow_${item_index}_normal_${price_val}`,
                    style: "green",
                    emoji: client.ns.emoji.id("gem"),
                },
            ],
            [
                {
                    text: "🎟️ Gunakan Kupon",
                    callback_data: `apply_coupon_${item_index}_normal_${price_val}`,
                    style: "blue",
                    emoji: client.ns.emoji.id("ticket_admit"),
                },
                back_row[0],
            ],
        ];
        const btn = client.ns.telegram.button.build_button_grid(layout);
        return await _reply_caption_or_text(callback_query, desc, btn);
    }

    const text = `${client.ns.emoji.cross_mark} Paket VVIP tidak ditemukan.`;
    const btn = client.ns.telegram.button.build_button_grid([back_row]);
    await _reply_caption_or_text(callback_query, text, btn);
});

export const promo_detail = command(
    (_c: Any) => Filters.regex("^promo_detail_(.+)"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const item_id = callback_query.matches[0].group(1);
    const item_index = _resolve_item_index(callback_query, item_id);
    if (item_index === null || item_index === undefined) {
        return await callback_query.answer(
            "Sesi kedaluwarsa, silakan muat ulang menu.",
            { show_alert: true }
        );
    }

    const vvip_list =
        (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    const back_row = _build_back_row(client);
    let item: Any;
    try {
        item = vvip_list[item_index as number];
    } catch {
        item = null;
    }

    if (item && dget(item, "promo_price", 0) > 0) {
        const name = dget(item, "name");
        const promo_price_val = dget(item, "promo_price", 0);
        const promo_text = dget(item, "promo_text", "");
        const formatted_promo = Number(promo_price_val).toLocaleString("id-ID");

        let desc: string;
        if (promo_text) {
            desc = promo_text
                .split("{name}")
                .join(name)
                .split("{promo_price}")
                .join(formatted_promo);
        } else {
            desc =
                `╭─ **${client.ns.emoji.party_popper} Penawaran Spesial Terbatas!**\n` +
                "│\n" +
                `├─ ${client.ns.emoji.open_folder} **Nama Paket:** \`${name}\`\n` +
                `├─ ${client.ns.emoji.pencil} **Deskripsi:** Jangan lewatkan kesempatan emas ini untuk bergabung dengan harga yang jauh lebih terjangkau!\n` +
                "│\n" +
                `├─ ${client.ns.emoji.money_bag} **Harga Promo:** \`Rp ${formatted_promo}\`\n` +
                "│\n" +
                "╰─ Segera amankan slot Anda sebelum promo berakhir!\n";
        }
        const layout = [
            [
                {
                    text: "✅ Bayar Harga Promo",
                    callback_data: `paynow_${item_index}_promo_${promo_price_val}`,
                    style: "green",
                    emoji: client.ns.emoji.id("white_check_mark"),
                },
            ],
            [
                {
                    text: "🎟️ Gunakan Kupon",
                    callback_data: `apply_coupon_${item_index}_promo_${promo_price_val}`,
                    style: "blue",
                    emoji: client.ns.emoji.id("ticket_admit"),
                },
                back_row[0],
            ],
        ];
        const btn = client.ns.telegram.button.build_button_grid(layout);
        return await _reply_caption_or_text(callback_query, desc, btn);
    }

    const text =
        `${client.ns.emoji.cross_mark} Paket promo tidak ditemukan atau tidak aktif.`;
    const btn = client.ns.telegram.button.build_button_grid([back_row]);
    await _reply_caption_or_text(callback_query, text, btn);
});

export const apply_coupon_callback = command(
    (_c: Any) => Filters.regex("^apply_coupon_(\\d+)_(normal|promo)_(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const chat_id = callback_query.from_user.id;
    const match = callback_query.matches[0];
    const item_index = parseInt(match.group(1), 10);
    const tipe = match.group(2);
    const original_amount = parseInt(match.group(3), 10);
    await callback_query.message.delete();

    try {
        const ask_msg = await client.ask(
            chat_id,
            "Silakan masukkan kode kupon Anda.\n\nKetik `/batal` untuk membatalkan.",
            300
        );
        if ((ask_msg.message || ask_msg.text || "").toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        const coupon_code = (ask_msg.message || ask_msg.text || "").toUpperCase();

        const coupons = (await ctx.db.getListVars(client.me.id, "coupons")) || [];
        const coupon = coupons.find((c: Any) => dget(c, "code") === coupon_code);
        if (!coupon) {
            throw new ValueError(
                `${client.ns.emoji.cross_mark} Kode kupon tidak valid.`
            );
        }
        if (dget(coupon, "uses_left", 1) <= 0) {
            throw new ValueError(
                `${client.ns.emoji.cross_mark} Kupon ini sudah habis digunakan.`
            );
        }
        const expiry_str = dget(coupon, "expiry_date");
        if (expiry_str && new Date(expiry_str).getTime() < Date.now()) {
            throw new ValueError(
                `${client.ns.emoji.cross_mark} Kupon ini sudah kedaluwarsa.`
            );
        }

        const discount_type = dget(coupon, "discount_type");
        const discount_value = dget(coupon, "discount_value");
        let final_amount: number;
        if (discount_type === "percentage") {
            final_amount =
                original_amount - original_amount * (discount_value / 100);
        } else {
            final_amount = original_amount - discount_value;
        }
        final_amount = Math.max(1000, Math.trunc(final_amount));

        await client.send_message(
            chat_id,
            `${client.ns.emoji.white_check_mark} Kupon \`${coupon_code}\` berhasil digunakan! Harga awal \`Rp ${original_amount.toLocaleString("id-ID")}\` menjadi \`Rp ${final_amount.toLocaleString("id-ID")}\`.`
        );
        await _create_payment_invoice(
            client,
            callback_query.from_user,
            item_index,
            tipe,
            final_amount,
            coupon_code
        );
    } catch (e: any) {
        if (e instanceof UserCancelledError) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Proses Dibatalkan**`
            );
        } else if (e instanceof WaitTimeoutError) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.alarm_clock} **Waktu Habis**\nProses telah dibatalkan otomatis.`
            );
        } else if (e instanceof ValueError) {
            await client.send_message(chat_id, e.message);
        } else {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>${e}</pre>`
            );
        }
    }
});

export const paynow = command(
    (_c: Any) => Filters.regex("^paynow_(\\d+)_(normal|promo)_(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const match = callback_query.matches[0];
    const item_index = parseInt(match.group(1), 10);
    const tipe = match.group(2);
    const amount = parseInt(match.group(3), 10);

    if (callback_query.message && callback_query.message.photo) {
        await callback_query.message.delete();
    } else {
        await callback_query.edit_message_text(
            `${client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.`
        );
    }
    await _create_payment_invoice(client, callback_query.from_user, item_index, tipe, amount);
});

export const renew_subscription_callback = command(
    (_c: Any) => Filters.regex("^renew_sub_(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const item_index = parseInt(callback_query.matches[0].group(1), 10);
    const vvip_list =
        (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    let item: Any;
    try {
        item = vvip_list[item_index];
    } catch {
        return await callback_query.answer("❌ Paket VVIP tidak ditemukan.", {
            show_alert: true,
        });
    }
    if (!item) {
        return await callback_query.answer("❌ Paket VVIP tidak ditemukan.", {
            show_alert: true,
        });
    }

    if (dget(item, "promo_price", 0) > 0) {
        callback_query.data = `promo_detail_${item_index}`;
        callback_query.matches = [
            {
                group: (n: number) =>
                    n === 1 ? String(item_index) : undefined,
            },
        ];
        await promo_detail(client, callback_query);
    } else {
        callback_query.data = `notes_${item_index}`;
        callback_query.matches = [
            {
                group: (n: number) =>
                    n === 1 ? String(item_index) : undefined,
            },
        ];
        await notes_data(client, callback_query);
    }
});