import { TelegramClient } from "teleproto";
import { downloadMedia } from "teleproto/client/downloads";
import { command, ctx, is_bot_owner } from "../index";
import { Filters } from "../filters";
import { toId, WaitTimeoutError, UserCancelledError } from "../../types";
import fs from "fs";

type Any = any;

async function _reply_msg(client: Any, message: Any): Promise<Any | undefined> {
    const mid = message && message.replyToId;
    if (mid === undefined || mid === null) {
        return undefined;
    }
    let chat: Any = message.chatId;
    if (chat === undefined) {
        try {
            const entity = await client.getEntity(message.peerId);
            chat = entity && entity.id;
        } catch {
            return undefined;
        }
    }
    if (chat === undefined) {
        return undefined;
    }
    try {
        const msgs = await client.get_messages(chat, mid);
        return Array.isArray(msgs) ? msgs[0] : msgs;
    } catch {
        return undefined;
    }
}

async function send_star_gift_raw(
    client: TelegramClient,
    user_id: number,
    gift_id: number
): Promise<Any> {
    return await client.send_star_gift_raw(toId(user_id), Number(gift_id));
}

async function _require_owner(
    client: TelegramClient,
    callback_query: Any
): Promise<boolean> {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        await callback_query.answer("🚫 Anda tidak memiliki akses ke menu ini.", {
            show_alert: true,
        });
        return false;
    }
    return true;
}

function _sticker_emoji(doc: Any): string {
    if (!doc) {
        return "";
    }
    const attrs: Any[] = (doc.attributes || []).filter(Boolean);
    for (const a of attrs) {
        if (
            (a.className === "DocumentAttributeSticker" ||
                a._ === "DocumentAttributeSticker") &&
            a.alt
        ) {
            return String(a.alt);
        }
    }
    return "";
}

async function _send_gift_detail(
    client: TelegramClient,
    message: Any,
    gift: Any
): Promise<void> {
    const price = Number(gift.stars ?? gift.star_count ?? 0);
    let emoji = "❓️";
    if (gift.sticker) {
        const e = _sticker_emoji(gift.sticker);
        if (e) {
            emoji = `${e} `;
        }
    }

    const caption =
        `<b>${client.ns.emoji.gift} Info Hadiah</b>\n\n` +
        `<b>${client.ns.emoji.id_card} ID:</b> <code>${gift.id}</code>\n` +
        `<b>${client.ns.emoji.money_bag} Harga:</b> <code>${price} Stars</code>\n` +
        `<b>${client.ns.emoji.performing_arts} Emoji:</b> ${emoji}\n`;
    const buttons = [
        [
            {
                text: "🎁 Kirim ke Teman",
                callback_data: `gift_send_ask_${gift.id}`,
                style: "blue",
                emoji: client.ns.emoji.id("gift"),
            },
        ],
        [
            {
                text: "👤 Klaim Sendiri",
                callback_data: `gift_claim_self_${gift.id}`,
                style: "green",
                emoji: client.ns.emoji.id("bust_in_silhouette"),
            },
        ],
    ];
    const markup = client.ns.telegram.button.build_button_grid(buttons);

    const chat_id = message.chatId ?? message.chat?.id;
    let file_path: Any = undefined;
    try {
        if (
            gift.sticker &&
            gift.sticker.thumbs &&
            gift.sticker.thumbs.length
        ) {
            file_path = await downloadMedia(client, gift.sticker, undefined, undefined);
            if (file_path) {
                await client.send_photo(chat_id, file_path, {
                    caption: caption,
                    reply_markup: markup,
                });
                return;
            }
        }
        await client.send_message(chat_id, caption, { reply_markup: markup });
    } catch {
        try {
            await client.send_message(chat_id, caption, {
                reply_markup: markup,
            });
        } catch {
            // ignore send failures
        }
    } finally {
        if (file_path) {
            try {
                await new Promise<Any>((resolve) => {
                    if (typeof file_path === "string") {
                        fs.unlink(file_path, () => resolve(undefined));
                    } else {
                        resolve(undefined);
                    }
                });
            } catch {
                // ignore cleanup failures
            }
        }
    }
}

export const send_gift_handler = command(
    (_c: any) => Filters.command("gift") && Filters.private,
    "message"
)(async (client: TelegramClient, message: Any) => {
    if (!(await is_bot_owner(client, message.from_user.id))) {
        return;
    }
    try {
        let user_id_target: Any = undefined;
        let gift_id_arg: Any = undefined;
        if (message.replyToId) {
            const reply = await _reply_msg(client, message);
            const rid = reply && (reply.senderId ?? reply.from_user?.id);
            if (rid) {
                user_id_target = rid;
            }
            if (message.command.length > 1) {
                gift_id_arg = message.command[1];
            }
        } else if (message.command.length > 2) {
            try {
                const users = await client.get_users(message.command[1]);
                const user = Array.isArray(users) ? users[0] : users;
                if (user) {
                    user_id_target = user.id;
                    gift_id_arg = message.command[2];
                }
            } catch {
                // ignore parse errors
            }
        }

        if (!user_id_target) {
            return await message.reply_text(
                `${client.ns.emoji.cross_mark} **Target tidak ditemukan.**\n` +
                    "Balas pesan pengguna atau gunakan format:\n" +
                    "`/gift [username] [gift_id]`"
            );
        }
        if (!gift_id_arg || !/^\d+$/.test(String(gift_id_arg))) {
            return await message.reply_text(
                `${client.ns.emoji.cross_mark} **ID Hadiah tidak valid.**\n` +
                    "Gunakan `/listgift` untuk melihat ID."
            );
        }

        const gift_id = Math.trunc(Number(gift_id_arg));
        const status_msg = await message.reply_text(
            `${client.ns.emoji.repeat} Memproses pengiriman hadiah...`
        );
        const available_gifts = await client.get_available_gifts();
        let target_gift: Any = undefined;
        for (const g of available_gifts) {
            if (Number(g.id) === gift_id) {
                target_gift = g;
                break;
            }
        }
        if (!target_gift) {
            return await status_msg.edit(
                `${client.ns.emoji.cross_mark} Gift ID \`${gift_id}\` tidak ditemukan atau tidak tersedia.`
            );
        }

        const users = await client.get_users(user_id_target);
        const target_user = Array.isArray(users) ? users[0] : users;
        const mention = client.ns.telegram.arg.getMention(target_user);
        await status_msg.edit(
            `${client.ns.emoji.gift} Mengirim hadiah **Star** (ID: \`${gift_id}\`) ke **${mention}**...`
        );
        await send_star_gift_raw(client, Number(target_user.id), gift_id);
        await status_msg.edit(
            `${client.ns.emoji.white_check_mark} Berhasil mengirim hadiah ke **${mention}**!`
        );
    } catch (e: Any) {
        await message.reply_text(
            `${client.ns.emoji.cross_mark} Gagal mengirim hadiah: \`${e}\``
        );
    }
});

export const list_gift_handler = command(
    (_c: any) => Filters.command("listgift") && Filters.private,
    "message"
)(async (client: TelegramClient, message: Any) => {
    if (!(await is_bot_owner(client, message.from_user.id))) {
        return;
    }
    const status_msg = await message.reply_text(
        `${client.ns.emoji.repeat} Mengambil daftar hadiah...`
    );
    try {
        const gifts = await client.get_available_gifts();
        if (!gifts || !gifts.length) {
            return await status_msg.edit(
                `${client.ns.emoji.exclamation} Tidak ada hadiah yang tersedia saat ini.`
            );
        }
        for (const gift of gifts) {
            if (!gift.soldOut) {
                await _send_gift_detail(client, message, gift);
                await new Promise((r) => setTimeout(r, 1500));
            }
        }
        await status_msg.delete();
    } catch (e: Any) {
        await status_msg.edit(
            `${client.ns.emoji.cross_mark} Gagal mengirim hadiah: \`${e}\``
        );
    }
});

export const claim_self_gift_callback = command(
    (_c: any) => Filters.regex(/^gift_claim_self_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (!(await _require_owner(client, callback_query))) {
        return;
    }
    const gift_id = Math.trunc(Number(callback_query.data.split("_")[3]));
    const user_id = callback_query.from_user.id;
    try {
        await callback_query.edit_message_reply_markup(undefined);
        await send_star_gift_raw(client, Number(user_id), gift_id);
        await callback_query.edit_message_caption(
            `${client.ns.emoji.white_check_mark} Berhasil mengklaim hadiah (ID: ${gift_id}) untuk diri sendiri!`
        );
    } catch (e: Any) {
        await callback_query.answer(`❌ Gagal klaim: ${e}`, {
            show_alert: true,
        });
    }
});

export const ask_send_gift_callback = command(
    (_c: any) => Filters.regex(/^gift_send_ask_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: Any) => {
    if (!(await _require_owner(client, callback_query))) {
        return;
    }
    const gift_id = Math.trunc(Number(callback_query.data.split("_")[3]));
    const chat_id = callback_query.message.chatId ?? callback_query.message.chat?.id;
    try {
        await callback_query.edit_message_reply_markup(undefined);
        const prompt =
            `**${client.ns.emoji.bust_in_silhouette} Kirim Hadiah**\n\n` +
            "Silakan kirim **User ID** atau **Username** (@username) tujuan penerima hadiah.\n\n" +
            "Ketik `/batal` untuk membatalkan.";
        const ask_msg = await client.ask(chat_id, prompt, 60);
        if (String(ask_msg.message || "").trim().toLowerCase() === "/batal") {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} Pengiriman dibatalkan.`
            );
            return;
        }
        const target_input = String(ask_msg.message || "").trim();
        const processing_msg = await client.send_message(
            chat_id,
            `${client.ns.emoji.repeat} Mencari pengguna \`${target_input}\`...`
        );
        let target_user: Any;
        try {
            const users = await client.get_users(target_input);
            target_user = Array.isArray(users) ? users[0] : users;
        } catch {
            await processing_msg.edit(
                `${client.ns.emoji.cross_mark} Pengguna tidak ditemukan. Pastikan username/ID benar.`
            );
            return;
        }
        await processing_msg.edit(
            `${client.ns.emoji.gift} Mengirim hadiah **Star** (ID: \`${gift_id}\`) ke **${target_user.firstName}**...`
        );
        await send_star_gift_raw(client, Number(target_user.id), gift_id);
        await processing_msg.edit(
            `${client.ns.emoji.white_check_mark} Berhasil mengirim hadiah ke **${target_user.firstName}**!`
        );
    } catch (e: Any) {
        if (e instanceof WaitTimeoutError) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.alarm_clock} Waktu habis. Silakan ulangi proses.`
            );
        } else if (e instanceof UserCancelledError) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} Pengiriman dibatalkan.`
            );
        } else {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} Gagal mengirim hadiah: \`${e}\``
            );
        }
    }
});