import { TelegramClient } from "teleproto";
import { LoggerHandler } from "./helpers/logger";

const log = new LoggerHandler();

export async function initialize_bot_services(
    client: TelegramClient,
    db_instance: any
): Promise<void> {
    const bot_id = client.me.id;
    client.services.saweria = undefined;

    const saweria_user_id = await db_instance.getVars(bot_id, "SAWERIA_USER_ID");
    if (saweria_user_id) {
        try {
            client.services.saweria = new client.ns.payment.SaweriaScraper();
        } catch (e) {
            log.print(
                `${log.RED}Gagal inisialisasi SaweriaScraper untuk Bot ID ${bot_id}: ${e}`
            );
        }
    }
}