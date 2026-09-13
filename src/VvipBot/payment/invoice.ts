import { TelegramClient } from "teleproto";
import { ctx, is_bot_owner } from "../index";
import { generate_safe_saweria_message } from "../../helpers/saweriaMessageGenerator";
import { dget, titleCase } from "../../types";

type Any = any;

async function _ensure_saweria_available(
    client: TelegramClient,
    user: Any
): Promise<boolean> {
    const saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID");
    if (saweria_user_id) {
        return true;
    }
    if (await is_bot_owner(client, user.id)) {
        const text =
            `${client.ns.emoji.exclamation} **Layanan Pembayaran Tidak Aktif**\n\n` +
            "Silakan atur API Key untuk payment gateway terlebih dahulu.";
        const layout = [
            [
                {
                    text: "⚙️ Atur Kunci API",
                    callback_data: "api_settings",
                    style: "blue",
                    emoji: client.ns.emoji.id("toolbox"),
                },
            ],
        ];
        const btn = client.ns.telegram.button.build_button_grid(layout);
        await client.send_message(user.id, text, { reply_markup: btn });
    } else {
        await client.send_message(
            user.id,
            "Maaf, layanan pembayaran saat ini tidak tersedia."
        );
    }
    return false;
}

async function _build_payment(
    client: TelegramClient,
    user: Any,
    amount: number,
    product_line: string
): Promise<[string, Any, Any, string, Any]> {
    const fakeinfo = client.ns.utils.faker.generate();
    const random_message = generate_safe_saweria_message(fakeinfo.name);
    const saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID");

    const payment = await client.services.saweria.create_payment(
        saweria_user_id,
        Math.trunc(Number(amount)),
        fakeinfo.name,
        fakeinfo.email,
        random_message,
        client.me.username
    );
    const qr_string: string = payment.qr_string;
    const transaction_id: string = payment.id;
    const qr_image_stream: Any = payment.image?.buffer;
    const amount_raw: number = payment.amount_raw;

    const formatted_amount = Math.trunc(Number(amount_raw)).toLocaleString("id-ID");
    const caption =
        `**${client.ns.emoji.white_check_mark} Pembayaran Siap Dilakukan!**\n\n` +
        "Silakan scan QRIS di atas untuk membayar. Setelah itu, " +
        "tekan tombol **Konfirmasi Pembayaran**.\n\n" +
        "╭─ **Detail Tagihan**\n" +
        "│\n" +
        `├─ ${client.ns.emoji.shopping_bags} **Produk:** ${product_line}\n` +
        `├─ ${client.ns.emoji.gem} **Jumlah:** \`Rp ${formatted_amount}\`\n` +
        `├─ ${client.ns.emoji.id_card} **Order ID:** [${transaction_id}](https://saweria.co/qris/${transaction_id})\n` +
        "│\n" +
        `╰─ ${client.ns.emoji.down_pointing} **Jika sudah membayar, silakan klik tombol di bawah ini.**\n`;
    const layout = [
        [
            {
                text: "✅ Konfirmasi Pembayaran",
                callback_data: `confirm_payment ${transaction_id}`,
                style: "green",
                emoji: client.ns.emoji.id("white_check_mark"),
            },
        ],
    ];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    return [transaction_id, amount_raw, qr_image_stream, caption, btn];
}

async function _create_payment_invoice(
    client: TelegramClient,
    user: Any,
    item_index: number,
    tipe: string,
    amount: number,
    coupon_code: string | null = null
): Promise<void> {
    const vvip_list = (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    let item: Any;
    try {
        item = vvip_list[item_index];
    } catch {
        return await client.send_message(
            user.id,
            `${client.ns.emoji.cross_mark} Paket VVIP tidak ditemukan.`
        );
    }
    if (!item) {
        return await client.send_message(
            user.id,
            `${client.ns.emoji.cross_mark} Paket VVIP tidak ditemukan.`
        );
    }
    const names = dget(item, "name");

    if (!(await _ensure_saweria_available(client, user))) {
        return;
    }

    const msg = await client.send_message(
        user.id,
        `${client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.`
    );
    try {
        const [transaction_id, amount_raw, qr_image_stream, caption, btn] =
            await _build_payment(client, user, amount, `${names} (${titleCase(tipe)})`);
        let order_data = `${item_index}|${tipe}|${amount_raw}`;
        if (coupon_code) {
            order_data += `|${coupon_code}`;
        }
        await ctx.db.setVars(client.me.id, transaction_id, order_data);

        await client.send_photo(user.id, qr_image_stream, {
            caption,
            reply_markup: btn,
        });
        await msg.delete();
    } catch (e: any) {
        await msg.edit(
            `${client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>${e}</pre>`
        );
    }
}

async function _create_all_vvip_payment_invoice(
    client: TelegramClient,
    user: Any,
    selected_items: Any[],
    total_amount: number
): Promise<void> {
    if (!(await _ensure_saweria_available(client, user))) {
        return;
    }

    const msg = await client.send_message(
        user.id,
        `${client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.`
    );
    try {
        const total_len = selected_items.length;
        const [transaction_id, amount_raw, qr_image_stream, caption, btn] =
            await _build_payment(
                client,
                user,
                total_amount,
                `Semua VIP (${total_len} paket)`
            );
        const package_indexes = selected_items
            .map((item) => String(dget(item, "index")))
            .join(",");
        const order_data = `ALL|normal|${Math.trunc(Number(amount_raw))}|${package_indexes}`;
        await ctx.db.setVars(client.me.id, transaction_id, order_data);

        await client.send_photo(user.id, qr_image_stream, {
            caption,
            reply_markup: btn,
        });
        await msg.delete();
    } catch (e: any) {
        await msg.edit(
            `${client.ns.emoji.cross_mark} **Terjadi Kesalahan**\n<pre>${e}</pre>`
        );
    }
}

export { _ensure_saweria_available, _build_payment, _create_payment_invoice, _create_all_vvip_payment_invoice };