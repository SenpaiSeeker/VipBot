import { TelegramClient } from "teleproto";
import { ctx } from "../index";
import { _user_cache } from "../admin/cache";
import { toId } from "../../types";

type Any = any;

const _page_cache: Record<number, Any> = {};

const ITEMS_PER_PAGE = 25;

async function _unwrap_user(client: Any, user_id: Any): Promise<Any | undefined> {
    const users = await client.get_users(toId(user_id));
    return Array.isArray(users) ? users[0] : users;
}

export async function _resolve_owner_text(
    client: Any,
    owner_id: Any
): Promise<string> {
    if (!owner_id) {
        return "Tidak diketahui";
    }
    const owner_key = Number(owner_id);
    const cached = _user_cache.get(owner_key);
    if (cached !== undefined) {
        return client.ns.telegram.arg.getMention(cached);
    }
    try {
        const owner_user = await _unwrap_user(client, owner_key);
        _user_cache.set(owner_key, owner_user);
        return client.ns.telegram.arg.getMention(owner_user);
    } catch {
        return `ID <code>${owner_id}</code>`;
    }
}

async function _prefetch_owners(client: Any, owner_ids: Record<number, Any>): Promise<void> {
    const unique_uncached = new Set<number>();
    for (const oid of Object.values(owner_ids)) {
        if (oid && _user_cache.get(Number(oid)) === undefined) {
            unique_uncached.add(Number(oid));
        }
    }
    if (!unique_uncached.size) {
        return;
    }
    const fetched = await Promise.all(
        Array.from(unique_uncached).map((oid) =>
            _unwrap_user(client, oid).catch(() => undefined)
        )
    );
    let i = 0;
    for (const oid of unique_uncached) {
        const result = fetched[i];
        if (result !== undefined) {
            _user_cache.set(oid, result);
        }
        i += 1;
    }
}

function _bot_username_status(client: Any, bot_id: number): string {
    try {
        const bot_instance = ctx.manager.running_bots.get(bot_id);
        if (bot_instance && bot_instance.is_connected) {
            if (bot_instance.me.username) {
                return `@${bot_instance.me.username}`;
            }
            return bot_instance.me.firstName;
        }
        return "Offline";
    } catch {
        return "Error";
    }
}

async function _days_left_text(client: Any, bot_id: number): Promise<any> {
    const exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date");
    if (!exp_date_str) {
        return "N/A";
    }
    const diff_ms = new Date(exp_date_str).getTime() - Date.now();
    return Math.floor(diff_ms / 86400000);
}

async function _build_page(client: Any, page: number): Promise<Any> {
    const all_bots = await ctx.db.getBots(true);
    if (!all_bots.length) {
        return { empty: true };
    }

    const total_pages = Math.ceil(all_bots.length / ITEMS_PER_PAGE);
    page = ((page + total_pages) % total_pages + total_pages) % total_pages;
    const paginated_bots = all_bots.slice(
        page * ITEMS_PER_PAGE,
        (page + 1) * ITEMS_PER_PAGE
    );

    const owner_ids: Record<number, Any> = {};
    for (const bot_data of paginated_bots) {
        const bot_id = Math.trunc(Number(bot_data["name"]));
        owner_ids[bot_id] = await ctx.db.getVars(bot_id, "owner_id");
    }
    await _prefetch_owners(client, owner_ids);

    const text_lines = [
        `<b>${client.ns.emoji.open_folder} Daftar Semua Bot (${page + 1}/${total_pages})</b>\n`,
    ];
    const layout: Any[] = [];
    let button_row: Any[] = [];
    const bot_rows: Any[] = [];

    let index = 0;
    for (const bot_data of paginated_bots) {
        index += 1;
        const bot_id = Math.trunc(Number(bot_data["name"]));
        const bot_username = _bot_username_status(client, bot_id);
        const owner_id = owner_ids[bot_id];
        const owner_text = await _resolve_owner_text(client, owner_id);
        const days_left = await _days_left_text(client, bot_id);

        text_lines.push(
            `<b>${String(index).padStart(2)}:</b> ${bot_username} (<code>${bot_id}</code>)\n` +
                ` ├ ${client.ns.emoji.bust_in_silhouette} Owner: ${owner_text}\n` +
                ` ├ ${client.ns.emoji.hourglass} Aktif: <code>${days_left}</code> hari lagi`
        );
        bot_rows.push({
            bot_id: bot_id,
            owner_id: owner_id,
            days_left: days_left,
        });
        button_row.push({
            text: String(index),
            callback_data: `allbots_detail_${bot_id}_${page}`,
            style: "blue",
            emoji: client.ns.emoji.id("robot"),
        });
        if (button_row.length === 5) {
            layout.push(button_row);
            button_row = [];
        }
    }
    if (button_row.length) {
        layout.push(button_row);
    }

    if (total_pages > 1) {
        const prev_page = ((page - 1 + total_pages) % total_pages + total_pages) % total_pages;
        const next_page = (page + 1) % total_pages;
        layout.push([
            {
                text: "« Prev",
                callback_data: `allbots_${prev_page}`,
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
            {
                text: "Next »",
                callback_data: `allbots_${next_page}`,
                style: "blue",
                emoji: client.ns.emoji.id("right_pointing"),
            },
        ]);
    }

    layout.push([
        {
            text: "Tutup Panel",
            callback_data: "close_panel",
            style: "red",
            emoji: client.ns.emoji.id("cross_mark"),
        },
    ]);

    return {
        empty: false,
        page: page,
        total_pages: total_pages,
        text: text_lines.join("\n"),
        layout: layout,
        bot_rows: bot_rows,
    };
}

export async function send_allbots_list(
    client: Any,
    message_or_query: Any,
    page: number,
    force_refresh = false
): Promise<void> {
    if (force_refresh) {
        delete _page_cache[page];
    }
    if (!(page in _page_cache)) {
        _page_cache[page] = await _build_page(client, page);
    }

    const cached = _page_cache[page];
    if (cached["empty"]) {
        const text = "Belum ada bot yang dibuat oleh pengguna manapun.";
        if (typeof message_or_query.reply_text === "function") {
            return await message_or_query.reply_text(text);
        }
        return await message_or_query.answer(text, { show_alert: true });
    }

    const btn = client.ns.telegram.button.build_button_grid(cached["layout"]);
    if (typeof message_or_query.reply_text === "function") {
        await message_or_query.reply_text(cached["text"], { reply_markup: btn });
    } else {
        await message_or_query.edit_message_text(cached["text"], {
            reply_markup: btn,
        });
    }
}

export function invalidate_page_cache(page?: number | null): void {
    if (page === undefined || page === null) {
        for (const key of Object.keys(_page_cache)) {
            delete _page_cache[Number(key)];
        }
    } else {
        delete _page_cache[page];
    }
}