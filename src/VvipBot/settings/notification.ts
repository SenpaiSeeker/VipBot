import { TelegramClient } from "teleproto";
import { command, ctx, is_bot_owner } from "../index";
import { Filters } from "../filters";
import { UserCancelledError, WaitTimeoutError } from "../../types";

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

export const set_notif_chat_callback = command(
    (_c: any) => Filters.regex("^set_notif_chat$"),
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
            `**${client.ns.emoji.bell} Atur Tempat Notifikasi**\n\n` +
            "Kirim ID chat atau @username tempat notifikasi pembayaran akan dikirim.\n\n" +
            "Ketik `/none` untuk kembali ke default (dikirim ke owner_id).\n\n" +
            "Ketik `/batal` untuk membatalkan.";
        const ask_msg = await client.ask(chat_id, prompt, 600);

        const ask_text = String(ask_msg.message || ask_msg.text || "");
        if (!ask_text) {
            return await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Gagal:** Pesan bukan teks.`,
                { reply_markup: back_btn }
            );
        }
        if (ask_text.toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        if (ask_text.toLowerCase() === "/none") {
            await ctx.db.removeVars(client.me.id, "notif_chat_id");
            return await client.send_message(
                chat_id,
                `${client.ns.emoji.white_check_mark} **Sukses!** Notifikasi kembali ke default (owner_id).`,
                { reply_markup: back_btn }
            );
        }

        await ctx.db.setVars(client.me.id, "notif_chat_id", ask_text);
        await client.send_message(
            chat_id,
            `${client.ns.emoji.white_check_mark} **Sukses!** Tempat notifikasi diatur ke \`${ask_text}\`.`,
            { reply_markup: back_btn }
        );
    } catch (e: any) {
        if (e instanceof UserCancelledError || e instanceof WaitTimeoutError) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Proses Dibatalkan**`,
                { reply_markup: back_btn }
            );
        } else {
            throw e;
        }
    }
});