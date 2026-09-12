import { Api, TelegramClient } from "teleproto";
import { toId } from "../types";

type Any = any;

export class PreCheckoutQueryEvent {
    client: TelegramClient;
    update: Api.UpdateBotPrecheckoutQuery;

    constructor(client: TelegramClient, update: Api.UpdateBotPrecheckoutQuery) {
        this.client = client;
        this.update = update;
    }

    get query_id(): string {
        return toId(this.update.queryId);
    }

    get id(): string {
        return toId(this.update.queryId);
    }

    get from_user(): Any {
        return {
            id: toId(this.update.userId),
        };
    }

    get user_id(): string {
        return toId(this.update.userId);
    }

    get currency(): string {
        return String(this.update.currency ?? "");
    }

    get total_amount(): number {
        return Number(this.update.totalAmount ?? 0);
    }

    get payload(): string {
        return Buffer.from(this.update.payload as Buffer).toString("utf-8");
    }

    async answer(
        ok: boolean = true,
        options: Any = {}
    ): Promise<Any> {
        const error_message =
            typeof options === "string"
                ? options
                : options.error_message ?? options.error;
        return (this.client as Any).invoke(
            new Api.messages.SetBotPrecheckoutResults({
                queryId: this.update.queryId,
                success: ok,
                error: ok ? undefined : error_message,
            })
        );
    }
}