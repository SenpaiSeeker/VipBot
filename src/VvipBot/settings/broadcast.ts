import { TelegramClient } from "teleproto";
import { command, ctx, is_bot_owner } from "../index";
import { Filters } from "../filters";
import { UserCancelledError, WaitTimeoutError, ValueError } from "../../types";

function _back_to_settings_layout(client: TelegramClient): any[] {
    return [
        [
            {
                text: "• Kembali ke Pengaturan •",
                callback_data: "settings",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
}

export const set_broadcast_price_callback = command(
    (_c: any) => Filters.regex("^set_broadcast_price$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const chat_id = callback_query.from_user.id;
    await callback_query.message.delete();
    const back_btn = client.ns.telegram.button.build_button_grid(
        _back_to_settings_layout(client)
    );

    try {
        const prompt =
            `**${client.ns.emoji.glowing_star} Atur Harga Broadcast Paid**\n\n` +
            "Masukkan jumlah Bintang (Stars) yang harus dibayar pengguna.\n\n" +
            "Ketik `0` atau `/empty` untuk menonaktifkan.\n\n" +
            "Ketik `/batal` untuk membatalkan.";
        const ask_msg = await client.ask(chat_id, prompt, 300);
        const ask_text = String(ask_msg.message || ask_msg.text || "");

        if (ask_text.toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        if (["/empty", "0"].includes(ask_text.toLowerCase())) {
            await ctx.db.removeVars(client.me.id, "broadcast_price");
            return await client.send_message(
                chat_id,
                `${client.ns.emoji.white_check_mark} **Sukses!** Fitur Paid Broadcast dinonaktifkan.`,
                { reply_markup: back_btn }
            );
        }

        if (!/^\d+$/.test(ask_text)) {
            throw new ValueError("**Format Salah**");
        }

        const stars_amount = parseInt(ask_text, 10);
        await ctx.db.setVars(client.me.id, "broadcast_price", stars_amount);
        await client.send_message(
            chat_id,
            `${client.ns.emoji.white_check_mark} **Sukses!** Harga broadcast telah diatur menjadi \`${stars_amount}\` Stars.`,
            { reply_markup: back_btn }
        );
    } catch (e: any) {
        if (
            e instanceof UserCancelledError ||
            e instanceof WaitTimeoutError ||
            e instanceof ValueError
        ) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Proses Dibatalkan**\n${e.message || e}`,
                { reply_markup: back_btn }
            );
        } else {
            throw e;
        }
    }
});

export async function _send_broadcast_message(
    client: TelegramClient,
    target_user_id: any,
    source_message: any,
    broadcast_price: number = 0
): Promise<void> {
    const caption_or_text = source_message.caption || source_message.text;
    const text_to_parse = caption_or_text ? String(caption_or_text) : "";
    const [reply_markup, cleaned_text] =
        client.ns.telegram.button.create_inline_keyboard(text_to_parse);
    const final_markup = reply_markup?.inline_keyboard
        ? reply_markup
        : source_message.reply_markup
          ? source_message.reply_markup
          : undefined;

    if (broadcast_price > 0 && (source_message.photo || source_message.video)) {
        const media_list: any[] = [];
        if (source_message.photo) {
            media_list.push({
                file_id: source_message.photo.sizes[source_message.photo.sizes.length - 1].file_id,
            });
        } else if (source_message.video) {
            media_list.push({ file_id: source_message.video.file_id });
        }
        await client.send_paid_media(target_user_id, broadcast_price, media_list, {
            caption: cleaned_text,
            reply_markup: final_markup,
        });
        return;
    }

    if (source_message.photo) {
        await client.send_photo(
            target_user_id,
            source_message.photo.sizes[source_message.photo.sizes.length - 1].file_id,
            {
                caption: cleaned_text,
                reply_markup: final_markup,
            }
        );
    } else if (source_message.text) {
        await client.send_message(target_user_id, cleaned_text, {
            reply_markup: final_markup,
        });
    } else {
        await source_message.copy(target_user_id, cleaned_text, final_markup);
    }
}

export const broadcast_callback = command(
    (_c: any) => Filters.regex("^broadcast$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            { show_alert: true }
        );
    }

    const chat_id = callback_query.message.chat.id;
    const bot_id = client.me.id;

    try {
        await callback_query.message.delete();
        const prompt =
            `**${client.ns.emoji.loudspeaker} Kirim Pesan Broadcast**\n\n` +
            "Silakan teruskan (forward) atau kirim pesan yang ingin disiarkan.\n\n" +
            "Ketik `/batal` untuk membatalkan.";
        const ask_message = await client.ask(chat_id, prompt, 600);
        const ask_text = String(ask_message.message || ask_message.text || "");
        if (ask_text.toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }

        const broadcast_price_raw = (await ctx.db.getVars(bot_id, "broadcast_price")) || 0;
        const broadcast_price = Math.trunc(Number(broadcast_price_raw));

        if (
            broadcast_price > 0 &&
            !(ask_message.photo || ask_message.video)
        ) {
            throw new ValueError(
                `${client.ns.emoji.cross_mark} **Gagal:** Paid Broadcast memerlukan media foto/video!`
            );
        }

        const user_ids = (await ctx.db.getListVars(client.me.id, "user_ids")) || [];
        if (!user_ids.length) {
            return await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Gagal:** Tidak ada pengguna.`
            );
        }

        const progress_msg = await client.send_message(
            chat_id,
            `${client.ns.emoji.white_check_mark} Memulai siaran ke \`${user_ids.length}\` pengguna...`
        );
        let success_count = 0;
        let fail_count = 0;

        const send_to_user = async (target_user_id: any): Promise<void> => {
            try {
                await _send_broadcast_message(
                    client,
                    target_user_id,
                    ask_message,
                    broadcast_price
                );
                success_count += 1;
            } catch (e: any) {
                if (e && (e.name === "FloodWait" || e.floodWaitSecs !== undefined)) {
                    await new Promise((r) =>
                        setTimeout(
                            r,
                            (Number(e.floodWaitSecs ?? e.seconds ?? 30) + 1) * 1000
                        )
                    );
                    await send_to_user(target_user_id);
                } else {
                    await ctx.db.removeListVars(client.me.id, "user_ids", target_user_id);
                    fail_count += 1;
                }
            }
            await new Promise((r) => setTimeout(r, 100));
        };

        for (const user_id of user_ids) {
            if (String(user_id) !== String(ctx.owner_id)) {
                await send_to_user(user_id);
            }
        }

        await progress_msg.delete();
        await client.send_message(
            chat_id,
            `**${client.ns.emoji.loudspeaker} Siaran Selesai!**\n` +
                `${client.ns.emoji.white_check_mark} **Terkirim:** \`${success_count}\`\n` +
                `${client.ns.emoji.cross_mark} **Gagal:** \`${fail_count}\``
        );
    } catch (e: any) {
        if (
            e instanceof UserCancelledError ||
            e instanceof WaitTimeoutError ||
            e instanceof ValueError
        ) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Gagal/Batal**\n${e.message || e}`
            );
        } else {
            throw e;
        }
    }
});