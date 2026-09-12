import type { TelegramClient } from "teleproto";
import type { CallbackQueryEvent } from "teleproto/events";
import type { CustomMessage } from "teleproto/client/tl";
import { Api } from "teleproto";

type Any = any;

declare module "teleproto" {
    namespace Api {
        interface User {
            mention: string;
        }
        interface Message {
            reply_text(text: string, options?: Any): Promise<Any>;
            edit_text(text: string, options?: Any): Promise<Any>;
            edit_caption(text: string, options?: Any): Promise<Any>;
            reply_photo(photo: Any, options?: Any): Promise<Any>;
            reply_document(document: Any, options?: Any): Promise<Any>;
            copy(chat_id: Any, caption?: string, reply_markup?: Any): Promise<Any>;
        }
    }
}

declare module "teleproto/events" {
    interface CallbackQueryEvent {
        answer(
            text?: string | { message?: string; show_alert?: boolean; url?: string; cache_time?: number },
            options?: Any
        ): Promise<Any>;
        edit_message_text(text: string, options?: Any): Promise<Any>;
        edit_message_caption(text: string, options?: Any): Promise<Any>;
        edit_message_reply_markup(rt?: Any): Promise<Any>;
        message: CustomMessage | undefined;
        from_user: Api.User | undefined;
        data_string: string;
        _vvipMessage?: CustomMessage;
        _vvipFromUser?: Api.User;
    }
}

declare module "teleproto/client/tl" {
    interface CustomMessage {
        reply_text(text: string, options?: Any): Promise<Any>;
        edit_text(text: string, options?: Any): Promise<Any>;
        edit_caption(text: string, options?: Any): Promise<Any>;
        reply_photo(photo: Any, options?: Any): Promise<Any>;
        reply_document(document: Any, options?: Any): Promise<Any>;
        successful_payment?: Any;
        from_user?: Any;
        sender_chat?: Any;
    }
}

declare module "teleproto" {
    interface TelegramClient {
        ns: Any;
        services: Any;
        me: Api.User;
        get_me(): Promise<Api.User>;
        is_connected: boolean;
        _vvip_me: Api.User;
        apiId: string | number;
        apiHash: string;
        listen(chat_id: Any, timeout?: number): Promise<CustomMessage>;
        ask(chat_id: Any, text: string, timeout?: number, options?: Any): Promise<CustomMessage>;
        cancel(chat_id: Any): void;
        send_message(chat_id: Any, text: string, options?: Any): Promise<CustomMessage>;
        edit_message_text(chat_id: Any, message_id: Any, text: string, options?: Any): Promise<Any>;
        edit_message_caption(chat_id: Any, message_id: Any, text: string, options?: Any): Promise<Any>;
        send_photo(chat_id: Any, photo: Any, options?: Any): Promise<CustomMessage>;
        send_document(chat_id: Any, document: Any, options?: Any): Promise<CustomMessage>;
        send_invoice(chat_id: Any, options?: Any): Promise<Any>;
        send_paid_media(chat_id: Any, star_count: number, media: Any, options?: Any): Promise<Any>;
        answer_pre_checkout_query(query_id: Any, ok?: boolean, options?: Any): Promise<Any>;
        get_users(ids: Any): Promise<Api.TypeUser[]>;
        resolve_peer(e: Any): Promise<Any>;
        get_chat(e: Any): Promise<Any>;
        get_messages(chat_id: Any, message_id: Any): Promise<CustomMessage[]>;
        delete_messages(chat_id: Any, ids: Any[], revoke?: boolean): Promise<Any>;
        ban_chat_member(chat_id: Any, user_id: Any): Promise<Any>;
        unban_chat_member(chat_id: Any, user_id: Any): Promise<Any>;
        get_chat_member(chat_id: Any, user_id: Any): Promise<Any>;
        get_chat_members(chat_id: Any): Promise<Any[]>;
        create_chat_invite_link(chat_id: Any, options?: Any): Promise<Any>;
        export_chat_invite_link(chat_id: Any): Promise<Any>;
        download_media(message: Any, file_path?: string): Promise<string>;
        send_star_gift_raw(user_id: Any, gift_id: number): Promise<Any>;
        get_available_gifts(): Promise<Any[]>;
        refund_star_payment(options: { user_id: Any; telegram_payment_charge_id: Any }): Promise<Any>;
    }
}