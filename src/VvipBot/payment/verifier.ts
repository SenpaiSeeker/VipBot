import { TelegramClient } from "teleproto";
import { ctx } from "../index";
import { dget } from "../../types";

type Any = any;

export const VERIFICATION_TIMEOUT = 3600;

export const LEAVING_STATUSES = ["left", "kicked"];

const _sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function verify_user_join(
    client: TelegramClient,
    user: Any,
    chat_id: Any,
    link_msg: Any
): Promise<void> {
    const start_time = Date.now() / 1000;
    let is_joined = false;

    while (Date.now() / 1000 - start_time < VERIFICATION_TIMEOUT) {
        try {
            const member = await client.get_chat_member(chat_id, user.id);
            if (!LEAVING_STATUSES.includes(String(member.status))) {
                is_joined = true;
                ctx.log.print(
                    `${ctx.log.GREEN}User ${user.id} berhasil bergabung ke ${chat_id}.`
                );
                break;
            }
        } catch {
            await _sleep(15000);
        }
    }

    try {
        await link_msg.delete();
    } catch {
        // ignore
    }

    if (!is_joined) {
        await client.send_message(
            user.id,
            `${client.ns.emoji.exclamation} **Peringatan!** Link undangan Anda telah kedaluwarsa karena Anda tidak bergabung dalam 60 menit.`
        );
    }
}

export async function verify_user_join_multiple(
    client: TelegramClient,
    user: Any,
    invite_payloads: Any[],
    link_msg: Any
): Promise<void> {
    const start_time = Date.now() / 1000;
    let pending_payloads: Any[] = [];

    while (Date.now() / 1000 - start_time < VERIFICATION_TIMEOUT) {
        pending_payloads = [];
        for (const payload of invite_payloads) {
            const chat_id = dget(payload, "chat_id");
            try {
                const member = await client.get_chat_member(chat_id, user.id);
                if (LEAVING_STATUSES.includes(String(member.status))) {
                    pending_payloads.push(payload);
                }
            } catch {
                pending_payloads.push(payload);
            }
        }

        if (!pending_payloads.length) {
            try {
                await link_msg.delete();
            } catch {
                // ignore
            }
            return;
        }
        await _sleep(15000);
    }

    const pending_lines = pending_payloads.map(
        (item) => `• ${dget(item, "name")}: ${dget(item, "link")}`
    );
    try {
        await client.send_message(
            user.id,
            `${client.ns.emoji.exclamation} Anda belum join ke semua grup VIP dalam waktu 60 menit.\n\n` +
                "Silakan join grup berikut:\n" +
                pending_lines.join("\n") +
                "\n",
            { protect_content: true }
        );
    } catch {
        // ignore
    }
}

export function _get_all_vvip_items(vvip_list: Any[]): Any[] {
    const selected_items: Any[] = [];
    for (let index = 0; index < vvip_list.length; index++) {
        const item = vvip_list[index];
        const price = Number(dget(item, "price", 0) || 0);
        const chat_id_normal = dget(item, "chat_id_normal");
        if (price > 0 && chat_id_normal) {
            selected_items.push({
                index,
                name: dget(item, "name") ?? `Paket ${index + 1}`,
                price,
                chat_id: chat_id_normal,
                duration: dget(item, "duration", 0),
            });
        }
    }
    return selected_items;
}