import * as path from "path";
import { TelegramClient, sessions, Api } from "teleproto";

type Any = any;

export class Argument {
    private client: TelegramClient;

    constructor(client: TelegramClient) {
        this.client = client;
    }

    getMention(
        user: Any,
        logs: boolean = false,
        no_tag: boolean = false,
        tag_and_id: boolean = false
    ): string {
        let name = user.firstName || "";
        if (user.lastName) {
            name += ` ${user.lastName}`;
        }
        const uid = (user.id ?? user.id).toString();
        if (logs) {
            return `${name} (${uid})`;
        }
        if (no_tag) {
            return name;
        }
        let mention = `<a href="tg://user?id=${uid}">${name}</a>`;
        if (tag_and_id) {
            mention += ` (<code>${uid}</code>)`;
        }
        return mention;
    }

    async getNamebot(bot_token: string): Promise<Api.User | string> {
        const client = this.client as Any;
        const temp = new TelegramClient(
            new sessions.MemorySession(),
            Number(client.apiId),
            String(client.apiHash),
            {}
        );
        try {
            await temp.start({ botAuthToken: bot_token });
            const me = await temp.getMe();
            await temp.disconnect();
            return me;
        } catch {
            return "Bot token invalid";
        }
    }

    static _slice_args(source_text: string, command_str: string): string {
        try {
            return source_text.slice(command_str.length).trim();
        } catch {
            return "";
        }
    }

    async getMessage(
        message: Any,
        is_arg: boolean = false,
        is_tuple: boolean = false
    ): Promise<{ part1?: string; part2?: string } | Any> {
        const full_text: string = message.message || message.text || "";
        const full_html = full_text;
        const command_parts = full_text.split(/\s+/).filter((p) => p.length > 0);
        let replied: Any | undefined;
        try {
            replied = message.getReplyMessage
                ? await message.getReplyMessage()
                : undefined;
        } catch {
            replied = undefined;
        }

        let replied_text: string | undefined;
        if (replied) {
            replied_text = (replied as Any).message || (replied as Any).caption || undefined;
        }

        if (is_tuple) {
            const part1 = command_parts.length > 1 ? command_parts[1] : undefined;
            let part2: string | undefined;
            if (command_parts.length > 2) {
                part2 = command_parts.slice(2).join(" ").trim() || undefined;
            } else if (replied_text) {
                part2 = replied_text;
            }
            return { part1, part2 };
        }

        if (is_arg) {
            if (command_parts.length > 1) {
                return Argument._slice_args(full_html, command_parts[0]);
            }
            if (replied && replied_text) {
                return replied_text;
            }
            return "";
        }

        if (replied) {
            return replied;
        }

        if (command_parts.length > 1) {
            return Argument._slice_args(full_html, command_parts[0]);
        }

        return "";
    }

    async getReasonAndId(
        message: Any,
        sender_chat: boolean = false
    ): Promise<[string | undefined, string | undefined]> {
        const args = (message.text || "").split(/\s+/).filter((s: string) => s);
        let replied: Any | undefined;
        try {
            replied = message.getReplyMessage
                ? await message.getReplyMessage()
                : undefined;
        } catch {
            replied = undefined;
        }
        let target_id: string | undefined;
        let reason: string | undefined;

        if (replied) {
            let from_user: Any;
            try {
                from_user = await (replied as Any).getSender();
            } catch {
                from_user = undefined;
            }
            if (from_user && from_user.id) {
                target_id = String(from_user.id);
            } else if (sender_chat && (replied as Any).chat && (replied as Any).chat.id) {
                target_id = String((replied as Any).chat.id);
            }
            if (args.length > 1) {
                reason = args.slice(1).join(" ");
            }
        } else if (args.length > 1) {
            try {
                const target_user = await this.client.get_users(args[1]);
                target_id = String((target_user[0] as Any).id);
                if (args.length > 2) {
                    reason = args.slice(2).join(" ");
                }
            } catch {
                return [undefined, undefined];
            }
        }
        return [target_id, reason];
    }
}