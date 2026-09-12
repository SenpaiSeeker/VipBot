import { DataBase } from "./helpers/database";
import { Scheduler } from "./helpers/scheduler";
import { getConfig } from "./config";

export const schedule = new Scheduler();

export let db: DataBase;

export function init_database(): DataBase {
    if (db) {
        return db;
    }
    const config = getConfig();
    db = new DataBase({
        storage_type: "local",
        file_name: config.DB_NAME || "vvip_database",
        keys_encrypt: config.DB_KEY,
        method_encrypt: "bytes",
        auto_backup: true,
        backup_bot_token: config.BOT_TOKEN,
        backup_chat_id: config.OWNER_ID,
        backup_cron_spec: "0 */3 * * *",
        scheduler_instance: schedule,
    });
    return db;
}