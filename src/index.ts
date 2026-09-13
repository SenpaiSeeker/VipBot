import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";
import { sessions, TelegramClient } from "teleproto";
import { configure, getConfig } from "./config";
import { db, init_database, schedule } from "./database";
import "./helpers/index";
import { patchTelegramClient } from "./facade";
import { BotManager } from "./bot_manager";
import { register_all_handlers, ctx } from "./VvipBot/index";
import { initialize_bot_services } from "./services";
import { LoggerHandler } from "./helpers/logger";
import { load_session, save_session } from "./helpers/sessionStore";

const log = new LoggerHandler();

type Any = any;

function session_prefix_for_env(env_file: string): string {
    return path.basename(env_file).replace(/\.env$/, "");
}

function build_main_client(config: ReturnType<typeof getConfig>): TelegramClient {
    const saved = load_session(session_prefix_for_env(config.ENV_FILE));
    const session = saved
        ? new sessions.StringSession(saved)
        : new sessions.StringSession();
    return new TelegramClient(
        session,
        config.API_ID,
        config.API_HASH,
        {}
    );
}

function clean_sessions(): void {
    try {
        execSync("rm -rf *.session* /tmp/*.session*", { stdio: "ignore" });
    } catch {
        // ignore cleanup failures
    }
}

function register_signal_handlers(): Promise<void> {
    let stop_resolve: (() => void) | undefined;
    const stop_promise = new Promise<void>((resolve) => {
        stop_resolve = resolve;
    });
    const handler = () => {
        if (stop_resolve) {
            stop_resolve();
        }
    };
    process.on("SIGINT", handler);
    process.on("SIGTERM", handler);
    return stop_promise;
}

async function shutdown(app: TelegramClient, manager: BotManager): Promise<void> {
    log.print(`${log.ORANGE}Memulai proses shutdown...`);
    if (app.is_connected) {
        try {
            await app.disconnect();
        } catch {
            // ignore
        }
    }
    const bot_ids = Object.keys(manager.running_bots);
    if (bot_ids.length) {
        try {
            await Promise.all(
                bot_ids.map((bot_id) => manager.stop_bot(bot_id))
            );
        } catch {
            // ignore
        }
    }
    log.print(`${log.RED}Semua proses telah dimatikan.`);
}

async function main(): Promise<void> {
    configure();
    const config = getConfig();
    init_database();

    clean_sessions();

    const manager = new BotManager(db, config.OWNER_ID);
    ctx.manager = manager as unknown as Any;

    const app = build_main_client(config);
    patchTelegramClient(app);
    register_all_handlers(app, db, manager as unknown as Any, config.OWNER_ID);

    const stop_promise = register_signal_handlers();

    try {
        app.ns.utils.grad.render_text("VVIP Meneger");
        log.print(`${log.MAGENTA}Developed by NorSodikin`);

        await app.start({ botAuthToken: config.BOT_TOKEN });
        Object.defineProperty(app, "me", {
            value: await app.getMe(),
            writable: true,
            configurable: true,
            enumerable: true,
        });
        save_session(
            session_prefix_for_env(config.ENV_FILE),
            String((app.session as Any).save())
        );
        log.info(`Bot utama '${app.me.firstName}' berhasil dimulai.`);

        await initialize_bot_services(app, db);

        manager.main_bot_client = app;
        manager.main_bot_id = String(app.me.id);
        manager.running_bots[String(app.me.id)] = app;

        await manager.start_all_bots();

        if (schedule.jobs.length) {
            schedule.start();
        }

        log.print(`${log.CYAN}Bot sekarang berjalan. Tekan Ctrl+C untuk berhenti.`);

        await stop_promise;
    } catch (e: Any) {
        log.print(`${log.RED}[FATAL] Terjadi error saat memulai: ${e}`);
    } finally {
        await shutdown(app, manager);
        process.exit(0);
    }
}

void main();