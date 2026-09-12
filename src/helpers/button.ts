import bigInt from "big-integer";
import { Api } from "teleproto";
import type { GridButton, GridLayout } from "../types";

export type ButtonLike = Api.TypeKeyboardInlineButton | Api.KeyboardButton;

const URL_PATTERN = /(?:https?:\/\/)?(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:[/?]\S+)?|tg:\/\/\S+$/;
const INLINE_PATTERN = /\| ([^|]+) - ([^|]+) \|/g;
const REPLY_PATTERN = /\|\s*([^\|]+?)\s*\|/g;

function _styleObject(style?: string, emojiVal?: string | number): Api.KeyboardButtonStyle | undefined {
    const opts: { bgDanger?: boolean; bgPrimary?: boolean; bgSuccess?: boolean; icon?: any } = {};
    if (style === "red") opts.bgDanger = true;
    else if (style === "blue") opts.bgPrimary = true;
    else if (style === "green") opts.bgSuccess = true;
    if (emojiVal !== undefined && emojiVal !== null) {
        opts.icon = bigInt(String(emojiVal));
    }
    if (!opts.bgDanger && !opts.bgPrimary && !opts.bgSuccess && !opts.icon) {
        return undefined;
    }
    return new Api.KeyboardButtonStyle(opts);
}

function _toStyleLike(style?: string, emojiVal?: string | number): Api.KeyboardButtonStyle | undefined {
    return _styleObject(style, emojiVal);
}

export class Button {
    URL_PATTERN = URL_PATTERN;
    INLINE_PATTERN = INLINE_PATTERN;
    REPLY_PATTERN = REPLY_PATTERN;

    get_urls(text: string): string[] {
        return text.match(URL_PATTERN) ?? [];
    }

    parse_buttons_and_text(
        text: string,
        mode = "inline"
    ): [Array<[string, string[]]>, string] {
        if (mode === "inline") {
            const buttonData: Array<[string, string[]]> = [];
            let match: RegExpExecArray | null;
            const re = new RegExp(INLINE_PATTERN.source);
            while ((match = re.exec(text))) {
                buttonData.push([match[1], [match[2]]]);
            }
            let extractedText: string;
            if (text.includes("|")) {
                extractedText = text.split(INLINE_PATTERN)[0].trim();
            } else {
                extractedText = text.trim();
            }
            return [buttonData, extractedText];
        }
        if (mode === "reply") {
            const rawData: string[] = [];
            let match: RegExpExecArray | null;
            const re = new RegExp(REPLY_PATTERN.source);
            while ((match = re.exec(text))) {
                rawData.push(match[1]);
            }
            const extractedText = text.replace(REPLY_PATTERN, "").trim();
            const buttons: Array<[string, string[]]> = [];
            for (const chunk of rawData) {
                for (const part of chunk.split("-")) {
                    if (part.includes(";")) {
                        const [label, ...params] = part.split(";");
                        buttons.push([
                            label.trim().replace(/\]$/, ""),
                            params.map((p) => p.trim()),
                        ]);
                    } else {
                        buttons.push([part.trim().replace(/\]$/, ""), []]);
                    }
                }
            }
            return [buttons, extractedText];
        }
        throw new Error("Invalid parse mode. Use 'inline' or 'reply'.");
    }

    create_inline_keyboard(
        text: string,
        inline_cmd?: string,
        is_id?: boolean,
        cb_prefix?: string
    ): [Api.TypeReplyMarkup, string] {
        const layout: ButtonLike[][] = [];
        const [buttons, remainingText] = this.parse_buttons_and_text(text, "inline");
        for (const [label, payloadArr] of buttons) {
            const payload = payloadArr[0] ?? "";
            const [cbDataRaw, ...extraParams] = payload.split(";");
            let cbData = cbDataRaw;
            const isUrl = Boolean(this.get_urls(cbData)) && !extraParams.includes("webapp");
            const isCopy = extraParams.includes("copy");
            const isUser = extraParams.includes("user");
            const isWebapp = extraParams.includes("webapp");
            if (!(isUrl || isCopy || isUser || isWebapp)) {
                if (cb_prefix) {
                    cbData = `${cb_prefix}_${cbData}`;
                } else if (inline_cmd && is_id) {
                    cbData = `${inline_cmd} ${is_id}_${cbData}`;
                } else if (inline_cmd) {
                    cbData = `${inline_cmd} ${cbData}`;
                }
            }
            let style: string | undefined;
            let emojiVal: string | number | undefined;
            for (let param of extraParams) {
                param = param.trim();
                if (param.startsWith("style=")) {
                    style = param.split("=")[1].toLowerCase();
                } else if (param.startsWith("emoji=")) {
                    emojiVal = this._custom_emoji_id(param.split("=")[1]);
                }
            }
            const styleLike = _toStyleLike(style, emojiVal);
            let button: ButtonLike;
            if (isUser) {
                button = Button.userProfile(label, cbData, styleLike);
            } else if (isCopy) {
                button = Button.copy(label, cbData, styleLike);
            } else if (isWebapp) {
                button = Button.webView(label, cbData, styleLike);
            } else if (isUrl) {
                button = Button.url(label, cbData, styleLike);
            } else {
                button = Button.inline(label, cbData, styleLike);
            }
            if (extraParams.includes("same") && layout.length) {
                layout[layout.length - 1].push(button);
            } else {
                layout.push([button]);
            }
        }
        return [Button.toMarkup(layout), remainingText];
    }

    create_button_keyboard(text: string): [Api.TypeReplyMarkup, string] {
        const layout: ButtonLike[][] = [];
        const [buttons, remainingText] = this.parse_buttons_and_text(text, "reply");
        for (const [label, params] of buttons) {
            const button = params.includes("is_contact")
                ? new Api.KeyboardButton({
                      text: label,
                      type: new Api.ButtonTypeRequestPhone(),
                  })
                : new Api.KeyboardButton({
                      text: label,
                      type: new Api.ButtonTypeDefault(),
                  });
            if (params.includes("same") && layout.length) {
                layout[layout.length - 1].push(button);
            } else {
                layout.push([button]);
            }
        }
        return [Button.toReplyMarkup(layout), remainingText];
    }

    remove_reply_keyboard(selective = false): Api.TypeReplyMarkup {
        return new Api.ReplyKeyboardHide({ selective });
    }

    build_button_grid(layout: GridLayout): Api.TypeReplyMarkup | undefined {
        const keyboard: ButtonLike[][] = [];
        for (const rowData of layout) {
            const row: ButtonLike[] = [];
            for (const buttonInfo of rowData) {
                const opts: GridButton = { ...buttonInfo };
                let style: string | undefined;
                if (typeof opts.style === "string") {
                    style = opts.style.toLowerCase();
                }
                let emojiVal: string | number | undefined;
                if (opts.emoji !== undefined) {
                    emojiVal = this._custom_emoji_id(opts.emoji);
                }
                const styleLike = _toStyleLike(style, emojiVal);
                let button: ButtonLike;
                if ("web_app" in opts) {
                    const url = typeof opts.web_app === "string" ? opts.web_app : opts.web_app?.url;
                    button = Button.webView(opts.text, url ?? "", styleLike);
                } else if ("copy_text" in opts && opts.copy_text) {
                    button = Button.copy(opts.text, opts.copy_text, styleLike);
                } else if ("user_id" in opts && opts.user_id != null) {
                    button = Button.userProfile(opts.text, String(opts.user_id), styleLike);
                } else if ("url" in opts && opts.url) {
                    button = Button.url(opts.text, opts.url, styleLike);
                } else {
                    button = Button.inline(
                        opts.text,
                        opts.callback_data ?? opts.text,
                        styleLike
                    );
                }
                row.push(button);
            }
            if (row.length) {
                keyboard.push(row);
            }
        }
        if (!keyboard.length) {
            return undefined;
        }
        return new Api.ReplyInlineMarkup({
            rows: keyboard.map(
                (buttons) =>
                    new Api.KeyboardInlineButtonRow({
                        buttons: buttons as Api.TypeKeyboardInlineButton[],
                    })
            ),
        });
    }

    static row(buttons: ButtonLike[]): Api.KeyboardInlineButtonRow {
        return new Api.KeyboardInlineButtonRow({
            buttons: buttons as Api.TypeKeyboardInlineButton[],
        });
    }

    static toMarkup(layout: ButtonLike[][]): Api.TypeReplyMarkup {
        return new Api.ReplyInlineMarkup({
            rows: layout.map((buttons) =>
                Button.row(buttons)
            ),
        });
    }

    static toReplyMarkup(layout: ButtonLike[][]): Api.TypeReplyMarkup {
        return new Api.ReplyKeyboardMarkup({
            rows: layout.map(
                (buttons) =>
                    new Api.KeyboardButtonRow({
                        buttons: buttons as Api.KeyboardButton[],
                    })
            ),
            resize: true,
        });
    }

    static inline(
        text: string,
        data: string | Buffer,
        style?: Api.KeyboardButtonStyle
    ): Api.KeyboardInlineButton {
        const buf = Buffer.isBuffer(data) ? data : Buffer.from(data, "utf-8");
        return new Api.KeyboardInlineButton({
            text,
            type: new Api.InlineButtonTypeCallback({ data: buf }),
            style,
        });
    }

    static url(
        text: string,
        url: string,
        style?: Api.KeyboardButtonStyle
    ): Api.KeyboardInlineButton {
        return new Api.KeyboardInlineButton({
            text,
            type: new Api.InlineButtonTypeUrl({ url }),
            style,
        });
    }

    static webView(
        text: string,
        url: string,
        style?: Api.KeyboardButtonStyle
    ): Api.KeyboardInlineButton {
        return new Api.KeyboardInlineButton({
            text,
            type: new Api.InlineButtonTypeWebView({ url }),
            style,
        });
    }

    static copy(
        text: string,
        copyText: string,
        style?: Api.KeyboardButtonStyle
    ): Api.KeyboardInlineButton {
        return new Api.KeyboardInlineButton({
            text,
            type: new Api.InlineButtonTypeCopy({ copyText }),
            style,
        });
    }

    static userProfile(
        text: string,
        userId: string | number,
        style?: Api.KeyboardButtonStyle
    ): Api.KeyboardInlineButton {
        return new Api.KeyboardInlineButton({
            text,
            type: new Api.InputInlineButtonTypeUserProfile({
                userId: bigInt(String(userId)) as any,
            }) as any,
            style,
        });
    }

    _custom_emoji_id(value: unknown): string | number {
        const n = Number(value);
        if (Number.isFinite(n) && String(value).trim() !== "") {
            return n;
        }
        return String(value);
    }
}