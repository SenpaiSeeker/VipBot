import { TelegramClient } from "teleproto";
import { command, ctx } from "../index";
import { Filters } from "../filters";
import { toId } from "../../types";

function _fmtDate(d: Date): string {
    return d.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

export const extend_command_handler = command(
    (_c: any) =>
        Filters.command("extend") &&
        Filters.user((_c2: any) => ctx.owner_id as any),
    "message"
)(async (client: TelegramClient, message: any) => {
    const [bot_id, days_str] = await client.ns.telegram.arg.getReasonAndId(
        message
    );
    if (!bot_id || !days_str) {
        return await message.reply_text(
            "**Format salah.**\nGunakan: `/extend <bot_id/@username> <jumlah_hari>` atau reply ke pesan bot.\nContoh: `/extend 12345678 30` atau `/extend @namabot 30`"
        );
    }
    let days_to_add: number;
    try {
        days_to_add = Math.trunc(Number(days_str.trim()));
        if (!/^\d+$/.test(days_str.trim())) {
            throw new Error();
        }
    } catch {
        return await message.reply_text(
            "**Format salah.** `jumlah_hari` harus berupa angka bulat.\nContoh: `/extend 12345678 30`"
        );
    }

    const exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date");
    const current_exp_date = exp_date_str
        ? new Date(exp_date_str)
        : new Date();
    const new_exp_date = new Date(
        current_exp_date.getTime() + days_to_add * 24 * 3600 * 1000
    );
    await ctx.db.setVars(bot_id, "bot_expiration_date", new_exp_date.toISOString());

    const formatted_new_date = _fmtDate(new_exp_date);
    await message.reply_text(
        `${client.ns.emoji.white_check_mark} **Sukses!** Durasi bot \`${bot_id}\` berhasil diubah. Masa aktif baru: \`${formatted_new_date}\`.`
    );

    const owner_bot_id = await ctx.db.getVars(bot_id, "owner_id");
    if (owner_bot_id) {
        try {
            const bot_instance = ctx.manager.running_bots.get(
                Math.trunc(Number(bot_id))
            );
            const bot_name = bot_instance
                ? bot_instance.me.firstName
                : `ID ${bot_id}`;
            await client.send_message(
                owner_bot_id,
                `${client.ns.emoji.party_popper} **Kabar Baik!**\n\nMasa aktif bot Anda **${bot_name}** telah diperpanjang oleh Owner Utama.`
            );
        } catch {
            // ignore
        }
    }
});

export const broadcast_owners_handler = command(
    (_c: any) =>
        Filters.command("broadcast_owners") &&
        Filters.user((_c2: any) => ctx.owner_id as any),
    "message"
)(async (client: TelegramClient, message: any) => {
    const broadcast_msg = await client.ns.telegram.arg.getMessage(message);
    if (!broadcast_msg) {
        return await message.reply_text(
            "Gunakan: `/broadcast_owners <pesan>` atau balas ke sebuah pesan."
        );
    }

    const all_bots_data = await ctx.db.getBots(true);
    const owner_ids = new Set<string>();
    for (const bot of all_bots_data) {
        const owner_id = await ctx.db.getVars(
            Math.trunc(Number(bot["name"])),
            "owner_id"
        );
        if (owner_id) {
            owner_ids.add(toId(owner_id));
        }
    }
    if (!owner_ids.size) {
        return await message.reply_text(
            "Tidak ada pemilik bot yang bisa di-broadcast."
        );
    }

    const total_owners = owner_ids.size;
    const progress_msg = await message.reply_text(
        `${client.ns.emoji.white_check_mark} Memulai siaran ke \`${total_owners}\` pengguna...`
    );
    let success_count = 0;
    let fail_count = 0;
    for (const owner_id of owner_ids) {
        try {
            const target = await client
                .getInputEntity(owner_id)
                .catch(() => undefined);
            if (target) {
                await broadcast_msg.copy(owner_id);
                success_count += 1;
            } else {
                fail_count += 1;
            }
        } catch (e) {
            ctx.log.print(`${ctx.log.RED}Gagal broadcast ke owner ${owner_id}: ${e}`);
            fail_count += 1;
        }
        await new Promise((r) => setTimeout(r, 200));
    }

    await progress_msg.edit(
        `**${client.ns.emoji.loudspeaker} Siaran Selesai!**\n` +
            `${client.ns.emoji.white_check_mark} **Terkirim:** \`${success_count}\`\n` +
            `${client.ns.emoji.cross_mark} **Gagal:** \`${fail_count}\``
    );
});