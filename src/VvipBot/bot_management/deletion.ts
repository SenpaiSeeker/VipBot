import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { toId } from "../../types";

async function _get_bot_display_name(
    client: TelegramClient,
    bot_id: number
): Promise<string> {
    try {
        const bot_instance = ctx.manager.running_bots.get(bot_id);
        if (bot_instance && bot_instance.is_connected) {
            return bot_instance.me.firstName;
        }
    } catch {
        // ignore
    }
    return `ID ${bot_id}`;
}

export const confirm_delete_bot_callback = command(
    (_c: any) => Filters.regex("^confirm_delete_bot\\s(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const bot_id_to_manage = Math.trunc(
        Number(callback_query.data_string.split(" ", 2)[1])
    );
    const bot_name = await _get_bot_display_name(client, bot_id_to_manage);

    const text =
        `**${client.ns.emoji.exclamation} Konfirmasi Penghapusan**\n\n` +
        `Anda yakin ingin menghapus bot **${bot_name}** (\`${bot_id_to_manage}\`) secara permanen?\n\n` +
        "__Semua data (member, paket, pengaturan) bot ini akan hilang dan tindakan ini tidak dapat diurungkan.__";
    const layout = [
        [
            {
                text: "✅ Ya, Saya Yakin Hapus",
                callback_data: `do_delete_bot ${bot_id_to_manage}`,
                style: "red",
                emoji: client.ns.emoji.id("minus"),
            },
            {
                text: "❌ Tidak, Batalkan",
                callback_data: `manage_bot ${bot_id_to_manage}`,
                style: "green",
                emoji: client.ns.emoji.id("white_check_mark"),
            },
        ],
    ];
    const btn = client.ns.telegram.button.build_button_grid(layout);
    if (callback_query.message && callback_query.message.photo) {
        await callback_query.edit_message_caption(text, { reply_markup: btn });
    } else {
        await callback_query.edit_message_text(text, { reply_markup: btn });
    }
});

export const do_delete_bot_callback = command(
    (_c: any) => Filters.regex("^do_delete_bot\\s(\\d+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    const bot_id_to_manage = Math.trunc(
        Number(callback_query.data_string.split(" ", 2)[1])
    );
    const user_id = callback_query.from_user.id;
    const owner_of_target_bot =
        (await ctx.db.getVars(bot_id_to_manage, "owner_id")) || 0;

    if (toId(user_id) !== toId(owner_of_target_bot) && toId(user_id) !== ctx.owner_id) {
        return await callback_query.answer(
            "Anda tidak berhak menghapus bot ini.",
            { show_alert: true }
        );
    }

    await callback_query.edit_message_caption(
        `${client.ns.emoji.hourglass} Sedang menghentikan dan menghapus bot \`${bot_id_to_manage}\`...`
    );
    try {
        await ctx.manager.stop_bot(bot_id_to_manage);
        await ctx.db.removeBot(bot_id_to_manage);
        await ctx.db.removeAllVars(bot_id_to_manage);

        const layout = [
            [
                {
                    text: "⬅️ Kembali ke Daftar Bot",
                    callback_data: "list_my_bots_0",
                    style: "blue",
                    emoji: client.ns.emoji.id("back_arrow"),
                },
            ],
        ];
        const btn = client.ns.telegram.button.build_button_grid(layout);
        await callback_query.edit_message_caption(
            `${client.ns.emoji.white_check_mark} **Penghapusan Berhasil!**\n` +
                `Bot \`${bot_id_to_manage}\` beserta datanya telah dihapus dari sistem.`,
            { reply_markup: btn }
        );
    } catch (e: any) {
        await callback_query.edit_message_caption(
            `${client.ns.emoji.cross_mark} Terjadi kesalahan saat menghapus bot: \`${e}\``
        );
    }
});