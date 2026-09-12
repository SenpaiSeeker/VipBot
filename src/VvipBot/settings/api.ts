import { TelegramClient } from "teleproto";
import { command, ctx, is_bot_owner } from "../index";
import { Filters } from "../filters";
import { UserCancelledError, WaitTimeoutError } from "../../types";
import { initialize_bot_services } from "../../services";

function _back_to_api_layout(client: TelegramClient): any[] {
    return [
        [
            {
                text: "• Kembali ke Pengaturan API •",
                callback_data: "api_settings",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
}

async function _reply(
    client: TelegramClient,
    callback_query: any,
    text: string,
    btn: any
): Promise<void> {
    if (callback_query.message.photo) {
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else {
        await callback_query.edit_message_text(text, { reply_markup: btn });
    }
}

export const api_settings_callback = command(
    (_c: any) => Filters.regex("^api_settings$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const saweria_user_id = await ctx.db.getVars(client.me.id, "SAWERIA_USER_ID");
    const saweria_status = saweria_user_id
        ? `${client.ns.emoji.white_check_mark} Aktif`
        : `${client.ns.emoji.cross_mark} Belum Diatur`;

    const layout = [
        [
            {
                text: "💳 Atur Kunci Saweria",
                callback_data: "set_api SAWERIA",
                style: "green",
                emoji: client.ns.emoji.id("gem"),
            },
        ],
        [
            {
                text: "🗑️ Hapus Semua Kunci",
                callback_data: "del_api_confirm",
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
        ],
        [
            {
                text: "• Kembali ke Pengaturan •",
                callback_data: "settings",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
    const text =
        `**${client.ns.emoji.key} Pengelola Kunci API untuk ${client.me.mention}**\n\n` +
        "Atur koneksi pembayaran Saweria untuk bot Anda.\n\n" +
        "**Status Layanan:**\n" +
        `- \`Gateway Pembayaran (Saweria)\`: **${saweria_status}**\n\n` +
        "Pilih tindakan:";
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});

export const set_api_key_prompt = command(
    (_c: any) => Filters.regex("^set_api\\s(.+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const chat_id = callback_query.from_user.id;
    const key_name = callback_query.data_string.split(" ", 2)[1];
    await callback_query.message.delete();

    const back_btn = client.ns.telegram.button.build_button_grid(
        _back_to_api_layout(client)
    );
    try {
        const ask = (p: string): Promise<any> =>
            client.ask(
                chat_id,
                `${p}\n\nKetik \`/batal\` untuk membatalkan.`,
                600
            );

        if (key_name === "SAWERIA") {
            const username_msg = await ask(
                `**2/2:** Kirim **Username Saweria** Anda.`
            );
            const username_text = String(
                username_msg.message || username_msg.text || ""
            );
            if (username_text.toLowerCase() === "/batal") {
                throw new UserCancelledError();
            }

            const processing_msg = await client.send_message(
                chat_id,
                `${client.ns.emoji.hourglass} **Sedang Memproses...**\nMohon tunggu sebentar.`
            );
            try {
                const saweria_temp = new client.ns.payment.SaweriaScraper();
                const user_id_saweria = await saweria_temp.get_user_id(username_text);
                if (!user_id_saweria) {
                    throw new Error("Username Saweria tidak ditemukan.");
                }

                await ctx.db.setVars(
                    client.me.id,
                    "SAWERIA_USER_ID",
                    user_id_saweria
                );
                await processing_msg.delete();
                await client.send_message(
                    chat_id,
                    `${client.ns.emoji.white_check_mark} **Sukses!**\nKunci Saweria berhasil disimpan.`,
                    { reply_markup: back_btn }
                );
            } catch (e: any) {
                await processing_msg.edit_text(
                    `${client.ns.emoji.cross_mark} **Gagal!**\n\`Error: ${e}\``,
                    { reply_markup: back_btn }
                );
                return;
            }
        } else {
            await client.send_message(chat_id, "Fitur tidak didukung.", {
                reply_markup: back_btn,
            });
            return;
        }

        await initialize_bot_services(client, ctx.db);
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

export const confirm_delete_api_keys = command(
    (_c: any) => Filters.regex("^del_api_confirm$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const text =
        `**${client.ns.emoji.exclamation} Konfirmasi**\n\n` +
        "Anda yakin ingin menghapus **SEMUA** kunci API?";
    const layout = [
        [
            {
                text: "✅ Ya, Hapus Semua",
                callback_data: "do_del_api",
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
            {
                text: "❌ Tidak, Batalkan",
                callback_data: "api_settings",
                style: "green",
                emoji: client.ns.emoji.id("white_check_mark"),
            },
        ],
    ];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
});

export const do_delete_api_keys = command(
    (_c: any) => Filters.regex("^do_del_api$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    await ctx.db.removeVars(client.me.id, "SAWERIA_USER_ID");
    await initialize_bot_services(client, ctx.db);

    await callback_query.answer(
        "Semua kunci API untuk bot ini telah berhasil dihapus.",
        { show_alert: true }
    );
    await api_settings_callback(client, callback_query);
});