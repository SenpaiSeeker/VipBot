import { Api } from "teleproto";

type Entity = Api.TypeMessageEntity;

function escapeHtml(s: string): string {
    return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

export function entitiesToHtml(
    text: string,
    entities: Entity[] | undefined
): string {
    if (!entities || !entities.length) {
        return escapeHtml(text);
    }

    const len = text.length;

    const tags: [number, string][] = [];
    const closes: [number, string][] = [];

    for (const e of entities) {
        const s = e.offset;
        const l = e.length;
        if (s >= len || l <= 0) continue;

        const slice = text.slice(s, s + l);

        const cls = (e as any).className as string;

        if (cls === "MessageEntityBold") {
            tags.push([s, "<b>"]);
            closes.push([s + l, "</b>"]);
        } else if (cls === "MessageEntityItalic") {
            tags.push([s, "<i>"]);
            closes.push([s + l, "</i>"]);
        } else if (cls === "MessageEntityUnderline") {
            tags.push([s, "<u>"]);
            closes.push([s + l, "</u>"]);
        } else if (cls === "MessageEntityStrike") {
            tags.push([s, "<s>"]);
            closes.push([s + l, "</s>"]);
        } else if (cls === "MessageEntityCode") {
            tags.push([s, "<code>"]);
            closes.push([s + l, "</code>"]);
        } else if (cls === "MessageEntityPre") {
            const lang =
                "language" in e && typeof e.language === "string"
                    ? e.language
                    : "";
            tags.push([s, `<pre${lang ? ` language="${escapeHtml(lang)}"` : ""}>`]);
            closes.push([s + l, "</pre>"]);
        } else if (cls === "MessageEntitySpoiler") {
            tags.push([s, "<spoiler>"]);
            closes.push([s + l, "</spoiler>"]);
        } else if (cls === "MessageEntityBlockquote") {
            const expandable = (e as any).collapsed === true;
            const attr = expandable ? ' expandable' : '';
            tags.push([s, `<blockquote${attr}>`]);
            closes.push([s + l, "</blockquote>"]);
        } else if (cls === "MessageEntityTextUrl") {
            const url =
                "url" in e && typeof e.url === "string"
                    ? e.url
                    : "#";
            tags.push([s, `<a href="${escapeHtml(url)}">`]);
            closes.push([s + l, "</a>"]);
        } else if (cls === "MessageEntityMention") {
            tags.push([s, `<a href="tg://user?id=${escapeHtml(slice)}">`]);
            closes.push([s + l, "</a>"]);
        } else if (cls === "MessageEntityCustomEmoji") {
            const emojiId =
                "documentId" in e
                    ? String((e as any).documentId)
                    : "";
            tags.push([s, `<tg-emoji emoji-id="${emojiId}">`]);
            closes.push([s + l, "</tg-emoji>"]);
        } else if (cls === "MessageEntityMentionName") {
            const userId =
                "userId" in e ? String((e as any).userId) : "";
            tags.push([s, `<a href="tg://user?id=${escapeHtml(userId)}">`]);
            closes.push([s + l, "</a>"]);
        }
    }

    const events: [number, "open" | "close", string][] = [];
    for (const [pos, tag] of tags) events.push([pos, "open", tag]);
    for (const [pos, tag] of closes) events.push([pos, "close", tag]);

    events.sort((a, b) => {
        if (a[0] !== b[0]) return a[0] - b[0];
        return a[1] === "close" ? -1 : 1;
    });

    let result = "";
    let cursor = 0;

    for (const [pos, type, tag] of events) {
        if (pos > cursor && pos <= len) {
            result += escapeHtml(text.slice(cursor, pos));
            cursor = pos;
        }
        result += tag;
    }

    if (cursor < len) {
        result += escapeHtml(text.slice(cursor));
    }

    return result;
}

export function entitiesToMarkdown(
    text: string,
    entities: Entity[] | undefined
): string {
    if (!entities || !entities.length) {
        return text;
    }

    const len = text.length;

    const events: [number, "open" | "close", string][] = [];

    for (const e of entities) {
        const s = e.offset;
        const l = e.length;
        if (s >= len || l <= 0) continue;

        const cls = (e as any).className as string;

        let open = "";
        let close = "";

        if (cls === "MessageEntityBold") {
            open = "**"; close = "**";
        } else if (cls === "MessageEntityItalic") {
            open = "_"; close = "_";
        } else if (cls === "MessageEntityStrike") {
            open = "~~"; close = "~~";
        } else if (cls === "MessageEntityCode") {
            open = "`"; close = "`";
        } else if (cls === "MessageEntityPre") {
            open = "```\n"; close = "\n```";
        } else if (cls === "MessageEntityUnderline") {
            open = "__"; close = "__";
        } else if (cls === "MessageEntitySpoiler") {
            open = "||"; close = "||";
        } else if (cls === "MessageEntityTextUrl") {
            const url = "url" in e && typeof e.url === "string" ? e.url : "#";
            open = "["; close = `](${url})`;
        }

        if (open) {
            events.push([s, "open", open]);
            events.push([s + l, "close", close]);
        }
    }

    events.sort((a, b) => {
        if (a[0] !== b[0]) return a[0] - b[0];
        return a[1] === "close" ? -1 : 1;
    });

    let result = "";
    let cursor = 0;

    for (const [pos, type, tag] of events) {
        if (pos > cursor && pos <= len) {
            result += text.slice(cursor, pos);
            cursor = pos;
        }
        result += tag;
    }

    if (cursor < len) {
        result += text.slice(cursor);
    }

    return result;
}