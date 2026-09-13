import * as fs from "fs";
import * as path from "path";
import bigInt from "big-integer";
import { Api, TelegramClient } from "teleproto";
import { CustomFile } from "teleproto/client/uploads";
import { CallbackQueryEvent } from "teleproto/events";
import { toId } from "./types";
import { RichParseMode } from "./helpers/richParser";

const _TG_CLIENT_PATCHED = Symbol("vvip_client_patched");

type Any = any;

interface SendMessageOptions {
    parse_mode?: unknown;
    reply_markup?: Any;
    reply_to_message_id?: number | Api.Message;
    disable_web_page_preview?: boolean;
    protect_content?: boolean;
    buttons?: Any;
}

interface MediaOptions {
    caption?: string;
    reply_markup?: Any;
    reply_to_message_id?: number | Api.Message;
    file_name?: string;
    parse_mode?: unknown;
    [key: string]: unknown;
}

function _resolveFile(file: Any, defaultName: string): Any {
    if (typeof file === "string") {
        return file;
    }
    if (Buffer.isBuffer(file)) {
        return new CustomFile(defaultName, file.length, "", file);
    }
    if (file && typeof file === "object" && file.name && file.path) {
        return new CustomFile(String(file.name), fs.statSync(file.path).size, file.path);
    }
    return file;
}

function chatId(id: Any): Any {
    return id;
}

export function patchTelegramClient(_client: TelegramClient): void {
    const proto = TelegramClient.prototype as Any;

    if (!proto._vvip_send_message) {
        proto._vvip_send_message = true;

        proto.send_message = function send_message(
            chat_id: Any,
            text: string,
            options: SendMessageOptions = {}
        ) {
            return this.sendMessage(chatId(chat_id), {
                message: text ?? "",
                parseMode:
                    options.parse_mode === undefined
                        ? RichParseMode
                        : options.parse_mode,
                buttons: options.reply_markup ?? options.buttons,
                replyTo: options.reply_to_message_id ?? undefined,
                linkPreview: !options.disable_web_page_preview,
                noforwards: options.protect_content,
            });
        };

        proto.edit_message_text = function edit_message_text(
            chat_id: Any,
            message_id: Any,
            text: string,
            options: Any = {}
        ) {
            return this.editMessage(chatId(chat_id), {
                message: message_id,
                text: text ?? "",
                parseMode:
                    options.parse_mode === undefined
                        ? RichParseMode
                        : options.parse_mode,
                buttons: options.reply_markup,
            });
        };

        proto.edit_message_caption = proto.edit_message_text;

        proto.send_photo = function send_photo(
            chat_id: Any,
            photo: Any,
            options: MediaOptions = {}
        ) {
            return this.sendFile(chatId(chat_id), {
                file: _resolveFile(photo, "photo.png"),
                caption: options.caption,
                buttons: options.reply_markup,
                replyTo: options.reply_to_message_id ?? undefined,
                parseMode:
                    options.parse_mode === undefined
                        ? RichParseMode
                        : options.parse_mode,
                forceDocument: false,
            });
        };

        proto.send_document = function send_document(
            chat_id: Any,
            document: Any,
            options: MediaOptions = {}
        ) {
            return this.sendFile(chatId(chat_id), {
                file: _resolveFile(document, options.file_name || "file.bin"),
                caption: options.caption,
                buttons: options.reply_markup,
                replyTo: options.reply_to_message_id ?? undefined,
                parseMode:
                    options.parse_mode === undefined
                        ? RichParseMode
                        : options.parse_mode,
                forceDocument: true,
            });
        };

        proto.send_invoice = function send_invoice(
            chat_id: Any,
            options: Any = {}
        ) {
            return sendInvoiceLegacy(this, chat_id, options);
        };

        proto.send_paid_media = function send_paid_media(
            chat_id: Any,
            star_count: Any,
            media: Any,
            options: Any = {}
        ) {
            const entry = Array.isArray(media) ? media[0] : media;
            const file_id = entry?.file_id ?? entry;
            if (this.ns && this.ns.utils && this.ns.utils.log) {
                this.ns.utils.log.print(
                    `${this.ns.utils.log.YELLOW}Paid media tidak didukung, mengirim sebagai media biasa (${star_count} stars).`
                );
            }
            return this.sendFile(chatId(chat_id), {
                file: file_id,
                caption: options.caption,
                buttons: options.reply_markup,
                replyTo: options.reply_to_message_id ?? undefined,
                parseMode:
                    options.parse_mode === undefined
                        ? RichParseMode
                        : options.parse_mode,
                forceDocument: false,
            });
        };

        proto.answer_pre_checkout_query = function answer_pre_checkout_query(
            query_id: Any,
            ok = true,
            options: Any = {}
        ) {
            return this.invoke(
                new Api.messages.SetBotPrecheckoutResults({
                    queryId: query_id,
                    success: ok,
                    error: ok ? undefined : options.error_message,
                })
            );
        };

        proto.get_users = function get_users(ids: Any) {
            const list = Array.isArray(ids) ? ids : [ids];
            return Promise.all(
                list.map((id: Any) => this.getEntity(toId(id)))
            );
        };

        proto.resolve_peer = proto.getInputEntity;

        proto.get_chat = function get_chat(e: Any) {
            return this.getEntity(e);
        };

        proto.get_messages = function get_messages(
            chat_id: Any,
            message_id: Any
        ) {
            return this.getMessages(chatId(chat_id), {
                ids: [message_id],
            });
        };

        proto.delete_messages = function delete_messages(
            chat_id: Any,
            ids: Any[],
            revoke = true
        ) {
            return this.deleteMessages(chatId(chat_id), ids, { revoke });
        };

        proto.ban_chat_member = function ban_chat_member(
            chat_id: Any,
            user_id: Any
        ) {
            return this.kickParticipant(chatId(chat_id), toId(user_id));
        };

        proto.unban_chat_member = function unban_chat_member(
            chat_id: Any,
            user_id: Any
        ) {
            return this.editBanned(chatId(chat_id), toId(user_id), {
                viewMessages: false,
            } as Any);
        };

        proto.get_chat_member = async function get_chat_member(
            chat_id: Any,
            user_id: Any
        ) {
            const inputPeer = await this.getInputEntity(chatId(chat_id));
            if (inputPeer instanceof Api.InputPeerChannel) {
                return this.getParticipant(inputPeer, toId(user_id));
            }
            const users = await this.getParticipants(inputPeer, {
                filter: new Api.ChannelParticipantsSearch({ q: toId(user_id) }),
            });
            return users[0];
        };

        proto.create_chat_invite_link = function create_chat_invite_link(
            chat_id: Any,
            options: Any = {}
        ) {
            return this.exportChatInvite(chatId(chat_id), {
                expireDate: options.expire_date
                    ? Math.floor(options.expire_date / 1000)
                    : 0,
                usageLimit: options.member_limit ?? 0,
                title: options.title,
            });
        };

        proto.export_chat_invite_link = function export_chat_invite_link(
            chat_id: Any
        ) {
            return this.exportChatInvite(chatId(chat_id), {
                expireDate: 0,
                usageLimit: 0,
            } as Any);
        };

        proto.get_chat_members = async function get_chat_members(chat_id: Any) {
            const inputPeer = await this.getInputEntity(chatId(chat_id));
            const users = await this.getParticipants(inputPeer, {
                filter: new Api.ChannelParticipantsRecent() as Any,
            } as Any);
            const members = (users as Any[]).map((u) => ({
                user: u,
                status: {
                    name: u && u.bot ? "MemberStatusRestricted" : "MemberStatusMember",
                },
            }));
            return members;
        };

        proto.download_media = async function download_media(
            message: Any,
            file_path?: string
        ) {
            const target = message instanceof Api.Message ? message : message.message;
            const out =
                file_path ??
                path.join(
                    "temp_media",
                    `media_${Date.now()}_${Math.floor(Math.random() * 1e6)}`
                );
            const result = await this.downloadMedia(target, out);
            return result === undefined ? out : result;
        };

        proto.send_star_gift_raw = function send_star_gift_raw(
            user_id: Any,
            gift_id: number
        ) {
            return sendStarsGift(this, user_id, gift_id);
        };

        proto.refund_star_payment = async function refund_star_payment(options: {
            user_id: Any;
            telegram_payment_charge_id: Any;
        }) {
            const userId = await this.getInputEntity(toId(options.user_id));
            return this.invoke(
                new Api.payments.RefundStarsCharge({
                    userId,
                    chargeId: String(options.telegram_payment_charge_id),
                } as Any)
            );
        };

        proto.get_available_gifts = async function get_available_gifts() {
            const res = await this.invoke(
                new Api.payments.GetStarGifts({ hash: 0 } as Any)
            );
            return res.gifts;
        };
    }

    const msgProto = Api.Message.prototype as Any;
    if (!msgProto._vvip_reply_photo) {
        msgProto._vvip_reply_photo = true;
        msgProto.reply_text = function reply_text(
            text: string,
            options: SendMessageOptions = {}
        ) {
            return this.reply({
                message: text ?? "",
                parseMode:
                    options.parse_mode === undefined
                        ? RichParseMode
                        : options.parse_mode,
                buttons: options.reply_markup ?? options.buttons,
                linkPreview: !options.disable_web_page_preview,
                noforwards: options.protect_content,
            });
        };
        msgProto.edit_text = function edit_text(
            text: string,
            options: Any = {}
        ) {
            return this.edit({
                text: text ?? "",
                parseMode:
                    options.parse_mode === undefined
                        ? RichParseMode
                        : options.parse_mode,
                buttons: options.reply_markup,
            });
        };
        msgProto.edit_caption = msgProto.edit_text;
        msgProto.reply_photo = async function reply_photo(
            photo: Any,
            options: MediaOptions = {}
        ) {
            const client = (this as Any)._client;
            const chat = await this.getInputChat();
            return client.send_photo(chat, photo, {
                ...options,
                reply_to_message_id: (this as Any).id,
            });
        };
        msgProto.reply_document = async function reply_document(
            document: Any,
            options: MediaOptions = {}
        ) {
            const client = (this as Any)._client;
            const chat = await this.getInputChat();
            return client.send_document(chat, document, {
                ...options,
                reply_to_message_id: (this as Any).id,
            });
        };
        msgProto.copy = async function copy(
            chat_id: Any,
            caption?: string,
            reply_markup?: Any
        ) {
            const client = (this as Any)._client as TelegramClient;
            const peer = await client.getInputEntity(chatId(chat_id));
            const msg = this as Any;
            const randomId = bigInt(Math.floor(Math.random() * 2 ** 31) - 2 ** 30);
            const text = caption ?? msg.message ?? "";
            if (msg.media) {
                let inputMedia: Any;
                if (
                    msg.media.photo &&
                    msg.media.photo.id &&
                    msg.media.photo.className === "Photo"
                ) {
                    const photo = msg.media.photo as Any;
                    inputMedia = new Api.InputMediaPhoto({
                        id: new Api.InputPhoto({
                            id: photo.id,
                            accessHash: photo.accessHash,
                            fileReference: photo.fileReference,
                        }),
                        caption: text,
                    } as Any);
                } else if (
                    msg.media.document &&
                    msg.media.document.className === "Document"
                ) {
                    const doc = msg.media.document as Any;
                    inputMedia = new Api.InputMediaDocument({
                        id: new Api.InputDocument({
                            id: doc.id,
                            accessHash: doc.accessHash,
                            fileReference: doc.fileReference,
                        }),
                        caption: text,
                    } as Any);
                }
                if (inputMedia) {
                    const result = await client.invoke(
                        new Api.messages.SendMedia({
                            peer,
                            media: inputMedia,
                            replyMarkup: reply_markup,
                            message: "",
                            randomId,
                        } as Any)
                    );
                    return result;
                }
            }
            return client.sendMessage(peer, {
                message: text ?? "",
                parseMode: RichParseMode,
                replyMarkup: reply_markup,
            } as Any);
        };
    }

    const cbProto = CallbackQueryEvent.prototype as Any;
    if (!cbProto._vvip_patched) {
        cbProto._vvip_patched = true;
        const origAnswer = CallbackQueryEvent.prototype.answer;
        cbProto.answer = function answer(
            text?: string | { message?: string; show_alert?: boolean; url?: string; cache_time?: number },
            options: Any = {}
        ) {
            if (typeof text === "object" && text !== null) {
                const o = text;
                return origAnswer.call(this, {
                    message: o.message,
                    cacheTime: o.cache_time,
                    url: o.url,
                    alert: o.show_alert,
                });
            }
            return origAnswer.call(this, {
                message: text,
                alert: options.show_alert,
                cacheTime: options.cache_time,
            });
        };
        cbProto.edit_message_text = function edit_message_text(
            text: string,
            options: Any = {}
        ) {
            return this.edit({
                message: this.messageId,
                text: text ?? "",
                parseMode:
                    options.parse_mode === undefined
                        ? RichParseMode
                        : options.parse_mode,
                buttons: options.reply_markup,
            });
        };
        cbProto.edit_message_caption = cbProto.edit_message_text;
        cbProto.edit_message_reply_markup = function edit_message_reply_markup(
            rt: Any = undefined
        ) {
            return this.edit({ buttons: rt ?? [] });
        };
        Object.defineProperty(cbProto, "message", {
            get(this: Any) {
                if (this._vvipMessage) {
                    return this._vvipMessage;
                }
                return undefined;
            },
            enumerable: true,
        });
        Object.defineProperty(cbProto, "from_user", {
            get(this: Any) {
                if (this._vvipFromUser) {
                    return this._vvipFromUser;
                }
                const sender = this.sender;
                if (sender instanceof Api.User || (sender && sender.className === "User")) {
                    return sender;
                }
                return undefined;
            },
            enumerable: true,
        });
        Object.defineProperty(cbProto, "data_string", {
            get(this: Any) {
                const data = this.data;
                if (typeof data === "string") {
                    return data;
                }
                if (Buffer.isBuffer(data)) {
                    return Buffer.from(data).toString("utf-8");
                }
                return String(data ?? "");
            },
            enumerable: true,
        });
    }

    const userProto = Api.User.prototype as Any;
    if (!userProto._vvip_mention) {
        userProto._vvip_mention = true;
        Object.defineProperty(userProto, "mention", {
            get(this: Any) {
                if (this.username) {
                    return `@${this.username}`;
                }
                return this.firstName ?? "";
            },
            enumerable: true,
        });
    }

    if (!proto._vvip_me_getter) {
        proto._vvip_me_getter = true;
        Object.defineProperty(proto, "me", {
            get(this: Any) {
                return this._vvip_me;
            },
            enumerable: true,
        });
        proto.get_me = function get_me() {
            return this.getMe();
        };
        if (!proto._vvip_is_connected) {
            proto._vvip_is_connected = true;
            Object.defineProperty(proto, "is_connected", {
                get(this: Any) {
                    try {
                        const sender = this._sender;
                        if (!sender) {
                            return false;
                        }
                        const lifecycle = sender.lifecycle;
                        return (
                            lifecycle === "connected" ||
                            lifecycle === "reconnecting"
                        );
                    } catch {
                        return false;
                    }
                },
                enumerable: true,
            });
        }
        Object.defineProperty(proto, "services", {
            get(this: Any) {
                if (!this._vvip_services) {
                    this._vvip_services = {};
                }
                return this._vvip_services;
            },
            enumerable: true,
        });
    }
}

async function sendInvoiceLegacy(
    client: TelegramClient,
    chat_id: Any,
    options: Any
): Promise<Any> {
    const inputPeer = await client.getInputEntity(chatId(chat_id));
    return client.invoke(
        new Api.messages.SendMedia({
            peer: inputPeer,
            media: new Api.InputMediaInvoice({
                title: options.title ?? "",
                description: options.description ?? "",
                invoice: new Api.Invoice({
                    currency: options.currency ?? "XTR",
                    prices: (options.prices ?? []).map(
                        (p: Any) =>
                            new Api.LabeledPrice({
                                label: p.label ?? "",
                                amount: p.amount ?? 0,
                            })
                    ),
                    test: false,
                    nameRequested: false,
                    phoneRequested: false,
                    emailRequested: false,
                    shippingAddressRequested: false,
                    flexible: false,
                }),
                payload: Buffer.from(options.payload ?? "", "utf-8"),
                providerData: new Api.DataJSON({ data: "{}" }),
            }),
            message: "",
            randomId: bigInt(
                Math.floor(Math.random() * 2 ** 31)
            ).toString(),
        } as Any)
    );
}

async function sendStarsGift(
    client: TelegramClient,
    user_id: Any,
    gift_id: number
): Promise<Any> {
    const peer = await client.getInputEntity(toId(user_id));
    const invoice = new Api.InputInvoiceStarGift({
        peer,
        giftId: gift_id,
    } as Any);
    const paymentForm = await client.invoke(
        new Api.payments.GetPaymentForm({
            invoice,
        } as Any)
    );
    return client.invoke(
        new Api.payments.SendStarsForm({
            formId: paymentForm.formId,
            invoice,
        } as Any)
    );
}