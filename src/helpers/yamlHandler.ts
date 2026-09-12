import * as fsp from "fs/promises";
import * as yaml from "js-yaml";
import { AnsiColors } from "./colorize";

export function _to_namespace(data: unknown): any {
    if (data !== null && typeof data === "object" && !Array.isArray(data)) {
        const out: Record<string, unknown> = {};
        for (const [k, v] of Object.entries(data)) {
            out[String(k)] = _to_namespace(v);
        }
        return out;
    }
    if (Array.isArray(data)) {
        return data.map((item) => _to_namespace(item));
    }
    return data;
}

export class YamlHandler extends AnsiColors {
    async loadAndConvert(filePath: string): Promise<Record<string, unknown> | null> {
        try {
            const rawContent = await fsp.readFile(filePath, "utf-8");
            const rawData = yaml.load(rawContent);
            return _to_namespace(rawData);
        } catch (e) {
            if ((e as NodeJS.ErrnoException).code === "ENOENT") {
                console.log(
                    `${this.YELLOW}File ${this.LIGHT_CYAN}'${filePath}' ` +
                        `${this.RED}tidak ditemukan.${this.RESET}`
                );
            } else if (e instanceof yaml.YAMLException) {
                console.log(
                    `${this.YELLOW}Kesalahan saat memproses file YAML: ` +
                        `${this.RED}${e}${this.RESET}`
                );
            }
        }
        return null;
    }
}