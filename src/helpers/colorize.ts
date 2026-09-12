const _COLOR_CODES: Record<string, string> = {
    BLACK: "\x1b[1;38;5;16m",
    RED: "\x1b[1;38;5;196m",
    GREEN: "\x1b[1;38;5;46m",
    YELLOW: "\x1b[1;38;5;226m",
    BLUE: "\x1b[1;38;5;21m",
    MAGENTA: "\x1b[1;38;5;201m",
    CYAN: "\x1b[1;38;5;51m",
    WHITE: "\x1b[1;38;5;231m",
    ORANGE: "\x1b[1;38;5;208m",
    PINK: "\x1b[1;38;5;206m",
    GRAY: "\x1b[1;38;5;244m",
    BROWN: "\x1b[1;38;5;94m",
    AQUA: "\x1b[1;38;5;123m",
    PURPLE: "\x1b[1;38;5;93m",
    GOLD: "\x1b[1;38;5;220m",
    SILVER: "\x1b[1;38;5;250m",
    INDIGO: "\x1b[1;38;5;54m",
    TEAL: "\x1b[1;38;5;30m",
    CRIMSON: "\x1b[1;38;5;160m",
    LIME: "\x1b[1;38;5;154m",
    TURQUOISE: "\x1b[1;38;5;45m",
    VIOLET: "\x1b[1;38;5;128m",
    CORAL: "\x1b[1;38;5;209m",
    MAROON: "\x1b[1;38;5;88m",
    NAVY: "\x1b[1;38;5;17m",
    OLIVE: "\x1b[1;38;5;58m",
    BEIGE: "\x1b[1;38;5;230m",
    MINT: "\x1b[1;38;5;121m",
    LIGHT_BLACK: "\x1b[1;38;5;235m",
    LIGHT_RED: "\x1b[1;38;5;203m",
    LIGHT_GREEN: "\x1b[1;38;5;120m",
    LIGHT_YELLOW: "\x1b[1;38;5;227m",
    LIGHT_BLUE: "\x1b[1;38;5;81m",
    LIGHT_MAGENTA: "\x1b[1;38;5;219m",
    LIGHT_CYAN: "\x1b[1;38;5;87m",
    LIGHT_WHITE: "\x1b[1;38;5;255m",
    LIGHT_ORANGE: "\x1b[1;38;5;214m",
    LIGHT_PINK: "\x1b[1;38;5;218m",
    LIGHT_GRAY: "\x1b[1;38;5;250m",
    LIGHT_BROWN: "\x1b[1;38;5;180m",
    LIGHT_AQUA: "\x1b[1;38;5;159m",
    LIGHT_PURPLE: "\x1b[1;38;5;183m",
    LIGHT_GOLD: "\x1b[1;38;5;228m",
    LIGHT_SILVER: "\x1b[1;38;5;253m",
    LIGHT_INDIGO: "\x1b[1;38;5;99m",
    LIGHT_TEAL: "\x1b[1;38;5;37m",
    LIGHT_CRIMSON: "\x1b[1;38;5;167m",
    LIGHT_LIME: "\x1b[1;38;5;191m",
    LIGHT_TURQUOISE: "\x1b[1;38;5;159m",
    LIGHT_VIOLET: "\x1b[1;38;5;177m",
    LIGHT_CORAL: "\x1b[1;38;5;216m",
    LIGHT_MAROON: "\x1b[1;38;5;131m",
    LIGHT_NAVY: "\x1b[1;38;5;33m",
    LIGHT_OLIVE: "\x1b[1;38;5;100m",
    LIGHT_BEIGE: "\x1b[1;38;5;253m",
    LIGHT_MINT: "\x1b[1;38;5;157m",
};

export class AnsiColors {
    RESET: string;
    BLACK: string = "";
    RED: string = "";
    GREEN: string = "";
    YELLOW: string = "";
    BLUE: string = "";
    MAGENTA: string = "";
    CYAN: string = "";
    WHITE: string = "";
    ORANGE: string = "";
    PINK: string = "";
    GRAY: string = "";
    BROWN: string = "";
    AQUA: string = "";
    PURPLE: string = "";
    GOLD: string = "";
    SILVER: string = "";
    INDIGO: string = "";
    TEAL: string = "";
    CRIMSON: string = "";
    LIME: string = "";
    TURQUOISE: string = "";
    VIOLET: string = "";
    CORAL: string = "";
    MAROON: string = "";
    NAVY: string = "";
    OLIVE: string = "";
    BEIGE: string = "";
    MINT: string = "";
    LIGHT_BLACK: string = "";
    LIGHT_RED: string = "";
    LIGHT_GREEN: string = "";
    LIGHT_YELLOW: string = "";
    LIGHT_BLUE: string = "";
    LIGHT_MAGENTA: string = "";
    LIGHT_CYAN: string = "";
    LIGHT_WHITE: string = "";
    LIGHT_ORANGE: string = "";
    LIGHT_PINK: string = "";
    LIGHT_GRAY: string = "";
    LIGHT_BROWN: string = "";
    LIGHT_AQUA: string = "";
    LIGHT_PURPLE: string = "";
    LIGHT_GOLD: string = "";
    LIGHT_SILVER: string = "";
    LIGHT_INDIGO: string = "";
    LIGHT_TEAL: string = "";
    LIGHT_CRIMSON: string = "";
    LIGHT_LIME: string = "";
    LIGHT_TURQUOISE: string = "";
    LIGHT_VIOLET: string = "";
    LIGHT_CORAL: string = "";
    LIGHT_MAROON: string = "";
    LIGHT_NAVY: string = "";
    LIGHT_OLIVE: string = "";
    LIGHT_BEIGE: string = "";
    LIGHT_MINT: string = "";

    constructor() {
        this.RESET = "\x1b[0m";
        for (const name of Object.keys(_COLOR_CODES)) {
            (this as unknown as Record<string, string>)[name] =
                _COLOR_CODES[name];
        }
    }

    print_all_colors(): void {
        for (const name of Object.keys(_COLOR_CODES)) {
            console.log(`${_COLOR_CODES[name]}${name}${this.RESET}`);
        }
    }

    get random_color(): [string, string] {
        const codes = Object.values(_COLOR_CODES);
        return [codes[Math.floor(Math.random() * codes.length)], this.RESET];
    }
}