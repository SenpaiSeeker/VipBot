import figlet from "figlet";

function _random_channel(): number {
    return 128 + Math.floor(Math.random() * 128);
}

function _rgb_to_256_ansi_index(r: number, g: number, b: number): number {
    if (r === g && g === b) {
        if (r < 8) return 16;
        if (r > 248) return 231;
        return Math.round(((r - 8) / 247) * 24) + 232;
    }
    const rIdx = Math.round((r / 255) * 5);
    const gIdx = Math.round((g / 255) * 5);
    const bIdx = Math.round((b / 255) * 5);
    return 16 + 36 * rIdx + 6 * gIdx + bIdx;
}

export class Gradient {
    private start_color: [number, number, number];
    private end_color: [number, number, number];

    constructor() {
        this.start_color = [_random_channel(), _random_channel(), _random_channel()];
        this.end_color = [_random_channel(), _random_channel(), _random_channel()];
    }

    static random_color(): [number, number, number] {
        return [_random_channel(), _random_channel(), _random_channel()];
    }

    rgb_to_ansi(r: number, g: number, b: number): string {
        return `\x1b[38;5;${_rgb_to_256_ansi_index(r, g, b)}m`;
    }

    interpolate_color(factor: number): [number, number, number] {
        const _channel = (start: number, end: number) =>
            Math.max(0, Math.min(255, Math.round(start + (end - start) * factor)));
        const [rs, gs, bs] = this.start_color;
        const [re, ge, be] = this.end_color;
        return [_channel(rs, re), _channel(gs, ge), _channel(bs, be)];
    }

    render_text(text: string): void {
        const rendered = figlet.textSync(text, { font: "Slant" });
        let out = "";
        for (let i = 0; i < rendered.length; i++) {
            const factor = i / Math.max(rendered.length - 1, 1);
            const [r, g, b] = this.interpolate_color(factor);
            out += `${this.rgb_to_ansi(r, g, b)}${rendered[i]}`;
        }
        console.log(`${out}\x1b[0m`);
    }
}