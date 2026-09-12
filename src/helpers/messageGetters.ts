import { Api, TelegramClient } from "teleproto";
import { toId } from "../types";

type Any = any;

const PATCHED = Symbol("vvip_message_getters_patched");

export interface SuccessfulPaymentView {
    invoice_payload: string;
    total_amount: number;
    telegram_payment_charge_id: string;
    provider_charge_id?: string;
    currency?: string;
}

export class ServicePaymentMessage {
    service: Api.MessageService;
    successful_payment: SuccessfulPaymentView;
    from_user: Any | undefined;
    id: number;

    constructor(
        service: Api.MessageService,
        action: SuccessfulPaymentView,
        from_user: Any,
        id: number
    ) {
        this.service = service;
        this.successful_payment = action;
        this.from_user = from_user;
        this.id = id;
    }

    get message(): string {
        return "";
    }

    get text(): string {
        return "";
    }
}

export function patchMessageGetters(_client: TelegramClient): void {
    const proto = Api.Message.prototype as Any;
    if (proto[PATCHED]) {
        return;
    }
    Object.defineProperty(proto, PATCHED, { value: true });

    Object.defineProperty(proto, "from_user", {
        get(this: Api.Message): Any | undefined {
            const sender = (this as Any).sender;
            if (sender instanceof Api.User || (sender && (sender as Any).className === "User")) {
                return sender;
            }
            return undefined;
        },
        enumerable: true,
    });

    Object.defineProperty(proto, "sender_chat", {
        get(this: Api.Message): Any | undefined {
            const sender = (this as Any).sender;
            if (sender instanceof Api.User || (sender && (sender as Any).className === "User")) {
                return undefined;
            }
            return sender || undefined;
        },
        enumerable: true,
    });

    Object.defineProperty(proto, "caption", {
        get(this: Api.Message): string | undefined {
            return (this as Any).message;
        },
        enumerable: true,
    });

    Object.defineProperty(proto, "command", {
        get(this: Api.Message): string[] {
            const text = ((this as Any).message || "").trim();
            if (!text) {
                return [];
            }
            return text.split(/\s+/);
        },
        enumerable: true,
    });

    Object.defineProperty(proto, "successful_payment", {
        get(this: Api.Message): SuccessfulPaymentView | undefined {
            return undefined;
        },
        enumerable: true,
    });
}

export function successfulPaymentViewFromAction(
    action: Any
): SuccessfulPaymentView | undefined {
    if (action instanceof Api.MessageActionPaymentSentMe) {
        return {
            invoice_payload: Buffer.from(action.payload as Buffer).toString(
                "utf-8"
            ),
            total_amount: Number(action.totalAmount),
            telegram_payment_charge_id: String(
                (action.charge && (action.charge as Any).id) ?? ""
            ),
            provider_charge_id: String(
                (action.charge && (action.charge as Any).providerChargeId) ?? ""
            ),
            currency: String(action.currency ?? ""),
        };
    }
    if (action instanceof Api.MessageActionPaymentSent) {
        return {
            invoice_payload: "",
            total_amount: Number(action.totalAmount),
            telegram_payment_charge_id: "",
            currency: String(action.currency ?? ""),
        };
    }
    return undefined;
}

export function peerUserId(peer: Any): string | undefined {
    if (!peer || typeof peer !== "object") {
        return undefined;
    }
    if (peer instanceof Api.PeerUser) {
        return toId((peer as Any).userId);
    }
    const p = peer as Any;
    if (p.className === "PeerUser") {
        return toId(p.userId);
    }
    return undefined;
}