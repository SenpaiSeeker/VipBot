import { Api } from "teleproto";
import { HTMLParser } from "teleproto/extensions/html";
import type { ParseInterface } from "../types";

const EMOJI_TAG_RE = /<emoji id="([0-9]+)">([\s\S]*?)<\/emoji>/g;

export class CustomEmojiParser {
    static _tag = EMOJI_TAG_RE;

    static parseEmoji(text: string): string {
        return text.replace(
            EMOJI_TAG_RE,
            (_match, id: string, inner: string) =>
                `<tg-emoji emoji-id="${id}">${inner}</tg-emoji>`
        );
    }
}

function _markdown_to_html(text: string): string {
    const link = /\[([^\]]+)\]\(([^\s)]+)\)/g;
    text = text.replace(link, '<a href="$2">$1</a>');
    const bold = /\*\*([^*]+?)\*\*/g;
    text = text.replace(bold, "<b>$1</b>");
    const italic = /__([^_]+?)__/g;
    text = text.replace(italic, "<i>$1</i>");
    const strike = /~~([^~]+?)~~/g;
    text = text.replace(strike, "<s>$1</s>");
    const code = /`([^`\n]+?)`/g;
    text = text.replace(code, "<code>$1</code>");
    return text;
}

export const RichParseMode: ParseInterface = {
    parse(message: string): [string, Api.TypeMessageEntity[]] {
        let prepped = message || "";
        prepped = CustomEmojiParser.parseEmoji(prepped);
        prepped = _markdown_to_html(prepped);
        return HTMLParser.parse(prepped);
    },
    unparse(text: string, _entities: Api.TypeMessageEntity[]): string {
        return text;
    },
};