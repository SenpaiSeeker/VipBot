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

function _apply_blockquote(text: string): string {
    const lines = text.split("\n");
    const out: string[] = [];
    let i = 0;

    while (i < lines.length) {
        const m = /^(>+)[ \t]?(.*)$/.exec(lines[i]);
        if (!m) {
            out.push(lines[i]);
            i++;
            continue;
        }

        let expandable = false;
        const parts: string[] = [];
        while (i < lines.length) {
            const mm = /^(>+)[ \t]?(.*)$/.exec(lines[i]);
            if (!mm) break;
            if (mm[1].length >= 3) {
                expandable = true;
            }
            parts.push(mm[2]);
            i++;
        }

        const attr = expandable ? " expandable" : "";
        out.push(`<blockquote${attr}>${parts.join("\n")}</blockquote>`);
    }

    return out.join("\n");
}

function _apply_headings(text: string): string {
    return text.replace(
        /^#{1,6}\s+(.*)$/gm,
        (m, h: string) => `<b>${h}</b>`
    );
}

function _markdown_to_html(text: string): string {
    const blocks: string[] = [];
    text = text.replace(
        /```([\w+\-]*?)\n([\s\S]*?)```/g,
        (_m, lang: string, code: string) => {
            blocks.push(`\u0000BLK\u0000${lang}\u0000${code}\u0000`);
            return `\u0000IDX${blocks.length - 1}\u0000`;
        }
    );

    text = _apply_headings(text);
    text = _apply_blockquote(text);

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
    const code = /`([^`\n]+?)`/g;
    text = text.replace(code, (_m, c: string) => `<code>${_escapeHtml(c)}</code>`);

    text = text.replace(/\u0000IDX(\d+)\u0000/g, (_m, idx: string) => {
        const raw = blocks[Number(idx)] || "";
        const parts = raw.split("\u0000");
        const lang = parts[2] || "";
        const code = parts.slice(3, -1).join("\u0000");
        return `<pre><code class="language-${_escapeHtml(lang) || "text"}">${_escapeHtml(
            code.trim()
        )}</code></pre>`;
    });

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