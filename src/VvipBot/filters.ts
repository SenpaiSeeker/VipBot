import { Api } from "teleproto";
import { toId } from "../types";

type Any = any;

export type UpdateKind = "message" | "callback" | "pre_checkout";

export interface FilterContext {
    kind: UpdateKind;
    message?: Any;
    callback?: Any;
    preCheckout?: Any;
    client?: Any;
}

export type AnyFilter = (ctx: FilterContext) => boolean | Promise<boolean>;

export function and_<T extends AnyFilter[]>(...filters: T): AnyFilter {
    const f = (ctx: FilterContext): boolean | Promise<boolean> => {
        for (const filter of filters) {
            const r = filter(ctx);
            if (r instanceof Promise) {
                return (async () => {
                    for (const filt of filters) {
                        if (!(await filt(ctx))) {
                            return false;
                        }
                    }
                    return true;
                })();
            }
            if (!r) {
                return false;
            }
        }
        return true;
    };
    return f;
}

function _messageText(msg: Any): string {
    if (!msg) {
        return "";
    }
    return msg.message || msg.caption || msg.text || "";
}

function _senderIdOf(ctx: FilterContext): string | undefined {
    const msg = ctx.message;
    if (msg) {
        if (msg.from_user && msg.from_user.id) {
            return toId(msg.from_user.id);
        }
        if (msg.senderId) {
            return toId(msg.senderId);
        }
        if (msg.fromId) {
            return toId(msg.fromId);
        }
        return undefined;
    }
    const cb = ctx.callback;
    if (cb) {
        if (cb.from_user && cb.from_user.id) {
            return toId(cb.from_user.id);
        }
        if (cb.senderId) {
            return toId(cb.senderId);
        }
        return undefined;
    }
    const pq = ctx.preCheckout;
    if (pq) {
        if (pq.from_user && pq.from_user.id) {
            return toId(pq.from_user.id);
        }
        if (pq.userId) {
            return toId(pq.userId);
        }
    }
    return undefined;
}

function _userIdOf(id: any): string | undefined {
    if (id === null || id === undefined) {
        return undefined;
    }
    if (typeof id === "object" && id.id !== undefined) {
        return toId(id.id);
    }
    return toId(id);
}

function _isPrivate(msg: Any): boolean {
    if (!msg) {
        return false;
    }
    if (msg.chat) {
        const chat = msg.chat;
        if (typeof chat.isPrivate === "function") {
            return chat.isPrivate();
        }
        if (chat instanceof Api.User) {
            return true;
        }
        if (chat._ === "User") {
            return true;
        }
        const c = msg.chatId;
        if (c && c > 0n) {
            return true;
        }
    }
    const peer = msg.peerId;
    if (peer && typeof peer === "object") {
        if (peer instanceof Api.PeerUser) {
            return true;
        }
        const p = peer as Any;
        if (p.className === "PeerUser") {
            return true;
        }
    }
    return false;
}

function normalizeCommandName(name: string): string {
    return name.replace(/^\//, "").toLowerCase();
}

export function command(...names: (string | string[])[]): AnyFilter {
    const flat: string[] = [];
    for (const n of names) {
        if (Array.isArray(n)) {
            flat.push(...n);
        } else {
            flat.push(n);
        }
    }
    const normalized = flat.map(normalizeCommandName);
    return (ctx: FilterContext) => {
        if (ctx.kind !== "message" || !ctx.message) {
            return false;
        }
        const text = _messageText(ctx.message).trim();
        const parts = text.split(/\s+/);
        if (parts.length === 0) {
            return false;
        }
        const first = parts[0].toLowerCase();
        for (const cmd of normalized) {
            if (first === `/${cmd}` || first === `/${cmd}@bot`) {
                return true;
            }
            const at = first.indexOf("@");
            if (at > 0 && first.slice(0, at) === `/${cmd}`) {
                return true;
            }
        }
        return false;
    };
}

export function user(users: Any | Any[]): AnyFilter {
    const list = Array.isArray(users) ? users : [users];
    const ids = new Set<string>();
    for (const u of list) {
        const id = _userIdOf(u);
        if (id !== undefined) {
            ids.add(id);
        }
    }
    return (ctx: FilterContext) => {
        const sid = _senderIdOf(ctx);
        if (sid === undefined) {
            return false;
        }
        return ids.has(sid);
    };
}

export const private_ = (ctx: FilterContext): boolean => {
    if (ctx.kind !== "message") {
        return false;
    }
    return _isPrivate(ctx.message);
};

function _pyMatch(match: RegExpExecArray): Any {
    return {
        group(n: number | string): string | undefined {
            if (typeof n === "number" && n >= 0 && n < match.length) {
                return match[n];
            }
            if (typeof n === "string" && match.groups) {
                return match.groups[n];
            }
            return undefined;
        },
    };
}

export function regex(pattern: RegExp | string): AnyFilter {
    const re = typeof pattern === "string" ? new RegExp(pattern) : pattern;
    return (ctx: FilterContext) => {
        if (ctx.kind === "callback" && ctx.callback) {
            const data = ctx.callback.decodedData ?? ctx.callback.data;
            let str: string;
            if (typeof data === "string") {
                str = data;
            } else if (Buffer.isBuffer(data)) {
                str = Buffer.from(data).toString("utf-8");
            } else {
                str = String(data ?? "");
            }
            re.lastIndex = 0;
            const m = re.exec(str);
            if (m) {
                (ctx.callback as Any).matches = [_pyMatch(m)];
                return true;
            }
            return false;
        }
        if (ctx.kind === "message" && ctx.message) {
            const text = _messageText(ctx.message);
            re.lastIndex = 0;
            const m = re.exec(text);
            if (m) {
                (ctx.message as Any).matches = [_pyMatch(m)];
                return true;
            }
            return false;
        }
        return false;
    };
}

export const successful_payment = (ctx: FilterContext): boolean => {
    if (ctx.kind !== "message" || !ctx.message) {
        return false;
    }
    return Boolean(ctx.message.successful_payment);
};

export class PreCheckoutQuery {}

export const Filters = {
    command,
    user,
    regex,
    successful_payment,
    private: private_,
    PreCheckoutQuery,
    and: and_,
};