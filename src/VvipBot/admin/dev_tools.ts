import { spawnSync } from "child_process";
import * as fs from "fs";
import * as fsp from "fs/promises";
import * as os from "os";
import * as path from "path";
import * as util from "util";
import AdmZip from "adm-zip";
import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { is_bot_owner } from "../index";
import { Filters } from "../filters";
import { DataBase } from "../../helpers/database";

type Any = any;

if (!(ctx as Any).eval_history) {
    (ctx as Any).eval_history = {
        last_code: null,
        last_result: null,
        last_stdout: null,
        last_error: null,
        last_time: null,
    };
}

function shell(code: string): string {
    const r = spawnSync("bash", ["-c", code], {
        encoding: "utf-8",
        stdio: ["ignore", "pipe", "pipe"],
    });
    if (r.error) {
        return String(r.error.message);
    }
    if (r.stdout) {
        return String(r.stdout);
    }
    if (r.stderr) {
        return String(r.stderr);
    }
    return "";
}

function _msgText(msg: Any): string {
    if (!msg) {
        return "";
    }
    return msg.message || msg.caption || msg.text || "";
}

async function _reply_msg(client: Any, message: Any): Promise<Any | undefined> {
    const mid = message && message.replyToId;
    if (mid === undefined || mid === null) {
        return undefined;
    }
    let chat: Any = message.chatId;
    if (chat === undefined) {
        try {
            const entity = await client.getEntity(message.peerId);
            chat = entity && entity.id;
        } catch {
            return undefined;
        }
    }
    if (chat === undefined) {
        return undefined;
    }
    try {
        const msgs = await client.get_messages(chat, mid);
        return Array.isArray(msgs) ? msgs[0] : msgs;
    } catch {
        return undefined;
    }
}

async function get_eval_payload(client: Any, message: Any): Promise<string> {
    const text = _msgText(message);
    let args = "";
    const parts = text.split(/\s+/);
    if (/^\/\S+/.test(text.trim())) {
        args = text.slice(text.indexOf(parts[0]) + parts[0].length).trim();
    } else {
        const m = /^\S+\s([\s\S]*)$/.exec(text);
        if (m) {
            args = m[1].trim();
        }
    }
    if (args) {
        return args;
    }
    const reply = await _reply_msg(client, message);
    if (reply) {
        return _msgText(reply);
    }
    return "";
}

function _pprint(value: Any): string {
    if (value === null || value === undefined) {
        return "None";
    }
    if (typeof value === "string") {
        return value;
    }
    if (typeof value === "number" || typeof value === "boolean") {
        return String(value);
    }
    if (value instanceof Buffer || ArrayBuffer.isView(value)) {
        const v: any = value;
        return `<${value.constructor.name} bytes=${
            v.length ?? v.byteLength
        }>`;
    }
    try {
        return util.inspect(value, { depth: 4, colors: false, sorted: true });
    } catch {
        return String(value);
    }
}

async function create_exec_scope(
    client: Any,
    message: Any
): Promise<Record<string, Any>> {
    const manager = (ctx as Any).manager || undefined;
    const reply_data: Any = await _reply_msg(client, message);
    const scope: Record<string, Any> = {
        client: client,
        c: client,
        app: client,
        message: message,
        m: message,
        msg: message,
        r: reply_data,
        rep: reply_data,
        ctx: ctx,
        db: ctx.db,
        manager: manager,
        bots: manager ? manager.running_bots : undefined,
        os: os,
        path: path,
        fs: fs,
        util: util,
        shell: shell,
        sh: shell,
        print: (v: Any) => _pprint(v),
        chat: message.chat,
        user: message.from_user ? message.from_user : client.me,
    };
    return scope;
}

async function aexec(code: string, client: Any, message: Any): Promise<Any> {
    const scope = await create_exec_scope(client, message);
    const keys = Object.keys(scope);
    const AsyncFunction = Object.getPrototypeOf(
        async function () {}
    ).constructor as Any;
    let fn: Any;
    try {
        new Function(`return (${code});`);
        fn = new AsyncFunction(...keys, `return (${code});`);
    } catch {
        fn = new AsyncFunction(...keys, code);
    }
    return await fn(...keys.map((k) => scope[k]));
}

function format_output(
    client: Any,
    code: string,
    result: Any,
    stdout_val: string,
    stderr_val: string,
    exc_str: string | null,
    exec_time: number
): [string, string] {
    let final_output = "";
    let status_header = "Success";
    if (exc_str) {
        final_output = exc_str.trim();
        status_header = "Error";
    } else if (stderr_val) {
        final_output = stderr_val.trim();
        status_header = "Stderr";
    } else if (stdout_val) {
        final_output = stdout_val.trim();
        if (result !== undefined && result !== null) {
            final_output += `\n---\nReturn: ${_pprint(result)}`;
        }
    } else if (result !== undefined && result !== null) {
        final_output = _pprint(result).trim();
    } else {
        final_output = "None";
    }

    const escaped_code = code
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    const escaped_output = final_output
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    const out_len_limit = 777;
    const short_output =
        escaped_output.length > out_len_limit
            ? escaped_output.slice(0, out_len_limit) + "..."
            : escaped_output;

    let display_text = `<b>${client.ns.emoji.zap} Input:</b>\n`;
    display_text += `<pre><code class='language-js'>${escaped_code}</code></pre>\n\n`;
    display_text += `<b>${client.ns.emoji.laptop} Output (${status_header}):</b>\n`;
    display_text += `<pre><code>${short_output}</code></pre>\n\n`;
    display_text += `<b>${client.ns.emoji.hourglass} Time: </b><code>${exec_time.toFixed(4)}s</code>`;

    return [display_text, final_output];
}

async function execute_and_format(
    client: Any,
    message: Any,
    code: string
): Promise<[string, Any, Any]> {
    let result: Any = undefined;
    let exc_traceback: string | null = null;
    const start_time = Date.now();
    try {
        result = await Promise.race([
            aexec(code, client, message),
            new Promise((_, reject) =>
                setTimeout(() => reject(new Error("timeout")), 60000)
            ),
        ]);
    } catch (e: Any) {
        if (e && e.message === "timeout") {
            exc_traceback = `${client.ns.emoji.cross_mark} TimeoutError: Execution exceeded 60 seconds.`;
        } else if (e && e.name === "CancelledError") {
            exc_traceback = "CancelledError: Execution was cancelled.";
        } else {
            exc_traceback = `${e && e.stack ? e.stack : String(e)}`;
        }
    }
    const end_time = Date.now();
    const execution_time = (end_time - start_time) / 1000;
    const stdout_val = "";
    const stderr_val = "";

    Object.assign((ctx as Any).eval_history, {
        last_code: code,
        last_result:
            result === undefined || result === null ? null : _pprint(result),
        last_stdout: stdout_val,
        last_error: exc_traceback || stderr_val,
        last_time: execution_time,
    });

    const [display_text, raw_output] = format_output(
        client,
        code,
        result,
        stdout_val,
        stderr_val,
        exc_traceback,
        execution_time
    );

    let document: Any = undefined;
    if (raw_output.length > 777) {
        document = Buffer.from(raw_output, "utf-8");
        (document as Any).name = "output.txt";
    }

    const layout = [
        [
            {
                text: "Run Again",
                callback_data: `eval_run_${message.chat.id}_${message.id}`,
                style: "green",
            },
            {
                text: "Delete",
                callback_data: `eval_del_${message.chat.id}_${message.id}`,
                style: "red",
            },
        ],
    ];
    const keyboard = client.ns.telegram.button.build_button_grid(layout);

    return [display_text, keyboard, document];
}

export const eval_bot_handler = command(
    (_c: any) =>
        Filters.command("eval") && Filters.user((_c2: any) => ctx.owner_id),
    "message"
)(async (client: TelegramClient, message: Any) => {
    const code = await get_eval_payload(client, message);
    if (!code) {
        return await message.reply_text(
            `${client.ns.emoji.cross_mark} Berikan kode untuk dievaluasi atau balas ke sebuah pesan.`
        );
    }

    const status_msg = await message.reply_text(
        `${client.ns.emoji.repeat} <code>Memproses kode...</code>`
    );
    try {
        const [text, keyboard, document] = await execute_and_format(
            client,
            message,
            code
        );
        if (document) {
            await status_msg.delete();
            await message.reply_document(document, {
                caption: text,
                reply_markup: keyboard,
            });
        } else {
            await status_msg.edit_text(text, { reply_markup: keyboard });
        }
    } catch (e: Any) {
        const error_text = `<b>Kesalahan Handler:</b>\n<code>${String(
            e && e.stack ? e.stack : e
        )
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")}</code>`;
        if (status_msg) {
            try {
                await status_msg.edit_text(error_text);
            } catch {
                await message.reply_text(error_text);
            }
        } else {
            await message.reply_text(error_text);
        }
    }
});

export const eval_callback_handler = command(
    (_c: any) =>
        Filters.regex(/^eval_/) &&
        Filters.user((_c2: any) => ctx.owner_id as Any),
    "callback"
)(async (client: TelegramClient, query: Any) => {
    const data = query.data.split("_");
    if (data.length < 4) {
        return;
    }

    const action = data[1];
    const chat_id = Math.trunc(Number(data[2]));
    const message_id = Math.trunc(Number(data[3]));

    if (action === "del") {
        try {
            await client.delete_messages(chat_id, [
                message_id,
                query.message.id,
            ]);
        } catch {
            await query.answer("Tidak bisa menghapus pesan.");
        }
    } else if (action === "run") {
        try {
            const trigger_message = await client.get_messages(
                chat_id,
                message_id
            );
            const code = await get_eval_payload(client, trigger_message);
            if (!code) {
                return await query.answer(
                    "Kode tidak ditemukan untuk dijalankan kembali.",
                    { show_alert: true }
                );
            }

            await query.answer("Menjalankan kembali kode...");

            const [text, keyboard, document] = await execute_and_format(
                client,
                trigger_message,
                code
            );

            if (code.trim().endsWith("return")) {
                return;
            }

            const is_current_msg_media = Boolean(
                query.message.media && query.message.media.className
            );

            if (document) {
                try {
                    await query.message.delete();
                } catch {
                    // ignore
                }
                await client.send_document(chat_id, document, {
                    caption: text,
                    reply_markup: keyboard,
                    reply_to_message_id: message_id,
                });
            } else {
                try {
                    await query.message.delete();
                } catch {
                    // ignore
                }
                await client.send_message(chat_id, text, {
                    reply_markup: keyboard,
                    reply_to_message_id: message_id,
                });
            }
        } catch (e: Any) {
            await query.answer(`Error: ${_pprint(e)}`, { show_alert: true });
        }
    }
});

function _select_database(
    config: DataBase,
    target_name: string,
    db_class: typeof DataBase
): DataBase {
    if (target_name === config.file_name) {
        return config;
    }
    return new db_class({
        file_name: target_name,
        keys_encrypt: config.keys_encrypt,
        method_encrypt: config.method_encrypt,
        auto_backup: false,
    } as Any);
}

export const restore_database_handler = command(
    (_c: any) =>
        Filters.command("restore") &&
        Filters.user((_c2: any) => ctx.owner_id as Any),
    "message"
)(async (client: TelegramClient, message: Any) => {
    const reply_target: Any = await _reply_msg(client, message);
    if (!reply_target || !reply_target.document) {
        return await message.reply_text(
            `${client.ns.emoji.exclamation} **Cara Penggunaan Salah:**\nBalas (reply) ke file backup \`.zip\` yang dikirim oleh bot dengan perintah ini.`
        );
    }
    const doc = reply_target.document;
    if (!doc.fileName || !doc.fileName.endsWith(".zip")) {
        return await message.reply_text(
            `${client.ns.emoji.cross_mark} **Format File Salah:**\nHanya file backup dengan format \`.zip\` yang bisa dipulihkan.`
        );
    }
    const status_msg = await message.reply_text(
        `${client.ns.emoji.hourglass} \`Mendownload & mengekstrak file backup...\``
    );
    let downloaded_zip_path: Any = undefined;
    try {
        downloaded_zip_path = await client.download_media(reply_target);

        const temp_dir = fsp.mkdtemp(
            path.join(os.tmpdir(), "vvip_restore_")
        );
        const final_temp_dir = await temp_dir;
        const zip = new AdmZip(downloaded_zip_path);
        if (!zip.getEntries().length) {
            throw new Error("File .zip ini kosong atau rusak.");
        }
        zip.extractAllTo(final_temp_dir, true);
        const current_db_path = (ctx.db as Any).data_file;
        if (!current_db_path) {
            throw new Error("Tidak dapat menentukan path database aktif.");
        }
        const db_ext = ".json";
        let restored = "";
        const walk = async (dir: string): Promise<void> => {
            const entries = await fsp.readdir(dir, { withFileTypes: true });
            for (const entry of entries) {
                const full = path.join(dir, entry.name);
                if (entry.isDirectory()) {
                    await walk(full);
                } else if (entry.name.endsWith(db_ext)) {
                    await fsp.rm(current_db_path, { force: true });
                    await fsp.rename(full, current_db_path);
                    restored = path.basename(current_db_path);
                    return;
                }
            }
        };
        await walk(final_temp_dir);
        await fsp.rm(final_temp_dir, { recursive: true, force: true });
        if (!restored) {
            throw new Error(
                `Tidak ada file database (${db_ext}) yang valid ditemukan dalam arsip.`
            );
        }
        await status_msg.edit_text(
            `${client.ns.emoji.white_check_mark} **Pemulihan Berhasil!**\n` +
                `Database \`${restored}\` telah dipulihkan.\n\n` +
                `${client.ns.emoji.exclamation} **PENTING:** Mohon **restart** bot agar dapat menggunakan database baru.`
        );
        ctx.log.print(
            `${ctx.log.GREEN}File-file berikut dipulihkan: ${restored} oleh admin.`
        );
    } catch (e: Any) {
        await status_msg.edit_text(
            `${client.ns.emoji.cross_mark} **Pemulihan Gagal!**\n\n**Error:** \`${e}\``
        );
        ctx.log.print(`${ctx.log.RED}Restore failed: ${e}`);
    } finally {
        if (downloaded_zip_path) {
            await fsp
                .rm(downloaded_zip_path, { force: true })
                .catch(() => undefined);
        }
    }
});

export const tfdatabase_command_handler = command(
    (_c: any) =>
        Filters.command("tfdatabase") &&
        Filters.user((_c2: any) => ctx.owner_id as Any),
    "message"
)(async (client: TelegramClient, message: Any) => {
    const args = _msgText(message).trim().split(/\s+/);
    if (args.length !== 3) {
        return await message.reply_text(
            "Format salah. Gunakan: `/tfdatabase <source_id>:<source_db> <target_id>:<target_db>`\nContoh: `/tfdatabase 123455:databaseV1 666999:databaseV2`"
        );
    }
    const source_part = args[1];
    const target_part = args[2];
    let source_id: number;
    let target_id: number;
    let source_db_name: string;
    let target_db_name: string;
    try {
        const sp = source_part.split(":");
        const tp = target_part.split(":");
        source_id = Math.trunc(Number(sp[0]));
        target_id = Math.trunc(Number(tp[0]));
        source_db_name = sp[1];
        target_db_name = tp[1];
        if (isNaN(source_id) || isNaN(target_id)) {
            throw new Error();
        }
    } catch {
        return await message.reply_text(
            "Format salah. Pastikan menggunakan format `ID:NAMA_DB`. Contoh: `/tfdatabase 123455:databaseV1 666999:databaseV2`"
        );
    }
    const msg = await message.reply_text(
        `${client.ns.emoji.repeat} Memproses transfer database...`
    );
    try {
        const source_db: Any = _select_database(
            ctx.db,
            source_db_name,
            DataBase
        );
        const target_db: Any = _select_database(ctx.db, target_db_name, DataBase);
        const source_data = await source_db._user_vars(source_id);
        if (!source_data || Object.keys(source_data).length === 0) {
            return await msg.edit_text(
                `${client.ns.emoji.cross_mark} Data sumber tidak ditemukan pada database.`
            );
        }
        await target_db._replace_user_vars(target_id, source_data);
        await msg.edit_text(
            `${client.ns.emoji.white_check_mark} **Transfer Database Berhasil!**\n\n` +
                `**Sumber:** \`${source_id}\` (\`${source_db_name}\`)\n` +
                `**Tujuan:** \`${target_id}\` (\`${target_db_name}\`)\n\n` +
                `Semua data berhasil disalin secara lengkap.`
        );
    } catch (e: Any) {
        await msg.edit_text(
            `${client.ns.emoji.cross_mark} Terjadi kesalahan saat mentransfer database:\n<pre>${e}</pre>`
        );
    }
});

export const tfbot_command_handler = command(
    (_c: any) =>
        Filters.command("tfbot") &&
        Filters.user((_c2: any) => ctx.owner_id as Any),
    "message"
)(async (client: TelegramClient, message: Any) => {
    const args = _msgText(message).trim().split(/\s+/);
    if (args.length !== 4) {
        return await message.reply_text(
            "Format salah. Gunakan: `/tfbot <id_bot> <source_db> <target_db>`\nContoh: `/tfbot 123456789 vvip_database vvip_databaseV2`"
        );
    }
    let bot_id: number;
    try {
        bot_id = Math.trunc(Number(args[1]));
        if (isNaN(bot_id)) {
            throw new Error();
        }
    } catch {
        return await message.reply_text("ID Bot harus berupa angka.");
    }
    const source_db_name = args[2];
    const target_db_name = args[3];
    const msg = await message.reply_text(
        `${client.ns.emoji.repeat} Memproses migrasi bot...`
    );
    try {
        const source_db: Any = _select_database(
            ctx.db,
            source_db_name,
            DataBase
        );
        const target_db: Any = _select_database(ctx.db, target_db_name, DataBase);
        const bots_token: Any[] = await source_db.getBots(true);
        const bots_session: Any[] = await source_db.getBots(false);
        const all_bots = bots_token.concat(bots_session);
        let bot_data: Any = undefined;
        for (const b of all_bots) {
            if (String(b["name"]) === String(bot_id)) {
                bot_data = b;
                break;
            }
        }
        if (!bot_data) {
            return await msg.edit_text(
                `${client.ns.emoji.cross_mark} Bot dengan ID \`${bot_id}\` tidak ditemukan di \`${source_db_name}\`.`
            );
        }
        const source_vars = await source_db._user_vars(bot_id);
        const api_id = bot_data["api_id"];
        const api_hash = bot_data["api_hash"];
        const bot_token = bot_data["bot_token"];
        const session_string = bot_data["session_string"];
        if (bot_token) {
            await target_db.saveBot(
                bot_id,
                api_id,
                api_hash,
                bot_token,
                true
            );
        } else if (session_string) {
            await target_db.saveBot(
                bot_id,
                api_id,
                api_hash,
                session_string,
                false
            );
        }
        if (source_vars && Object.keys(source_vars).length) {
            await target_db._replace_user_vars(bot_id, source_vars);
        }
        await source_db.removeBot(bot_id);
        await source_db.removeAllVars(bot_id);
        if ((ctx as Any).manager.running_bots.has(bot_id)) {
            await (ctx as Any).manager.stop_bot(bot_id);
        }
        await msg.edit_text(
            `${client.ns.emoji.white_check_mark} **Migrasi Bot Berhasil!**\n\n` +
                `**Bot ID:** \`${bot_id}\`\n` +
                `**Dari:** \`${source_db_name}\`\n` +
                `**Ke:** \`${target_db_name}\`\n\n` +
                `Bot beserta seluruh datanya telah dipindahkan dan dihapus dari database lama.\n\n` +
                `Jangan lupa restart bot tujuan agar bot ini segera menyala.`
        );
    } catch (e: Any) {
        ctx.log.print(`${ctx.log.RED}Error saat tfbot: ${e}`);
    }
});