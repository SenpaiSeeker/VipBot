import * as fs from "fs";
import * as path from "path";

export function session_file(prefix: string): string {
    return path.join(process.cwd(), ".sessions", `${prefix}.session`);
}

export function load_session(prefix: string): string {
    try {
        const f = session_file(prefix);
        if (fs.existsSync(f)) {
            const value = fs.readFileSync(f, "utf8").trim();
            if (value) {
                return value;
            }
        }
    } catch {
        // ignore
    }
    return "";
}

export function save_session(prefix: string, value: string): void {
    try {
        const f = session_file(prefix);
        fs.mkdirSync(path.dirname(f), { recursive: true });
        fs.writeFileSync(f, value);
    } catch {
        // ignore
    }
}