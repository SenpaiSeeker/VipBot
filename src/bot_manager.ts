import { Api, sessions, TelegramClient } from "teleproto";
import { DataBase } from "./helpers/database";
import { LoggerHandler } from "./helpers/logger";
import { schedule } from "./database";
import { initialize_bot_services } from "./services";
import { register_all_handlers, ctx } from "./VvipBot/index";
import { toId } from "./types";

type Any = any;

const log = new LoggerHandler();

const INVALID_TOKEN_ERRORS = [
    "USER_DEACTIVATED_BAN",
    "BOT_TOKEN_INVALID",
    "ACCESS_TOKEN_EXPIRED",
];

const WARNING_DAYS = [10, 5, 3, 1];

const DAY_MS = 24 * 60 * 60 * 1000;

function _daysLeft(expiry_iso: string, now: Date): number {
    const expiry = new Date(expiry_iso);
    return Math.floor((expiry.getTime() - now.getTime()) / DAY_MS);
}

export class BotManager {
    db: DataBase;
    owner_id: string;
    running_bots: Record<string, TelegramClient> = {};
    main_bot_client: TelegramClient | undefined = undefined;
    main_bot_id: string | undefined = undefined;

    constructor(db_instance: DataBase, owner_id: string) {
        this.db = db_instance;
        this.owner_id = toId(owner_id);
    }

    async start_bot(bot_data: Record<string, Any>): Promise<void> {
        const bot_id = Math.trunc(Number(bot_data["name"]));
        if (bot_id in this.running_bots) {
            log.warning(`Bot ${bot_id} sudah berjalan.`);
            return;
        }
        try {
            const client = new TelegramClient(
                new sessions.MemorySession(),
                Number(bot_data["api_id"]),
                String(bot_data["api_hash"]),
                {}
            );
            register_all_handlers(
                client,
                this.db,
                this as unknown as Any,
                this.owner_id
            );
            await client.start({
                botAuthToken: String(bot_data["bot_token"]),
            });
            await initialize_bot_services(client, this.db);
            this.running_bots[toId(client.me.id)] = client;
            log.info(
                `Bot ${client.me.firstName} (ID: ${client.me.id}) berhasil diaktifkan.`
            );
        } catch (e: Any) {
            log.print(`${log.RED}Gagal memulai bot ${bot_id}: ${e}`);
            const err_str = String(e).toUpperCase();
            if (INVALID_TOKEN_ERRORS.some((err) => err_str.includes(err))) {
                await this.db.removeBot(bot_id);
                log.debug(
                    `Data bot ${bot_id} dihapus karena token tidak valid/terblokir.`
                );
            }
        }
    }

    async start_all_bots(): Promise<void> {
        const all_bots_data = (await this.db.getBots(true)) || [];
        await Promise.all(
            all_bots_data.map((bot_data) => this.start_bot(bot_data))
        );
    }

    async stop_bot(bot_id: Any): Promise<void> {
        const key = toId(bot_id);
        const client = this.running_bots[key];
        delete this.running_bots[key];
        if (!client) {
            return;
        }
        try {
            if (client.is_connected) {
                await client.disconnect();
            }
            log.debug(`Bot ${bot_id} berhasil dihentikan.`);
        } catch (e: Any) {
            log.error(`Error saat menghentikan bot ${bot_id}: ${e}`);
        }
    }

    bot_display_name(bot_id: Any): string {
        const bot_instance = this.running_bots[toId(bot_id)];
        if (bot_instance && bot_instance.is_connected) {
            return bot_instance.me.firstName || `ID ${bot_id}`;
        }
        return `ID ${bot_id}`;
    }

    async relay_message(
        receiver_id: Any,
        text: string,
        fallback_client?: TelegramClient,
        reply_markup?: Any
    ): Promise<void> {
        try {
            await this.main_bot_client!.send_message(receiver_id, text, {
                buttons: reply_markup,
            } as Any);
        } catch {
            if (fallback_client) {
                await fallback_client.send_message(receiver_id, text, {
                    buttons: reply_markup,
                } as Any);
            }
        }
    }
}

export function purge_expired_bot(
    manager: BotManager,
    bot_id: Any,
    owner_id: Any
): Promise<void> {
    log.debug(`Masa aktif bot ${bot_id} telah habis. Menghapus bot...`);
    const bot_name = manager.bot_display_name(bot_id);
    const expired_message = `Masa aktif bot Anda **${bot_name}** sudah habis.`;
    return (async () => {
        await manager.relay_message(
            owner_id,
            expired_message,
            manager.running_bots[toId(bot_id)]
        );
        await manager.stop_bot(bot_id);
        await manager.db.removeBot(bot_id);
        log.warning(`Bot ${bot_id} telah dihapus karena kedaluwarsa.`);
    })();
}

async function send_expiry_warning(
    manager: BotManager,
    bot_id: Any,
    owner_id: Any,
    days_left: number
): Promise<void> {
    const today_str = new Date().toISOString().slice(0, 10);
    const notif_key = "last_warning_notification_date";
    if (
        (await manager.db.getVars(bot_id, notif_key)) === today_str
    ) {
        return;
    }
    try {
        const mc = manager.main_bot_client!;
        const users = await mc.get_users(owner_id);
        const owner_user = Array.isArray(users) ? users[0] : users;
        const mention_owner = mc.ns.telegram.arg.getMention(owner_user);
        const bot_name = manager.bot_display_name(bot_id);
        const warning_message =
            `${mc.ns.emoji.bell} **Notifikasi Masa Aktif** ` +
            `${mc.ns.emoji.bell}\n\n` +
            `Halo ${mention_owner},\n` +
            `Masa aktif bot Anda (**${bot_name}**) tinggal **${days_left} hari** lagi.\n\n` +
            "Silakan hubungi @NorSodikin jika mau diperpanjang.";
        await manager.relay_message(
            owner_id,
            warning_message,
            manager.running_bots[toId(bot_id)]
        );
        await manager.db.setVars(bot_id, notif_key, today_str);
        log.print(
            `${log.CYAN}Mengirim notifikasi sisa ${days_left} hari ke owner ${owner_id} ` +
                `untuk bot ${bot_id}`
        );
    } catch (e: Any) {
        log.print(
            `${log.RED}Gagal mengirim notifikasi perpanjangan ke owner ${owner_id}: ${e}`
        );
    }
}

export const expiration_checker_method = schedule.cron("0 * * * *")(async () => {
    log.info("Menjalankan pemeriksaan masa aktif bot...");
    const manager = ctx.manager as unknown as BotManager | undefined;
    if (!manager) {
        log.warning("BotManager belum diinisialisasi di ctx. Melewati pemeriksaan.");
        return;
    }
    const all_bots_data = (await manager.db.getBots(true)) || [];
    for (const bot_data of all_bots_data) {
        const bot_id = Math.trunc(Number(bot_data["name"]));
        try {
            const expiry_str = await manager.db.getVars(bot_id, "bot_expiration_date");
            if (!expiry_str) {
                continue;
            }
            const days_left = _daysLeft(String(expiry_str), new Date());
            const owner_id = await manager.db.getVars(bot_id, "owner_id");
            if (!owner_id || !manager.main_bot_client) {
                continue;
            }
            if (days_left < 1) {
                await purge_expired_bot(manager, bot_id, owner_id);
            } else if (WARNING_DAYS.includes(days_left)) {
                await send_expiry_warning(manager, bot_id, owner_id, days_left);
            } else if (days_left > 10) {
                const notif_key = "last_warning_notification_date";
                if (await manager.db.getVars(bot_id, notif_key)) {
                    await manager.db.removeVars(bot_id, notif_key);
                    log.info(`Mereset flag tanggal notifikasi untuk bot ${bot_id}.`);
                }
            }
        } catch (e: Any) {
            log.error(`Error saat memeriksa masa aktif bot ${bot_id}: ${e}`);
        }
    }
});

async function send_renewal_reminder(
    manager: BotManager,
    bot_client: TelegramClient,
    bot_id: Any,
    vvip_list: Any[],
    member: Record<string, Any>,
    time_left_days: number,
    now: Date
): Promise<void> {
    const user_id = member["user_id"];
    const vvip_name_val = member["vvip_name"];
    const notif_key = `last_renewal_notification_date_${bot_id}`;
    const today_str = now.toISOString().slice(0, 10);
    if ((await manager.db.getVars(user_id, notif_key)) === today_str) {
        return;
    }
    try {
        let item_index = -1;
        for (let i = 0; i < vvip_list.length; i++) {
            if (vvip_list[i]["name"] === vvip_name_val) {
                item_index = i;
                break;
            }
        }
        if (item_index === -1) {
            return;
        }
        const text =
            `${bot_client.ns.emoji.bell} **Pengingat Langganan**\n\n` +
            `Langganan Anda untuk paket **${vvip_name_val}** akan berakhir dalam ` +
            `**${time_left_days} hari** lagi. Perpanjang sekarang agar tidak ` +
            `kehilangan akses!`;
        const layout = [
            [
                {
                    text: "🔄 Perpanjang Sekarang",
                    callback_data: `renew_sub_${item_index}`,
                    style: "blue",
                    emoji: bot_client.ns.emoji.id("repeat"),
                },
            ],
        ];
        const btn = bot_client.ns.telegram.button.build_button_grid(layout);
        await bot_client.send_message(user_id, text, { buttons: btn });
        await manager.db.setVars(user_id, notif_key, today_str);
    } catch (e: Any) {
        log.print(`${ctx.log.RED}Gagal kirim notif perpanjangan ke ${user_id}: ${e}`);
    }
}

export const subscription_checker_method = schedule.cron("0 */12 * * *")(async () => {
    log.info("Menjalankan pemeriksaan langganan anggota...");
    const manager = ctx.manager as unknown as BotManager | undefined;
    if (!manager) {
        log.warning("BotManager belum diinisialisasi di ctx. Melewati pemeriksaan.");
        return;
    }
    const now = new Date();
    const all_bots_data = (await manager.db.getBots(true)) || [];
    const all_bot_ids = all_bots_data.map((d) => Math.trunc(Number(d["name"])));

    for (const bot_id of all_bot_ids) {
        const bot_client = manager.running_bots[toId(bot_id)];
        if (!bot_client || !bot_client.is_connected) {
            continue;
        }
        const members = (await manager.db.getListVars(bot_id, "vvip_members")) || [];
        const vvip_list = (await manager.db.getListVars(bot_id, "list_vvip")) || [];
        const members_to_keep: Any[] = [];

        for (const member of members) {
            const expiry_str = member["expiry_date"];
            if (!expiry_str) {
                members_to_keep.push(member);
                continue;
            }
            const expiry_date = new Date(String(expiry_str));
            const user_id = member["user_id"];
            if (now.getTime() > expiry_date.getTime()) {
                try {
                    const chat_id = member["chat_id_kick"];
                    await bot_client.ban_chat_member(chat_id, user_id);
                    await new Promise((r) => setTimeout(r, 1000));
                    await bot_client.unban_chat_member(chat_id, user_id);
                    const vvip_name_val = member["vvip_name"];
                    const expired_message_text =
                        `${bot_client.ns.emoji.hourglass_done} **Langganan Berakhir**\n\n` +
                        `Langganan Anda untuk paket **${vvip_name_val}** telah ` +
                        `berakhir. Anda telah dikeluarkan dari grup.`;
                    await bot_client.send_message(user_id, expired_message_text);
                    log.debug(
                        `Langganan ${user_id} di bot ${bot_id} habis. ` +
                            `Dikeluarkan dari grup.`
                    );
                } catch (e: Any) {
                    log.error(`Gagal kick member ${user_id} dari grup: ${e}`);
                }
                continue;
            }

            const time_left_days = Math.floor(
                (expiry_date.getTime() - now.getTime()) / DAY_MS
            );
            if (time_left_days > 2 && time_left_days <= 3) {
                await send_renewal_reminder(
                    manager,
                    bot_client,
                    bot_id,
                    vvip_list,
                    member,
                    time_left_days,
                    now
                );
            }
            members_to_keep.push(member);
        }

        if (members_to_keep.length !== members.length) {
            await manager.db.removeVars(bot_id, "vvip_members");
            for (const m of members_to_keep) {
                await manager.db.setListVars(bot_id, "vvip_members", m);
            }
        }
    }
});