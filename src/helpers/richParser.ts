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

function _escapeHtml(s: string): string {
    return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function _markdown_to_html(text: string): string {
    const link = /\[([^\]]+)\]\(([^\s)]+)\)/g;
    text = text.replace(link, '<a href="$2">$1</a>');
    const boldItalic = /\*\*\*([^*]+?)\*\*\*/g;
    text = text.replace(boldItalic, "<b><i>$1</i></b>");
    const bold = /\*\*([^*]+?)\*\*/g;
    text = text.replace(bold, "<b>$1</b>");
    const underline = /__([^_]+?)__/g;
    text = text.replace(underline, "<u>$1</u>");
    const italic = /(?<!_)_([^_\n]+?)_(?!_)/g;
    text = text.replace(italic, "<i>$1</i>");
    const strike = /~~([^~]+?)~~/g;
    text = text.replace(strike, "<s>$1</s>");
    const spoiler = /\|\|([^|\n]+?)\|\|/g;
    text = text.replace(spoiler, "<spoiler>$1</spoiler>");
    const expandBlockquote = /^(>>|>\|)\s*(.+)$/gm;
    text = text.replace(
        expandBlockquote,
        (_m, _p: string, line: string) =>
            `<blockquote expandable>${line}</blockquote>`
    );
    const blockquote = /^>\s*(.+)$/gm;
    text = text.replace(
        blockquote,
        (_m, line: string) => `<blockquote>${line}</blockquote>`
    );
    const codeBlock = /```([\w+\-]*?)\n([\s\S]*?)```/g;
    text = text.replace(
        codeBlock,
        (_m, lang: string, code: string) =>
            `<pre><code class="language-${_escapeHtml(lang) || "text"}">${_escapeHtml(
                code.trim()
            )}</code></pre>`
    );
    const code = /`([^`\n]+?)`/g;
    text = text.replace(code, (_m, c: string) => `<code>${_escapeHtml(c)}</code>`);
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