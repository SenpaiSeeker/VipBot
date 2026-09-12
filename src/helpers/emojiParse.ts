import { EMOJI_MAP } from "./emojiMap";

const _ATTR_CACHE: Record<string, string> = {};

function _tag(name: string): string {
    if (name in _ATTR_CACHE) {
        return _ATTR_CACHE[name];
    }
    const entry = EMOJI_MAP[name];
    if (!entry) {
        throw new Error(`Emoji '${name}' tidak ditemukan dalam EmojiParse.`);
    }
    const [eid, char] = entry;
    const result = `<emoji id="${eid}">${char}</emoji>`;
    _ATTR_CACHE[name] = result;
    return result;
}

export class EmojiParse implements Record<string, string> {
    [key: string]: any;

    constructor() {
        return new Proxy(this, {
            get(target, prop: string | symbol) {
                if (typeof prop !== "string") {
                    return (target as any)[prop];
                }
                if (prop in target) {
                    return (target as any)[prop];
                }
                if (prop.startsWith("_")) {
                    throw new Error(`Emoji '${prop}' tidak ditemukan dalam EmojiParse.`);
                }
                if (prop in EMOJI_MAP) {
                    return _tag(prop);
                }
                throw new Error(`Emoji '${prop}' tidak ditemukan dalam EmojiParse.`);
            },
        });
    }

    get _emojiMap(): typeof EMOJI_MAP {
        return EMOJI_MAP;
    }

    id(name: string): number {
        const entry = EMOJI_MAP[name];
        if (!entry) {
            throw new Error(`Emoji '${name}' tidak ditemukan dalam EmojiParse.`);
        }
        return Number(entry[0]);
    }

    all_names(): string[] {
        return Object.keys(EMOJI_MAP);
    }
}