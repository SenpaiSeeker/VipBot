import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { UserCancelledError, WaitTimeoutError, ValueError } from "../../types";
import { BACKUP_BOT } from "../../config";

export const MAX_BOTS = 30;

export const start_creation_process_callback = command(
    (_c: any) => Filters.regex("^start_creation_process$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const user_id = callback_query.from_user.id;
    const expiry_date_str = await ctx.db.getVars(user_id, "user_expiry_date");

    if (!expiry_date_str || new Date(expiry_date_str).getTime() < Date.now()) {
        return await callback_query.answer(
            "Langganan Anda tidak valid atau telah berakhir.",
            { show_alert: true }
        );
    }

    const all_bots_data = await ctx.db.getBots(true);
    if (all_bots_data.length >= MAX_BOTS) {
        const backup_text = BACKUP_BOT ? ` melalui @${BACKUP_BOT}` : "";
        return await callback_query.answer(
            `Kapasitas bot sudah penuh (${MAX_BOTS} Bot). Silakan buat bot baru${backup_text}.`,
            { show_alert: true }
        );
    }

    await callback_query.message.delete();

    try {
        const ask = (text: string): Promise<any> =>
            client.ask(
                user_id,
                `${text}\n\nKetik \`/batal\` untuk membatalkan.`,
                600
            );

        const api_id_msg = await ask(
            `**${client.ns.emoji.lock} 1/3: Masukkan API ID Anda.**\n` +
                "Dapatkan dari my.telegram.org."
        );
        if (String(api_id_msg.message || api_id_msg.text || "").toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        const api_id = api_id_msg.message || api_id_msg.text;

        const api_hash_msg = await ask(
            `**${client.ns.emoji.lock} 2/3: Masukkan API Hash Anda.**\n` +
                "Dapatkan dari my.telegram.org."
        );
        if (String(api_hash_msg.message || api_hash_msg.text || "").toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        const api_hash = api_hash_msg.message || api_hash_msg.text;

        const token_msg = await ask(
            `**${client.ns.emoji.robot} 3/3: Masukkan Bot Token Anda.**\n` +
                "Dapatkan dari @BotFather."
        );
        if (String(token_msg.message || token_msg.text || "").toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        const token = token_msg.message || token_msg.text;

        const msg = await client.send_message(
            user_id,
            `${client.ns.emoji.mag} \`Memverifikasi data & token...\``
        );
        const new_bot_name = await client.ns.telegram.arg.getNamebot(token);
        if (new_bot_name === "Bot token invalid") {
            throw new ValueError("Token bot yang Anda masukkan tidak valid.");
        }

        await msg.edit(
            `${client.ns.emoji.white_check_mark} Bot '${new_bot_name.firstName}' valid dan sedang disimpan. ` +
                `\`${client.ns.emoji.rocket} Memulai bot...\``
        );

        const new_bot_id = Math.trunc(Number(token.split(":", 1)[0]));
        const bot_data = {
            name: String(new_bot_id),
            api_id,
            api_hash,
            bot_token: token,
        };
        await ctx.manager.start_bot(bot_data);
        await ctx.db.saveBot(new_bot_id, api_id, api_hash, token, true);
        await ctx.db.setVars(new_bot_id, "bot_expiration_date", expiry_date_str);
        await ctx.db.setVars(new_bot_id, "owner_id", user_id);
        await ctx.db.removeVars(user_id, "user_expiry_date");

        await msg.edit(
            `${client.ns.emoji.party_popper} **Selamat!** Bot **${new_bot_name.firstName}** berhasil dibuat dan aktif.`
        );
    } catch (e: any) {
        if (e instanceof UserCancelledError) {
            await client.send_message(
                user_id,
                `${client.ns.emoji.cross_mark} **Proses Dibatalkan**`
            );
        } else if (e instanceof WaitTimeoutError) {
            await client.send_message(
                user_id,
                `${client.ns.emoji.alarm_clock} **Waktu Habis**\nProses telah dibatalkan otomatis.`
            );
        } else if (e instanceof ValueError) {
            await client.send_message(
                user_id,
                `${client.ns.emoji.cross_mark} **Error Pembuatan Bot:** \`${e.message}\``
            );
        } else {
            await client.send_message(
                user_id,
                `${client.ns.emoji.cross_mark} **Error Pembuatan Bot:** \`${e}\``
            );
        }
    }
});