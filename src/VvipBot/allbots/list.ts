import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters, and_ } from "../filters";
import { toId } from "../../types";
import { invalidate_page_cache, send_allbots_list } from "./helpers";

export const allbots_command_handler = command(
    (_c: any) =>
        and_(
            Filters.command("allbots"),
            Filters.user((_c2: any) => ctx.owner_id as any)
        ),
    "message"
)(async (client: TelegramClient, message: any) => {
    invalidate_page_cache();
    const msg_process = await message.reply_text(
        `${client.ns.emoji.repeat} Sedang memproses mengumpulkan bot`
    );
    await send_allbots_list(client, message, 0, true);
    await msg_process.delete();
});

export const allbots_pagination_callback = command(
    (_c: any) => Filters.regex(/^allbots_(\-?\d+)/),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (toId(callback_query.from_user.id) !== toId(ctx.owner_id)) {
        return;
    }
    const page = Math.trunc(Number(callback_query.data.split("_")[1]));
    await send_allbots_list(client, callback_query, page);
});