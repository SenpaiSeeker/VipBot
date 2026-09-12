import { AnsiColors } from "./colorize";

const _CODE_TO_NAME_ENV = {
    tz: "Asia/Jakarta",
};

function _format_time_with_tz(date: Date, tz: string, datefmt: string): string {
    const iso = date.toLocaleString("en-CA", {
        timeZone: tz,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    });
    const [datePart, timePart] = iso.split(", ");
    let [y, mo, d] = datePart.split("-");
    let [h, mi, s] = timePart.split(":");
    if (h === "24") h = "00";
    let out = datefmt
        .replace("%Y", y)
        .replace("%m", mo)
        .replace("%d", d)
        .replace("%H", h)
        .replace("%M", mi)
        .replace("%S", s);
    out = out.replace("%Z", "WIB");
    return out;
}

function _basename(path: string): string {
    const parts = path.split(/[\\/]/);
    return parts[parts.length - 1] || "<unknown>";
}

interface LogRecord {
    levelname: string;
    module: string;
    funcName: string;
    lineno: number;
    message: string;
}

function _caller(depth: number): { module: string; funcName: string; lineno: number } {
    const stack = new Error().stack?.split("\n") ?? [];
    for (const line of stack.slice(2)) {
        const m = line.match(/^\s*at\s+(?:(.+?)\s+\()?([^()]+):(\d+):(\d+)\)?\s*$/);
        if (m && !line.includes("logger.ts")) {
            return {
                module: _basename(m[2]),
                funcName: m[1] ? m[1].split(".").pop() ?? "<anonymous>" : "<anonymous>",
                lineno: Number(m[3]),
            };
        }
    }
    return { module: "<unknown>", funcName: "<unknown>", lineno: 0 };
}

export class LoggerHandler extends AnsiColors {
    tz: string;
    fmt: string;
    datefmt: string;
    colors: Record<string, string>;

    constructor(options: Record<string, unknown> = {}) {
        super();
        this.tz = (options.tz as string) || _CODE_TO_NAME_ENV.tz;
        this.fmt = (options.fmt as string) || "{asctime} {levelname} {module}:{funcName}:{lineno} {message}";
        this.datefmt = (options.datefmt as string) || "%Y-%m-%d %H:%M:%S %Z";
        this.colors = {
            INFO: this.GREEN,
            DEBUG: this.BLUE,
            WARNING: this.YELLOW,
            ERROR: this.RED,
            CRITICAL: this.MAGENTA,
            TIME: this.WHITE,
            MODULE: this.CYAN,
            PIPE: this.PURPLE,
            RESET: this.RESET,
        };
    }

    formatTime(): string {
        return _format_time_with_tz(new Date(), this.tz, this.datefmt);
    }

    format(record: LogRecord): string {
        const levelColor = this.colors[record.levelname] ?? this.RESET;
        const pipe = this.colors.PIPE;
        const level = `${pipe}│ ${levelColor}${record.levelname.padEnd(8)}`;
        const message = `${pipe}│ ${levelColor}${record.message}${this.RESET}`;
        const module = `${pipe}│ ${this.colors.MODULE}${_basename(record.module)}`;
        return this.fmt
            .replace("{asctime}", `${this.colors.TIME}[ ${this.formatTime()} ]`)
            .replace("{levelname}", level)
            .replace("{module}", module)
            .replace("{funcName}", record.funcName || "<unknown>")
            .replace("{lineno}", String(record.lineno ?? 0))
            .replace("{message}", message);
    }

    print(message: string, isPrint = true): string {
        const head = `${this.CYAN}[ ${this.WHITE}${this.formatTime()} ${this.CYAN}] ${this.WHITE}│ ${message}${this.RESET}`;
        if (isPrint) {
            console.log(`\x1b[2K${head}`);
            return head;
        }
        return head;
    }

    log(level: string, message: string, depth = 3): void {
        const info = _caller(depth);
        const record: LogRecord = {
            levelname: level,
            module: info.module,
            funcName: info.funcName,
            lineno: info.lineno,
            message,
        };
        console.log(`\x1b[2K${this.format(record)}`);
    }

    debug(message: string): void {
        this.log("DEBUG", message);
    }

    info(message: string): void {
        this.log("INFO", message);
    }

    warning(message: string): void {
        this.log("WARNING", message);
    }

    error(message: string): void {
        this.log("ERROR", message);
    }

    critical(message: string): void {
        this.log("CRITICAL", message);
    }
}

export class CustomLogHandler {
    formatter_util: LoggerHandler;

    constructor() {
        this.formatter_util = new LoggerHandler();
    }

    emit(
        record: {
            levelname: string;
            module: string;
            funcName: string;
            lineno: number;
            getMessage: () => string;
        }
    ): void {
        const custom_record: LogRecord = {
            levelname: record.levelname,
            module: record.module,
            funcName: record.funcName,
            lineno: record.lineno,
            message: record.getMessage(),
        };
        try {
            console.log(`\x1b[2K${this.formatter_util.format(custom_record)}`);
        } catch (_e) {
            // ignore
        }
    }
}