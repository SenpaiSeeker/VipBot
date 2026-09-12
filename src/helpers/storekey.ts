import { LoggerHandler } from "./logger";

export class KeyManager {
    logger = new LoggerHandler();

    handle_arguments(): [string, string] {
        const args = process.argv.slice(2);
        let key: string | undefined;
        let env: string | undefined;
        for (let i = 0; i < args.length; i++) {
            if (args[i] === "--key" && i + 1 < args.length) {
                key = args[i + 1];
            } else if (args[i] === "--env" && i + 1 < args.length) {
                env = args[i + 1];
            }
        }
        if (!key || !env) {
            this.logger.print(
                `${this.logger.RED}Argumen --key dan --env harus disertakan ` +
                    `untuk menjalankan bot.`
            );
            process.exit(1);
        }
        this.redact_key_arg();
        return [key, env];
    }

    redact_key_arg(): void {
        const cleaned: string[] = [];
        let skipNext = false;
        for (let i = 0; i < process.argv.length; i++) {
            if (skipNext) {
                skipNext = false;
                continue;
            }
            if (process.argv[i] === "--key") {
                cleaned.push("--key", "[REDACTED]");
                if (i + 1 < process.argv.length) {
                    skipNext = true;
                }
            } else {
                cleaned.push(process.argv[i]);
            }
        }
        try {
            process.title = cleaned.join(" ");
        } catch {
            this.logger.print(
                `${this.logger.YELLOW}Gagal menyembunyikan argumen proses`
            );
        }
    }
}