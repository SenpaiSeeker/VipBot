import path from "path";
import * as fs from "fs";
import { Api, TelegramClient } from "teleproto";
import { NewMessage, CallbackQuery, Raw } from "teleproto/events";
import {
    Filters,
    type AnyFilter,
    type FilterContext,
} from "./filters";
import { IGNORED_HANDLER_ERRORS, messageExceptionName } from "../errors";
import { toId } from "../types";
import { patchListen } from "../helpers/listen";
import {
    ServicePaymentMessage,
    successfulPaymentViewFromAction,
    peerUserId,
    patchMessageGetters,
} from "../helpers/messageGetters";
import { PreCheckoutQueryEvent } from "../helpers/preCheckoutEvent";

type Any = any;

export interface HandlerEntry {
    func: (client: Any, update: Any, ...args: Any[]) => Promise<Any>;
    filterLambda: (ctx: Any) => AnyFilter;
    handlerType: string;
    _computedFilter?: AnyFilter;
}

export const ALL_HANDLERS: HandlerEntry[] = [];

export class HandlerContext {
    [key: string]: any;
    db: Any = undefined;
    manager: Any = undefined;
    owner_id: string = "";
    log: Any = undefined;
    ACTIVE_MEMBERS_CACHE: Any = {};
}

export const ctx = new HandlerContext();

export function command(
    filter_lambda: (ctx: Any) => AnyFilter,
    handler_type: string = "message"
) {
    return (func: Any) => {
        ALL_HANDLERS.push({
            func,
            filterLambda: filter_lambda,
            handlerType: handler_type,
        });
        return func;
    };
}

export function seller_only(func: Any): Any {
    const wrapper = async (
        client: TelegramClient,
        update: Any,
        ...args: Any[]
    ): Promise<Any> => {
        const updateAny = update as Any;
        const user_id = updateAny.from_user?.id
            ? toId(updateAny.from_user.id)
            : undefined;
        const seller_list =
            (await ctx.db.getListVars(ctx.owner_id, "seller_id_list")) || [];
        const sellerIds = (seller_list as Any[]).map((s) =>
            toId(typeof s === "object" ? s.id : s)
        );
        if (
            user_id !== undefined &&
            (user_id === ctx.owner_id || sellerIds.includes(user_id))
        ) {
            return func(client, update, ...args);
        }
        const error_message = `${client.ns.emoji.cross_mark} **Akses Ditolak!**\nAnda tidak memiliki izin untuk menggunakan perintah ini.`;
        if (updateAny.getMessage) {
            return updateAny.answer(error_message, { show_alert: true });
        }
        if (updateAny.reply_text) {
            return updateAny.reply_text(error_message);
        }
        return undefined;
    };
    return wrapper;
}

export async function is_bot_owner(
    client: TelegramClient,
    user_id: Any
): Promise<boolean> {
    const owner_of_this_bot = await ctx.db.getVars(client.me.id, "owner_id");
    const uid = toId(user_id);
    return (
        uid === ctx.owner_id ||
        (owner_of_this_bot && uid === toId(owner_of_this_bot))
    );
}

export async function get_notification_target(
    client: TelegramClient
): Promise<string> {
    const target = await ctx.db.getVars(client.me.id, "notif_chat_id");
    if (target) {
        return toId(target);
    }
    const owner = await ctx.db.getVars(client.me.id, "owner_id");
    if (owner) {
        return toId(owner);
    }
    return ctx.owner_id;
}

export async function check_new_user(
    client: TelegramClient,
    update: Any
): Promise<void> {
    if (!update || !update.from_user) {
        return;
    }

    const user_list = await ctx.db.getListVars(client.me.id, "user_ids");
    if (
        user_list.some((u: Any) => toId(u) === toId(update.from_user.id))
    ) {
        return;
    }

    await ctx.db.setListVars(client.me.id, "user_ids", update.from_user.id);
    const owner_of_this_bot =
        (await ctx.db.getVars(client.me.id, "owner_id")) || ctx.owner_id;
    try {
        const mention_user = client.ns.telegram.arg.getMention(update.from_user);
        const notification_text =
            `**${client.ns.emoji.bust_in_silhouette} Pengguna Baru Telah Memulai Bot Anda!**\n\n` +
            `**Bot:** ${client.me.mention}\n` +
            `**Pengguna:** ${mention_user}\n` +
            `**ID:** \`${update.from_user.id}\``;
        await client.send_message(owner_of_this_bot, notification_text);
    } catch {
        // ignore notification errors
    }

    ctx.log.print(
        `${ctx.log.CYAN}User baru ${client.ns.telegram.arg.getMention(
            update.from_user,
            true
        )} memulai bot ${client.me.firstName}`
    );
}

export async function _load_all_handlers(): Promise<void> {
    const currentDir = __dirname;
    const flat_paths = fs
        .readdirSync(currentDir)
        .filter((f) => f.endsWith(".js") && !f.endsWith(".d.ts"));
    const flat_modules = flat_paths
        .map((f) => path.basename(f).replace(/\.js$/, ""))
        .filter((name) => name !== "index" && !name.startsWith("_"))
        .sort();
    for (const moduleName of flat_modules) {
        try {
            await import(path.join(currentDir, moduleName));
        } catch (e) {
            ctx.log?.print?.(`Gagal load handler ${moduleName}: ${e}`);
        }
    }

    const entries = fs.readdirSync(currentDir, { withFileTypes: true });
    for (const entry of entries.sort((a, b) => (a.name < b.name ? -1 : 1))) {
        if (!entry.isDirectory() || entry.name.startsWith("_")) {
            continue;
        }
        const pkgInit = path.join(currentDir, entry.name, "index.js");
        if (fs.existsSync(pkgInit)) {
            try {
                await import(pkgInit);
            } catch (e) {
                ctx.log?.print?.(
                    `Gagal load handler pkg ${entry.name}: ${e}`
                );
            }
        }
    }
}

async function _log_handler_error(e: Any): Promise<void> {
    const message = `${ctx.log.RED}[ERROR]: ${ctx.log.YELLOW}${messageExceptionName(
        e
    )}: ${ctx.log.RED}${e}${ctx.log.WHITE}`;
    ctx.log.print(message);
}

export function _make_handler_wrapper(original_func: Any): Any {
    return async (client: TelegramClient, update: Any, ...args: Any[]) => {
        const sender = update?.from_user || update?.sender_chat;
        if (sender !== undefined && sender !== null && sender.id !== undefined) {
            sender.id;
        }
        try {
            console.log("[DBG-WRAP-BEGIN]");
            await original_func(client, update, ...args);
            console.log("[DBG-WRAP-END]");
        } catch (e) {
            console.error("[DBG-WRAP-ERR]", e);
            const ee = e as Any;
            if (IGNORED_HANDLER_ERRORS.some((Cls) => ee instanceof Cls)) {
                return;
            }
            await _log_handler_error(e);
        }
    };
}

export function _installServiceHandler(client: TelegramClient): void {
    let installed = (client as Any)._vvipServiceHandlerInstalled;
    if (installed) {
        return;
    }
    (client as Any)._vvipServiceHandlerInstalled = true;
    client.addEventHandler(
        async (rawUpdate: Any) => {
            let service: Api.MessageService | undefined;
            if (rawUpdate instanceof Api.UpdateNewMessage) {
                const m = rawUpdate.message as Any;
                if (m instanceof Api.MessageService) {
                    service = m;
                }
            } else if (rawUpdate instanceof Api.UpdateNewChannelMessage) {
                const m = rawUpdate.message as Any;
                if (m instanceof Api.MessageService) {
                    service = m;
                }
            }
            if (!service) {
                return;
            }
            const view = successfulPaymentViewFromAction(service.action);
            if (!view) {
                return;
            }
            let from_user: Any;
            const uid = peerUserId(service.fromId) || peerUserId(service.peerId);
            if (uid) {
                try {
                    from_user = await client.getEntity(uid);
                } catch {
                    from_user = {
                        id: uid,
                        firstName: "",
                        lastName: undefined,
                        username: undefined,
                        mention: mentionOf(uid, ""),
                    };
                }
            } else {
                from_user = undefined;
            }
            const svcMessage = new ServicePaymentMessage(
                service,
                view,
                from_user,
                service.id
            );
            for (const entry of ALL_HANDLERS) {
                if (entry.handlerType !== "message") {
                    continue;
                }
                const filter = entry._computedFilter;
                if (filter !== Filters.successful_payment) {
                    continue;
                }
                await _make_handler_wrapper(entry.func)(client, svcMessage);
            }
        },
        new Raw({
            types: [Api.UpdateNewMessage, Api.UpdateNewChannelMessage],
        })
    );
}

export function mentionOf(id: Any, name: string): string {
    const uid = toId(id);
    const safe = name || "User";
    return `<a href="tg://user?id=${uid}">${safe}</a>`;
}

export function register_all_handlers(
    client: TelegramClient,
    db_instance: Any,
    bot_manager: Any,
    owner_id: Any
): void {
    ctx.db = db_instance;
    ctx.manager = bot_manager;
    ctx.owner_id = toId(owner_id);
    ctx.log = client.ns.utils.log;
    ctx.ACTIVE_MEMBERS_CACHE = {};

    patchMessageGetters(client);

    for (const entry of ALL_HANDLERS) {
        entry._computedFilter = entry.filterLambda(ctx as Any);
        if (!entry._computedFilter) {
            console.log(`[DBG-REG] EMPTY_COMPUTED slot=${ALL_HANDLERS.indexOf(entry)}`);
        }
        if (entry.handlerType === "pre_checkout") {
            client.addEventHandler(
                async (rawUpdate: Any) => {
                    if (!(rawUpdate instanceof Api.UpdateBotPrecheckoutQuery)) {
                        return;
                    }
                    const event = new PreCheckoutQueryEvent(client, rawUpdate);
                    await _make_handler_wrapper(entry.func)(client, event);
                },
                new Raw({ types: [Api.UpdateBotPrecheckoutQuery] })
            );
        } else if (entry.handlerType === "callback") {
            client.addEventHandler(
                async (cq: Any) => {
                    const fctx: FilterContext = {
                        kind: "callback",
                        callback: cq,
                        client,
                    };
                    if (!(await entry._computedFilter!(fctx))) {
                        return;
                    }
                    let message: Any;
                    try {
                        message = await cq.getMessage();
                    } catch {
                        message = undefined;
                    }
                    if (message) {
                        (cq as Any)._vvipMessage = message;
                    }
                    try {
                        const sender = await cq.getSender();
                        if (sender) {
                            (cq as Any)._vvipFromUser = sender;
                        }
                    } catch {
                        // ignore
                    }
                    await _make_handler_wrapper(entry.func)(client, cq);
                },
                new CallbackQuery({} as Any)
            );
        }
    }

    client.addEventHandler(
        async (event: Any) => {
            const message = event?.message;
            if (!message) {
                return;
            }
            console.log(
                `[DBG-MSG] text=${JSON.stringify(message.message ?? message.text ?? "")} from=${JSON.stringify(message.fromId ?? null)} chat=${JSON.stringify(message.chat ? { _: message.chat._, id: message.chat.id } : null)} peer=${message.peerId ? message.peerId.className : null} out=${!!message.out}`
            );
            if (String(message.message ?? message.text ?? "").trim().toLowerCase() === "/start") {
                const fctx2: FilterContext = { kind: "message", message, client };
                const priv = await (Filters.private as AnyFilter)(fctx2);
                const cmdf = Filters.command("start") as AnyFilter;
                const cmd = await cmdf(fctx2);
                console.log(`[DBG-START] private=${priv} command=${cmd}`);
            }
            for (const entry of ALL_HANDLERS) {
                if (entry.handlerType !== "message") {
                    continue;
                }
                const fctx: FilterContext = {
                    kind: "message",
                    message,
                    client,
                };
                if (await entry._computedFilter!(fctx)) {
                    console.log(`[DBG-HIT] slot=${ALL_HANDLERS.indexOf(entry)} handlerType=${entry.handlerType}`);
                    await _make_handler_wrapper(entry.func)(client, message);
                }
            }
        },
        new NewMessage({} as Any)
    );

    _installServiceHandler(client);
    patchListen();
    console.log(`[DBG-REG] total=${ALL_HANDLERS.length} computed=${ALL_HANDLERS.filter((e) => !!e._computedFilter).length}`);
    ALL_HANDLERS.forEach((e, i) =>
        console.log(`[DBG-SLOT] ${i} ${e.handlerType} ${e.func.toString().replace(/\s+/g, " ").slice(0, 140)}`)
    );
}