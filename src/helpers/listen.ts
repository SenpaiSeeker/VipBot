import { Api, TelegramClient, client as tpClient } from "teleproto";
import { NewMessage } from "teleproto/events";
import { toId, WaitTimeoutError, UserCancelledError } from "../types";

type Any = any;

interface ConversationEntry {
    resolve: (msg: Api.Message) => void;
    timer?: NodeJS.Timeout;
    done: () => void;
}

const CONVERSATIONS = Symbol("vvip_conversations");
const PATCHED = Symbol("vvip_listen_patched");
const RESOLVER_INSTALLED = Symbol("vvip_listen_resolver_installed");
const StopPropagation = tpClient.updates.StopPropagation;

export function patchListen(): void {
    const proto = TelegramClient.prototype as Any;
    if (proto[PATCHED]) {
        return;
    }
    proto[PATCHED] = true;

    proto.listen = function listen(
        chat_id: Any,
        timeout?: number
    ): Promise<Api.Message> {
        return doListen(this, chat_id, timeout);
    };

    proto.ask = function ask(
        chat_id: Any,
        text: string,
        timeout?: number,
        options: Any = {}
    ): Promise<Api.Message> {
        const self = this;
        return (async () => {
            const request = await self.send_message(chat_id, text, options);
            const response = await doListen(self, chat_id, timeout);
            (response as Any).request = request;
            return response;
        })();
    };

    proto.cancel = function cancel(chat_id: Any) {
        const map = (this as Any)[CONVERSATIONS] as
            | Map<string, ConversationEntry>
            | undefined;
        const key = toId(chat_id);
        if (!map) {
            return;
        }
        const entry = map.get(key);
        if (entry) {
            entry.done();
        }
    };
}

async function doListen(
    client: TelegramClient,
    chat_id: Any,
    timeout?: number
): Promise<Api.Message> {
    let id: string;
    if (typeof chat_id === "number" || /^\d+$/.test(String(chat_id))) {
        id = toId(chat_id);
    } else {
        const chat = await client.get_chat(chat_id);
        id = toId((chat as Any).id);
    }

    const map: Map<string, ConversationEntry> =
        (client as Any)[CONVERSATIONS] ??
        ((client as Any)[CONVERSATIONS] = new Map());

    if (map.has(id)) {
        throw new Error(`Already listening in chat ${id}`);
    }

    return new Promise<Api.Message>((resolve, reject) => {
        let settled = false;
        const cleanup = () => {
            if (settled) {
                return;
            }
            settled = true;
            if (entry.timer) {
                clearTimeout(entry.timer);
            }
            const current = map.get(id);
            if (current === entry) {
                map.delete(id);
            }
        };

        const entry: ConversationEntry = {
            resolve: (msg) => {
                cleanup();
                resolve(msg);
            },
            timer: undefined,
            done: () => {
                cleanup();
                reject(new UserCancelledError());
            },
        };

        if (timeout !== undefined && timeout !== null) {
            entry.timer = setTimeout(() => {
                cleanup();
                reject(new WaitTimeoutError());
            }, Number(timeout) * 1000);
        }

        map.set(id, entry);
        ensureResolver(client);
    });
}

function ensureResolver(client: TelegramClient): void {
    if ((client as Any)[RESOLVER_INSTALLED]) {
        return;
    }
    (client as Any)[RESOLVER_INSTALLED] = true;
    const handler = (event: Any) => {
        const map = (client as Any)[CONVERSATIONS] as
            | Map<string, ConversationEntry>
            | undefined;
        if (!map || map.size === 0) {
            return;
        }
        if (event && event.message) {
            const msg: Api.Message = event.message;
            const chatId = (msg as Any).chatId
                ? toId((msg as Any).chatId)
                : undefined;
            if (!chatId) {
                return;
            }
            const entry = map.get(chatId);
            if (entry) {
                entry.resolve(msg);
                throw new StopPropagation();
            }
        }
    };
    client.addEventHandler(handler, new NewMessage({}));
}