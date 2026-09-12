import type { Api } from "teleproto";

export type Id = string;

export interface ParseInterface {
    parse: (message: string) => [string, Api.TypeMessageEntity[]];
    unparse: (text: string, entities: Api.TypeMessageEntity[]) => string;
}

export function toId(value: unknown): Id {
    if (value === null || value === undefined) {
        return "";
    }
    if (typeof value === "string") {
        return value;
    }
    if (typeof (value as { toString?: unknown }).toString === "function") {
        return (value as { toString: () => string }).toString();
    }
    return String(value);
}

export function idEq(a: unknown, b: unknown): boolean {
    if (a === null || a === undefined || b === null || b === undefined) {
        return false;
    }
    return toId(a) === toId(b);
}

export class ValueError extends Error {
    constructor(message?: string) {
        super(message ?? "");
        this.name = "ValueError";
    }
}

export function titleCase(s: string): string {
    return s.replace(/\p{L}[\p{L}\p{N}]*/gu, (word) => {
        const first = word[0].toUpperCase();
        const rest = word
            .slice(1)
            .replace(/\p{Ll}/gu, (c) => c.toLowerCase());
        return first + rest;
    });
}

export function dget(obj: any, key: string, def?: any): any {
    if (obj == null) {
        return def;
    }
    if (obj instanceof Map) {
        return obj.has(key) ? obj.get(key) : def;
    }
    const v = obj[key];
    return v === undefined || v === null ? def : v;
}

export interface VipListItem {
    name: string;
    price: number;
    promo_price: number;
    discounted_price?: number;
    link?: string;
    description?: string;
    group_link?: string;
    [key: string]: unknown;
}

export interface MemberRecord {
    user_id?: string | number;
    name?: string;
    username?: string;
    avatar?: string;
    joined_date?: string;
    expires_date?: string;
    [key: string]: unknown;
}

export interface GridButton {
    text: string;
    callback_data?: string;
    url?: string;
    web_app?: string | { url: string };
    copy_text?: string;
    user_id?: string | number;
    request_contact?: boolean;
    style?: string;
    emoji?: string | number;
    same?: boolean;
    [key: string]: unknown;
}

export type GridRow = GridButton[];
export type GridLayout = GridRow[];

export class WaitTimeoutError extends Error {
    constructor(message = "Timeout expired") {
        super(message);
        this.name = "TimeoutError";
    }
}

export class UserCancelledError extends Error {
    constructor(message = "Operation cancelled by user") {
        super(message);
        this.name = "UserCancelled";
    }
}

export function withTimeout<T>(
    promise: Promise<T>,
    timeoutSeconds: number | undefined
): Promise<T> {
    if (timeoutSeconds === undefined || timeoutSeconds === null) {
        return promise;
    }
    return new Promise<T>((resolve, reject) => {
        const timer = setTimeout(
            () => reject(new WaitTimeoutError()),
            timeoutSeconds * 1000
        );
        promise.then(
            (v) => {
                clearTimeout(timer);
                resolve(v);
            },
            (e) => {
                clearTimeout(timer);
                reject(e);
            }
        );
    });
}