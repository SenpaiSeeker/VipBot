import * as fs from "fs";
import * as fsp from "fs/promises";
import * as path from "path";
import AdmZip from "adm-zip";
import { CipherHandler } from "./encrypt";
import { Scheduler } from "./scheduler";

const _INITIAL_DATA = { vars: {}, bots: [] };

class Mutex {
    private _tail: Promise<unknown> = Promise.resolve();

    async run<T>(fn: () => Promise<T>): Promise<T> {
        const result = this._tail.then(async () => fn());
        this._tail = result.then(
            () => undefined,
            () => undefined
        );
        return result;
    }
}

function _now_components(): {
    y: string; mo: string; d: string; h: string; mi: string; s: string;
} {
    const dt = new Date();
    const parts = new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Jakarta",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    }).formatToParts(dt);
    const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "00";
    let h = get("hour");
    if (h === "24") h = "00";
    return { y: get("year"), mo: get("month"), d: get("day"), h, mi: get("minute"), s: get("second") };
}

function _decode(decrypted: unknown): unknown {
    if (typeof decrypted === "string" && (decrypted.startsWith("[") || decrypted.startsWith("{"))) {
        try {
            return JSON.parse(decrypted);
        } catch {
            return decrypted;
        }
    }
    return decrypted;
}

interface BotRecord {
    user_id?: string;
    _id?: string;
    api_id?: string;
    api_hash?: string;
    bot_token?: string;
    session_string?: string;
    [k: string]: unknown;
}

type VarsMap = Record<string, unknown>;

export class DataBase {
    storage_type = "local";
    file_name: string;
    keys_encrypt: string;
    method_encrypt: string;
    cipher: CipherHandler;
    _lock = new Mutex();
    auto_backup: boolean;
    backup_bot_token?: string;
    backup_chat_id?: number | string;
    backup_cron_spec: string;
    scheduler?: Scheduler;
    data_file: string;

    constructor(options: Record<string, unknown> = {}) {
        this.file_name = (options.file_name as string) || "database";
        this.keys_encrypt = (options.keys_encrypt as string) || "default_db_key_12345";
        this.method_encrypt = (options.method_encrypt as string) || "bytes";
        this.cipher = new CipherHandler({
            key: this.keys_encrypt,
            method: this.method_encrypt,
        });
        this.auto_backup = Boolean(options.auto_backup);
        this.backup_bot_token = options.backup_bot_token as string | undefined;
        this.backup_chat_id = options.backup_chat_id as number | string | undefined;
        this.backup_cron_spec = (options.backup_cron_spec as string) || "0 */3 * * *";
        this.scheduler = options.scheduler_instance as Scheduler | undefined;
        this.data_file = `${this.file_name}.json`;

        if (!fs.existsSync(this.data_file)) {
            fs.writeFileSync(this.data_file, JSON.stringify(_INITIAL_DATA, null, 4));
        }

        this._register_backup_task();
    }

    _register_backup_task(): void {
        if (this.auto_backup && this.scheduler) {
            if (!this.backup_bot_token || !this.backup_chat_id) {
                this.cipher.log.warning(
                    "Auto backup is disabled because token/chat_id is missing."
                );
                return;
            }
            this.scheduler.cron(this.backup_cron_spec)(async () => {
                void this.perform_backup();
            });
        }
    }

    async _load_data(): Promise<{ vars: VarsMap; bots: BotRecord[] }> {
        return this._lock.run(async () => {
            try {
                const content = await fsp.readFile(this.data_file, "utf-8");
                if (!content.trim()) {
                    return JSON.parse(JSON.stringify(_INITIAL_DATA));
                }
                return JSON.parse(content);
            } catch {
                return JSON.parse(JSON.stringify(_INITIAL_DATA));
            }
        });
    }

    async _save_data(data: unknown): Promise<void> {
        return this._lock.run(async () => {
            const temp_file = `${this.data_file}.tmp`;
            await fsp.writeFile(temp_file, JSON.stringify(data, null, 4), "utf-8");
            await fsp.rename(temp_file, this.data_file);
        });
    }

    async _user_vars(user_id: string | number): Promise<VarsMap> {
        const data = await this._load_data();
        return (data.vars[String(user_id)] as VarsMap) ?? {};
    }

    async _replace_user_vars(user_id: string | number, user_data: unknown): Promise<void> {
        const full_data = await this._load_data();
        full_data.vars[String(user_id)] = user_data;
        await this._save_data(full_data);
    }

    _setdefault(obj: Record<string, any>, key: string, def: unknown): any {
        if (!(key in obj)) {
            obj[key] = def;
        }
        return obj[key];
    }

    async setVars(
        user_id: string | number,
        query_name: string,
        value: unknown,
        var_key = "variabel"
    ): Promise<void> {
        const user_data = await this._user_vars(user_id);
        const bucket = this._setdefault(user_data, var_key, {});
        bucket[query_name] = await this.cipher.encrypt(JSON.stringify(value));
        await this._replace_user_vars(user_id, user_data);
    }

    async getVars(
        user_id: string | number,
        query_name: string,
        var_key = "variabel"
    ): Promise<any> {
        const user_data = await this._user_vars(user_id);
        const encryptedValue = (user_data[var_key] as VarsMap | undefined)?.[query_name];
        if (!encryptedValue) {
            return undefined;
        }
        const decrypted = await this.cipher.decrypt(encryptedValue as string);
        return _decode(decrypted);
    }

    async removeVars(
        user_id: string | number,
        query_name: string,
        var_key = "variabel"
    ): Promise<void> {
        const user_data = await this._user_vars(user_id);
        const bucket = user_data[var_key] as VarsMap | undefined;
        if (bucket && query_name in bucket) {
            delete bucket[query_name];
            await this._replace_user_vars(user_id, user_data);
        }
    }

    async setListVars(
        user_id: string | number,
        query_name: string,
        value: unknown,
        var_key = "variabel"
    ): Promise<void> {
        const encryptedValue = await this.cipher.encrypt(JSON.stringify(value));
        const user_data = await this._user_vars(user_id);
        const bucket = this._setdefault(user_data, var_key, {});
        const list = this._setdefault(bucket, query_name, []) as string[];
        if (!list.includes(encryptedValue)) {
            list.push(encryptedValue);
            await this._replace_user_vars(user_id, user_data);
        }
    }

    async getListVars(
        user_id: string | number,
        query_name: string,
        var_key = "variabel"
    ): Promise<any[]> {
        const user_data = await this._user_vars(user_id);
        const encryptedList = ((user_data[var_key] as VarsMap | undefined)?.[query_name] as string[]) ?? [];
        const decodedList: any[] = [];
        for (const raw of encryptedList) {
            const decrypted = await this.cipher.decrypt(raw);
            decodedList.push(_decode(decrypted));
        }
        return decodedList;
    }

    async removeListVars(
        user_id: string | number,
        query_name: string,
        value: unknown,
        var_key = "variabel"
    ): Promise<void> {
        const encryptedValue = await this.cipher.encrypt(JSON.stringify(value));
        const user_data = await this._user_vars(user_id);
        try {
            const bucket = (user_data[var_key] as VarsMap | undefined)?.[query_name] as string[] | undefined;
            if (bucket) {
                const idx = bucket.indexOf(encryptedValue);
                if (idx !== -1) {
                    bucket.splice(idx, 1);
                    await this._replace_user_vars(user_id, user_data);
                }
            }
        } catch {
            // ignore
        }
    }

    async removeAllVars(user_id: string | number): Promise<void> {
        const full_data = await this._load_data();
        if (String(user_id) in full_data.vars) {
            delete full_data.vars[String(user_id)];
            await this._save_data(full_data);
        }
    }

    async allVars(user_id: string | number, var_key = "variabel"): Promise<Record<string, any>> {
        const user_data = await this._user_vars(user_id);
        const encryptedData = (user_data[var_key] as VarsMap | undefined) ?? {};
        const decoded: Record<string, any> = {};
        for (const [key, value] of Object.entries(encryptedData)) {
            if (Array.isArray(value)) {
                const items: any[] = [];
                for (const raw of value as string[]) {
                    try {
                        items.push(_decode(await this.cipher.decrypt(raw)));
                    } catch {
                        items.push(raw);
                    }
                }
                decoded[key] = items;
            } else {
                try {
                    decoded[key] = _decode(await this.cipher.decrypt(value as string));
                } catch {
                    decoded[key] = value;
                }
            }
        }
        return decoded;
    }

    async saveBot(
        user_id: string | number,
        api_id: unknown,
        api_hash: string,
        value?: string | null,
        is_token = false
    ): Promise<void> {
        const field = is_token ? "bot_token" : "session_string";
        const encApiId = await this.cipher.encrypt(String(api_id));
        const encApiHash = await this.cipher.encrypt(api_hash);
        const botData: Record<string, unknown> = { api_id: encApiId, api_hash: encApiHash };
        if (value) {
            botData[field] = await this.cipher.encrypt(value);
        }
        const full_data = await this._load_data();
        const bots = full_data.bots as BotRecord[];
        let index = -1;
        for (let i = 0; i < bots.length; i++) {
            if (bots[i].user_id === String(user_id)) {
                index = i;
                break;
            }
        }
        if (index !== -1) {
            Object.assign(bots[index], botData);
        } else {
            bots.push({ user_id: String(user_id), ...botData } as BotRecord);
        }
        full_data.bots = bots;
        await this._save_data(full_data);
    }

    async getBots(is_token = false): Promise<any[]> {
        const data = await this._load_data();
        const results = await Promise.all(
            (data.bots as BotRecord[]).map(async (botData) => {
                try {
                    const decrypted: Record<string, any> = {
                        name: botData.user_id ?? botData._id,
                    };
                    const targets: Record<string, string> = {};
                    for (const key of ["api_id", "api_hash", "bot_token", "session_string"]) {
                        const v = botData[key] as string | undefined;
                        if (v) targets[key] = v;
                    }
                    for (const [key, value] of Object.entries(targets)) {
                        let result: unknown;
                        try {
                            result = this.cipher.decrypt(value);
                        } catch {
                            result = undefined;
                        }
                        if (result === undefined) continue;
                        decrypted[key] = key === "api_id" ? Number(result) : String(result);
                    }
                    if ((is_token && "bot_token" in decrypted) || (!is_token && "session_string" in decrypted)) {
                        return decrypted;
                    }
                } catch {
                    // ignore
                }
                return undefined;
            })
        );
        return results.filter((r) => r !== undefined);
    }

    async removeBot(user_id: string | number): Promise<void> {
        const full_data = await this._load_data();
        full_data.bots = (full_data.bots as BotRecord[]).filter(
            (b) => b.user_id !== String(user_id)
        );
        await this._save_data(full_data);
    }

    async perform_backup(): Promise<void> {
        const temp_backup_dir = "temp_db_backup";
        let zip_path: string | undefined;
        await this._lock.run(async () => {
            if (!fs.existsSync(this.data_file)) return;
            await fsp.mkdir(temp_backup_dir, { recursive: true }).catch(() => undefined);
            try {
                const temp_db_path = path.join(temp_backup_dir, path.basename(this.data_file));
                await fsp.copyFile(this.data_file, temp_db_path);
            } catch {
                await fsp.rm(temp_backup_dir, { recursive: true, force: true }).catch(() => undefined);
                return;
            }
            try {
                zip_path = this._create_zip_archive(temp_backup_dir, temp_backup_dir);
            } catch {
                zip_path = undefined;
            }
            if (zip_path) {
                const timestamp =
                    `${this._now_fmt("%Y-%m-%d %H:%M:%S")} WIB`;
                const caption =
                    `Backup otomatis untuk \`${path.basename(zip_path)}\`\n` +
                    `Tipe DB: \`${this.storage_type}\`\n` +
                    `Waktu: \`${timestamp}\``;
                await this._send_zip_to_telegram(zip_path, caption);
            }
        });
        await fsp.rm(temp_backup_dir, { recursive: true, force: true }).catch(() => undefined);
        if (zip_path) {
            await fsp.rm(zip_path, { force: true }).catch(() => undefined);
        }
    }

    _now_fmt(fmt: string): string {
        const c = _now_components();
        return fmt
            .replace("%Y", c.y)
            .replace("%m", c.mo)
            .replace("%d", c.d)
            .replace("%H", c.h)
            .replace("%M", c.mi)
            .replace("%S", c.s);
    }

    _timestamp_compact(): string {
        const c = _now_components();
        return `${c.y}${c.mo}${c.d}_${c.h}${c.mi}${c.s}`;
    }

    _create_zip_archive(containing_dir: string, _temp_dir: string): string {
        const timestamp = this._timestamp_compact();
        const zipFilename = `backup_${this.file_name}_${timestamp}.zip`;
        const zip = new AdmZip();
        const dbBasename = path.basename(this.data_file);
        const sourcePath = path.join(containing_dir, dbBasename);
        zip.addLocalFile(sourcePath, "", dbBasename);
        zip.writeZip(zipFilename);
        return zipFilename;
    }

    async _send_zip_to_telegram(file_path: string, caption: string): Promise<void> {
        const url = `https://api.telegram.org/bot${this.backup_bot_token}/sendDocument`;
        try {
            const fileBytes = await fsp.readFile(file_path);
            const form = new FormData();
            form.append("chat_id", String(this.backup_chat_id));
            form.append("caption", caption);
            form.append("parse_mode", "Markdown");
            form.append(
                "document",
                new Blob([new Uint8Array(fileBytes.buffer, fileBytes.byteOffset, fileBytes.byteLength)], {
                    type: "application/zip",
                }),
                path.basename(file_path)
            );
            await fetch(url, { method: "POST", body: form });
        } catch {
            // ignore
        }
    }
}