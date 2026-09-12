import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { toId } from "../../types";
import { _user_cache } from "../admin/cache";
import { invalidate_page_cache, send_allbots_list } from "./helpers";

function _sleep(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
}

export const allbots_confirm_delete_callback = command(
    (_c: any) => Filters.regex(/^allbots_confirm_delete_(\d+)_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const bot_id = Math.trunc(Number(callback_query.matches[0].group(1)));
    const page = Math.trunc(Number(callback_query.matches[0].group(2)));
    const layout = [
        [
            {
                text: "✅ Ya, Hapus",
                callback_data: `allbots_do_delete_${bot_id}_${page}`,
                style: "red",
                emoji: client.ns.emoji.id("white_check_mark"),
            },
            {
                text: "❌ Tidak",
                callback_data: `allbots_back_${page}`,
                style: "green",
                emoji: client.ns.emoji.id("cross_mark"),
            },
        ],
    ];
    const text =
        `**${client.ns.emoji.warning} Konfirmasi Penghapusan**\n\n` +
        `Anda yakin ingin menghapus bot dengan ID \`${bot_id}\` secara permanen?`;
    await callback_query.edit_message_text(text, {
        reply_markup: client.ns.telegram.button.build_button_grid(layout),
    });
});

export const allbots_do_delete_callback = command(
    (_c: any) => Filters.regex(/^allbots_do_delete_(\d+)_(\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const bot_id = Math.trunc(Number(callback_query.matches[0].group(1)));
    const page = Math.trunc(Number(callback_query.matches[0].group(2)));

    await callback_query.edit_message_text(
        `${client.ns.emoji.hourglass} Menghapus bot...`
    );
    try {
        const owner_id_to_invalidate = await ctx.db.getVars(bot_id, "owner_id");
        await ctx.manager.stop_bot(bot_id);
        await _sleep(1000);
        await ctx.db.removeBot(bot_id);
        await ctx.db.removeAllVars(bot_id);
        if (owner_id_to_invalidate) {
            _user_cache.invalidate(Number(owner_id_to_invalidate));
        }
        invalidate_page_cache(page);
        await send_allbots_list(client, callback_query, page, true);
        await callback_query.answer("✅ Bot berhasil dihapus.", {
            show_alert: true,
        });
    } catch (e: any) {
        await callback_query.answer(`❌Gagal menghapus bot: ${e}`, {
            show_alert: true,
        });
        await send_allbots_list(client, callback_query, 0, true);
    }
});