import { TelegramClient } from "teleproto";
import { command, ctx, is_bot_owner } from "../index";
import { Filters } from "../filters";
import { UserCancelledError, WaitTimeoutError, ValueError } from "../../types";

function _back_to_coupons_layout(client: TelegramClient): any[] {
    return [
        [
            {
                text: "• Kembali •",
                callback_data: "manage_coupons",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
}

export const manage_coupons_callback = command(
    (_c: any) => Filters.regex("^manage_coupons"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const text =
        `**${client.ns.emoji.ticket_admit} Manajemen Kupon**\n` +
        "Kelola kode diskon untuk VVIP Anda.";
    const layout = [
        [
            {
                text: "➕ Buat Kupon Baru",
                callback_data: "add_coupon",
                style: "green",
                emoji: client.ns.emoji.id("plus"),
            },
        ],
        [
            {
                text: "📋 Lihat Kupon",
                callback_data: "list_coupons_0",
                style: "blue",
                emoji: client.ns.emoji.id("open_book"),
            },
        ],
        [
            {
                text: "• Kembali •",
                callback_data: "settings",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    if (callback_query.message.photo) {
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else {
        await callback_query.edit_message_text(text, { reply_markup: btn });
    }
});

export const add_coupon_callback = command(
    (_c: any) => Filters.regex("^add_coupon"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const chat_id = callback_query.from_user.id;
    await callback_query.message.delete();

    try {
        const ask = (text: string): Promise<any> =>
            client.ask(
                chat_id,
                `${text}\n\nKetik \`/batal\` untuk membatalkan.`,
                600
            );

        const code_msg = await ask(
            `**1/4:** Masukkan kode kupon unik (misal: \`DISKONBARU\`).`
        );
        const code = String(code_msg.message || code_msg.text || "")
            .trim()
            .toUpperCase();

        const type_msg = await ask(
            "**2/4:** Pilih tipe diskon:\n1. Persentase (%)\n2. Potongan Harga Tetap"
        );
        const type_text = String(type_msg.message || type_msg.text || "");
        const discount_type = type_text.includes("1")
            ? "percentage"
            : "fixed";

        const value_prompt =
            discount_type === "percentage"
                ? "**3/4:** Masukkan nilai persentase."
                : "**3/4:** Masukkan jumlah potongan harga.";
        const discount_value_msg = await ask(value_prompt);
        const discount_value = Math.trunc(
            Number(String(discount_value_msg.message || discount_value_msg.text || ""))
        );

        const uses_left_msg = await ask(
            "**4/4:** Berapa kali kupon ini bisa digunakan?"
        );
        const uses_left = Math.trunc(
            Number(String(uses_left_msg.message || uses_left_msg.text || ""))
        );

        const expiry_days_msg = await ask(
            "**5/5:** Berapa hari kupon ini akan berlaku?"
        );
        const expiry_days = Math.trunc(
            Number(String(expiry_days_msg.message || expiry_days_msg.text || ""))
        );
        const expiry_date =
            expiry_days > 0
                ? new Date(Date.now() + expiry_days * 24 * 3600 * 1000).toISOString()
                : null;

        const coupon_data = {
            code,
            discount_type,
            discount_value,
            uses_left,
            expiry_date,
        };
        await ctx.db.setListVars(client.me.id, "coupons", coupon_data);

        await client.send_message(
            chat_id,
            `${client.ns.emoji.white_check_mark} Kupon \`${code}\` berhasil dibuat.`
        );
    } catch (e: any) {
        if (
            e instanceof UserCancelledError ||
            e instanceof WaitTimeoutError ||
            e instanceof ValueError
        ) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Proses Dibatalkan**`
            );
        } else {
            throw e;
        }
    }
});

function _format_expiry(coupon: any): string {
    if (coupon && coupon.expiry_date) {
        const d = new Date(coupon.expiry_date);
        return d.toLocaleDateString("en-GB", {
            day: "2-digit",
            month: "short",
            year: "numeric",
        });
    }
    return "Permanent";
}

export const list_coupons_callback = command(
    (_c: any) => Filters.regex("^list_coupons_(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const page = parseInt(callback_query.data_string.split("_")[2], 10);
    const coupons = (await ctx.db.getListVars(client.me.id, "coupons")) || [];
    const back_row = _back_to_coupons_layout(client)[0];

    if (!coupons.length) {
        const text = "Tidak ada kupon yang dibuat.";
        const btn = client.ns.telegram.button.build_button_grid([back_row]);
        await callback_query.edit_message_caption(text, { reply_markup: btn });
        return;
    }

    const total_pages = coupons.length;
    const safe_page = Math.max(0, Math.min(page, total_pages - 1));
    const coupon = coupons[safe_page];

    const text =
        `**${client.ns.emoji.pencil} Detail Kupon (${safe_page + 1}/${total_pages})**\n` +
        `- Kode: \`${coupon["code"]}\`\n` +
        `- Tipe: \`${coupon["discount_type"]}\`\n` +
        `- Nilai: \`${coupon["discount_value"]}\`\n` +
        `- Sisa Penggunaan: \`${coupon["uses_left"]}\`\n` +
        `- Berlaku hingga: \`${_format_expiry(coupon)}\``;

    const layout: any[] = [];
    const pagination_row: any[] = [];
    if (total_pages > 1) {
        const prev_page = (safe_page - 1 + total_pages) % total_pages;
        const next_page =
            safe_page + 1 < total_pages ? safe_page + 1 : safe_page;
        pagination_row.push(
            {
                text: "«",
                callback_data: `list_coupons_${prev_page}`,
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
            {
                text: "»",
                callback_data: `list_coupons_${next_page}`,
                style: "blue",
                emoji: client.ns.emoji.id("right_pointing"),
            }
        );
    }

    layout.push([
        {
            text: "🗑️ Hapus Kupon Ini",
            callback_data: `delete_coupon ${coupon["code"]} ${safe_page}`,
            style: "red",
            emoji: client.ns.emoji.id("minus"),
        },
    ]);
    if (pagination_row.length) {
        layout.push(pagination_row);
    }
    layout.push([back_row]);
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await callback_query.edit_message_caption(text, { reply_markup: btn });
});

export const delete_coupon_callback = command(
    (_c: any) => Filters.regex("^delete_coupon\\s(.+)\\s(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const parts = callback_query.data_string.split(/\s+/);
    const code = parts[1];
    const page_str = parts[2];
    const coupons = (await ctx.db.getListVars(client.me.id, "coupons")) || [];
    const coupon_to_remove = coupons.find((c: any) => c["code"] === code);
    if (coupon_to_remove) {
        await ctx.db.removeListVars(client.me.id, "coupons", coupon_to_remove);
        await callback_query.answer("Kupon berhasil dihapus.", { show_alert: true });
    }

    let new_page = parseInt(page_str, 10);
    const remaining_coupons =
        (await ctx.db.getListVars(client.me.id, "coupons")) || [];
    if (new_page >= remaining_coupons.length && remaining_coupons.length > 0) {
        new_page = remaining_coupons.length - 1;
    }

    callback_query.data_string = `list_coupons_${new_page}`;
    await list_coupons_callback(client, callback_query);
});