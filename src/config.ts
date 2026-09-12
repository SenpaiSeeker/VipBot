import * as fs from "fs";
import { config as loadDotEnv } from "dotenv";
import { KeyManager } from "./helpers/storekey";

export interface ConfigValues {
    API_ID: number;
    API_HASH: string;
    BOT_TOKEN: string;
    OWNER_ID: string;
    DB_NAME: string;
    BACKUP_BOT: string;
    DB_KEY: string;
    ENV_FILE: string;
}

export let API_ID = 0;
export let API_HASH = "";
export let BOT_TOKEN = "";
export let OWNER_ID = "";
export let DB_NAME = "";
export let BACKUP_BOT = "";
export let DB_KEY = "";
export let ENV_FILE = "";

let _loaded = false;

export function configure(envFile?: string, dbKey?: string): void {
    if (_loaded) {
        return;
    }
    _loaded = true;

    const key_manager = new KeyManager();
    if (envFile === undefined || dbKey === undefined) {
        const handled = key_manager.handle_arguments();
        DB_KEY = handled[0];
        ENV_FILE = handled[1];
    } else {
        DB_KEY = dbKey;
        ENV_FILE = envFile;
    }

    if (!fs.existsSync(ENV_FILE)) {
        key_manager.logger.print(
            `${key_manager.logger.RED}File environment '${ENV_FILE}' tidak ditemukan.`
        );
        process.exit(1);
    }

    loadDotEnv({ path: ENV_FILE });

    API_ID = Number(process.env.API_ID);
    API_HASH = process.env.API_HASH || "";
    BOT_TOKEN = process.env.BOT_TOKEN || "";
    OWNER_ID = process.env.OWNER_ID || "";
    DB_NAME = process.env.DB_NAME || "";
    BACKUP_BOT = process.env.BACKUP_BOT || "";
}

export function getConfig(): ConfigValues {
    return {
        API_ID,
        API_HASH,
        BOT_TOKEN,
        OWNER_ID,
        DB_NAME,
        BACKUP_BOT,
        DB_KEY,
        ENV_FILE,
    };
}