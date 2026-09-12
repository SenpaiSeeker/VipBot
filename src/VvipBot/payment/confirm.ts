import { TelegramClient } from "teleproto";
import { command, ctx, get_notification_target, is_bot_owner } from "../index";
import { Filters } from "../filters";
import { verify_user_join, verify_user_join_multiple } from "./verifier";
import { dget, toId, titleCase } from "../../types";

type Any = any;

export const INVITE_LINK_MINUTES = 60;
export const INVITE_MEMBER_LIMIT = 1;

async function _create_one_time_invite(
    client: TelegramClient,
    target_chat_id: Any
): Promise<string> {
    const expire_date_link = Date.now() + INVITE_LINK_MINUTES * 60 * 1000;
    const invite_link_obj = await client.create_chat_invite_link(
        target_chat_id,
        {
            member_limit: INVITE_MEMBER_LIMIT,
            expire_date: expire_date_link,
        }
    );
    return invite_link_obj.invite_link;
}

function _build_member_data(
    user: Any,
    name: string,
    tipe: string,
    target_chat_id: Any,
    item_found: Any
): Any {
    const member_data: Any = {
        user_id: toId(user.id),
        vvip_name: name,
        join_date: new Date().toISOString(),
        payment_type: tipe,
        chat_id_kick: target_chat_id,
    };
    const duration = dget(item_found, "duration", 0);
    if (duration > 0) {
        const expiry_date = new Date(Date.now() + duration * 24 * 3600 * 1000);
        member_data.expiry_date = expiry_date.toISOString();
    }
    return member_data;
}

async function _record_revenue(
    client: TelegramClient,
    user: Any,
    amount_raw: number,
    item_name: string,
    tipe: string
): Promise<void> {
    const revenue_data = {
        user_id: toId(user.id),
        username: user.username || user.firstName,
        amount: amount_raw,
        date: new Date().toISOString(),
        item_name,
        type: tipe,
    };
    await ctx.db.setListVars(client.me.id, "vip_revenue_history", revenue_data);
}

async function _notify_new_income(
    client: TelegramClient,
    user: Any,
    item_label: string
): Promise<void> {
    const owner_bot_id = await get_notification_target(client);
    const user_mention_str = client.ns.telegram.arg.getMention(user);
    const bot_mention_str = client.me.mention;
    await client.send_message(
        owner_bot_id,
        `${client.ns.emoji.money_bag} **Pemasukan Baru!**\n\n` +
            `**Pengguna:** ${user_mention_str}\n` +
            `**Bot:** ${bot_mention_str}\n` +
            `**Kategori:** \`${item_label}\``
    );
}

async function _consume_coupons(
    client: TelegramClient,
    coupon_code: string
): Promise<void> {
    let coupons = (await ctx.db.getListVars(client.me.id, "coupons")) || [];
    coupons = coupons.slice();
    for (const c of coupons) {
        if (dget(c, "code") === coupon_code) {
            c.uses_left = dget(c, "uses_left", 1) - 1;
            break;
        }
    }
    await ctx.db.removeVars(client.me.id, "coupons");
    for (const c of coupons) {
        await ctx.db.setListVars(client.me.id, "coupons", c);
    }
}

function _parse_ref(
    transaction_id: string,
    ref_data_str: string
): [
    boolean,
    string,
    number,
    string | null,
    number[],
    number | null
] {
    const ref_parts = ref_data_str.split("|");
    const is_bundle_order = ref_parts[0] === "ALL";
    const tipe = ref_parts[1];
    const amount_raw = Number(ref_parts[2]);
    let coupon_code: string | null = null;
    let bundle_indexes: number[] = [];
    let item_index: number | null = null;
    if (is_bundle_order) {
        bundle_indexes =
            ref_parts.length > 3
                ? ref_parts[3]
                      .split(",")
                      .map((i) => parseInt(i.trim(), 10))
                      .filter((i) => !Number.isNaN(i))
                : [];
    } else {
        item_index = parseInt(ref_parts[0], 10);
        coupon_code = ref_parts.length > 3 ? ref_parts[3] : null;
    }
    return [is_bundle_order, tipe, amount_raw, coupon_code, bundle_indexes, item_index];
}

export const manual_check_payment_callback = command(
    (_c: Any) => Filters.regex("^confirm_payment\\s(.+)"),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    const transaction_id = callback_query.data_string.split(" ", 2)[1];
    const user = callback_query.from_user || callback_query._vvipFromUser;
    const ref_data_str = await ctx.db.getVars(client.me.id, transaction_id);

    if (!ref_data_str) {
        return await callback_query.answer(
            "⚠️ Invoice ini sudah tidak valid atau telah selesai.",
            { show_alert: true }
        );
    }

    const [is_bundle_order, tipe, amount_raw, coupon_code, bundle_indexes, item_index] =
        _parse_ref(transaction_id, ref_data_str);

    try {
        const is_owner_confirm = await is_bot_owner(client, user.id);
        const is_paid =
            is_owner_confirm ||
            (await client.services.saweria.check_paid_status(transaction_id));

        if (is_paid) {
            await callback_query.edit_message_reply_markup(undefined);
            await ctx.db.removeVars(client.me.id, transaction_id);
            const vvip_list =
                (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];

            if (is_bundle_order) {
                const invite_payloads: Any[] = [];
                const purchased_names: string[] = [];
                for (const idx of bundle_indexes) {
                    let item_found: Any;
                    try {
                        item_found = vvip_list[idx];
                    } catch {
                        continue;
                    }
                    if (!item_found) {
                        continue;
                    }
                    const name = dget(item_found, "name");
                    const target_chat_id = dget(item_found, "chat_id_normal");
                    if (!target_chat_id) {
                        continue;
                    }
                    let link: string;
                    try {
                        link = await _create_one_time_invite(client, target_chat_id);
                    } catch (e) {
                        ctx.log.print(
                            `Gagal membuat invite link bundle untuk ${target_chat_id}: ${e}`
                        );
                        continue;
                    }

                    const member_data = _build_member_data(
                        user,
                        name,
                        "normal",
                        target_chat_id,
                        item_found
                    );
                    await ctx.db.setListVars(client.me.id, "vvip_members", member_data);
                    purchased_names.push(name);
                    invite_payloads.push({
                        name,
                        chat_id: target_chat_id,
                        link,
                    });
                }

                if (!invite_payloads.length) {
                    throw new Error("Tidak ada paket VIP valid untuk pembelian semua VIP.");
                }

                const item_label = purchased_names.join(" + ");
                await _record_revenue(client, user, amount_raw, item_label, "bundle");

                const link_text = invite_payloads
                    .map((item) => `• ${item.name}: ${item.link}`)
                    .join("\n");
                const link_msg = await client.send_message(
                    user.id,
                    `${client.ns.emoji.party_popper} **Pembayaran Paket Semua VIP Berhasil!**\n\n` +
                        `Berikut semua link akses VIP Anda:\n\n${link_text}\n\n` +
                        `${client.ns.emoji.exclamation} Setiap link hanya berlaku 1 kali klik dan kedaluwarsa dalam ${INVITE_LINK_MINUTES} menit.\n`,
                    { protect_content: true }
                );
                await callback_query.message.delete();
                void verify_user_join_multiple(client, user, invite_payloads, link_msg);
                await _notify_new_income(client, user, "Semua VIP (Bundle)");
                return;
            }

            let item_found: Any;
            try {
                item_found = vvip_list[item_index as number];
            } catch {
                throw new Error("Kategori VVIP tidak ditemukan di database.");
            }
            if (!item_found) {
                throw new Error("Kategori VVIP tidak ditemukan di database.");
            }
            const name = dget(item_found, "name");

            const is_promo = tipe === "promo";
            const target_chat_id = is_promo
                ? dget(item_found, "chat_id_promo")
                : dget(item_found, "chat_id_normal");
            if (!target_chat_id) {
                throw new Error(
                    "Chat ID untuk paket VVIP ini belum diatur oleh admin."
                );
            }

            let link: string;
            try {
                link = await _create_one_time_invite(client, target_chat_id);
            } catch (e) {
                ctx.log.print(`Gagal membuat invite link untuk ${target_chat_id}: ${e}`);
                throw new Error("Gagal membuat link undangan.");
            }

            const member_data = _build_member_data(
                user,
                name,
                tipe,
                target_chat_id,
                item_found
            );
            if (coupon_code) {
                await _consume_coupons(client, coupon_code);
            }
            await ctx.db.setListVars(client.me.id, "vvip_members", member_data);
            await _record_revenue(client, user, amount_raw, name, tipe);

            const link_msg = await client.send_message(
                user.id,
                `${client.ns.emoji.party_popper} **Pembayaran Dikonfirmasi!**\n\n` +
                    `Terima kasih, berikut adalah link akses Anda untuk paket **${name}**:\n\n${link}\n\n` +
                    `${client.ns.emoji.exclamation} Link ini hanya berlaku untuk 1 kali klik dan akan kedaluwarsa dalam ${INVITE_LINK_MINUTES} menit jika tidak digunakan.\n`,
                { protect_content: true }
            );
            await callback_query.message.delete();
            void verify_user_join(client, user, target_chat_id, link_msg);
            await _notify_new_income(client, user, `${name} (${titleCase(tipe)})`);
        } else {
            await callback_query.answer(
                "❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah beberapa saat.",
                { show_alert: true }
            );
        }
    } catch (e: any) {
        await callback_query.answer(`**Terjadi Kesalahan**\n${e}`, {
            show_alert: true,
        });
    }
});

export const pre_checkout_handler = command(
    (_c: Any) => Filters.PreCheckoutQuery as any,
    "pre_checkout"
)(async (_client: TelegramClient, pre_checkout_query: Any) => {
    await pre_checkout_query.answer(true);
});