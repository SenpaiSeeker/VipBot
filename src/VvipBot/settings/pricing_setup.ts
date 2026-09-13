import { randomUUID } from "crypto";
import { TelegramClient } from "teleproto";
import { command, ctx, is_bot_owner } from "../index";
import { Filters } from "../filters";
import { UserCancelledError, WaitTimeoutError, ValueError } from "../../types";
import { entitiesToMarkdown, entitiesToHtml } from "../../helpers/entities";

const ERROR_MESSAGES: Record<string, string> = {
    "settings.setup_vvip.err_must_be_number":
        "**Input Tidak Valid!** Nilai harus berupa angka.",
    "settings.setup_vvip.err_must_be_chat_id":
        "**Input Tidak Valid!** Format Chat ID salah.",
};

function _back_layout(client: TelegramClient): any[] {
    return [
        [
            {
                text: "• Kembali ke Pengaturan •",
                callback_data: "settings",
                style: "blue",
                emoji: client.ns.emoji.id("back_arrow"),
            },
        ],
    ];
}

async function _reply(
    client: TelegramClient,
    callback_query: any,
    text: string,
    btn: any
): Promise<any> {
    if (callback_query.message.photo) {
        return await callback_query.edit_message_caption(text, { reply_markup: btn });
    }
    return await callback_query.edit_message_text(text, { reply_markup: btn });
}

export const set_start_photo_callback = command(
    (_c: any) => Filters.regex("^set_start_photo$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const chat_id = callback_query.from_user.id;
    await callback_query.message.delete();

    const back_btn = client.ns.telegram.button.build_button_grid(_back_layout(client));
    try {
        const ask_msg = await client.ask(
            chat_id,
            "Kirim foto baru untuk menyambut user.\n\nKetik `/batal` untuk membatalkan.",
            120
        );
        const text_value = String(ask_msg.message || ask_msg.text || "");
        if (text_value) {
            if (text_value.toLowerCase() === "/batal") {
                throw new UserCancelledError();
            }
            if (text_value.toLowerCase() === "/empty") {
                await ctx.db.removeVars(client.me.id, "start_photo_id");
                return await client.send_message(
                    chat_id,
                    `${client.ns.emoji.white_check_mark} **Sukses!** Foto /start telah dihapus.`,
                    { reply_markup: back_btn }
                );
            }
        }
        if (!ask_msg.photo) {
            return await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Gagal:** Pesan bukan foto.`,
                { reply_markup: back_btn }
            );
        }

        const photo_bytes = await client.downloadMedia(ask_msg);
        if (!photo_bytes || typeof photo_bytes !== "object") {
            return await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Gagal:** Foto tidak dapat diunduh.`,
                { reply_markup: back_btn }
            );
        }
        await ctx.db.setVars(client.me.id, "start_photo_id", photo_bytes);
        await client.send_message(
            chat_id,
            `${client.ns.emoji.white_check_mark} **Sukses!** Foto /start berhasil diperbarui.`,
            { reply_markup: back_btn }
        );
    } catch (e: any) {
        if (e instanceof UserCancelledError || e instanceof WaitTimeoutError) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Proses Dibatalkan**`,
                { reply_markup: back_btn }
            );
        } else {
            throw e;
        }
    }
});

export const set_start_text_callback = command(
    (_c: any) => Filters.regex("^set_start_text$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const chat_id = callback_query.from_user.id;
    await callback_query.message.delete();

    const back_btn = client.ns.telegram.button.build_button_grid(_back_layout(client));
    try {
        const prompt =
            `**${client.ns.emoji.writing_hand} Atur Teks Start**\n\n` +
            "Silakan kirim teks baru untuk pesan /start. Anda dapat menggunakan variabel " +
            "`{{mention}}` untuk menyapa pengguna.\n\n" +
            "Ketik `/empty` untuk menghapus teks kustom dan kembali ke default.\n\n" +
            "Ketik `/batal` untuk membatalkan.";
        const ask_text_msg = await client.ask(chat_id, prompt, 600);

        const raw_text = String(ask_text_msg.message || ask_text_msg.text || "");
        if (!raw_text) {
            return await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Gagal:** Pesan bukan teks.`,
                { reply_markup: back_btn }
            );
        }
        if (raw_text.toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        if (raw_text.toLowerCase() === "/empty") {
            await ctx.db.removeVars(client.me.id, "start_text_template");
            await ctx.db.removeVars(client.me.id, "start_text_template_html");
            return await client.send_message(
                chat_id,
                `${client.ns.emoji.white_check_mark} **Sukses!** Teks /start telah dihapus.`,
                { reply_markup: back_btn }
            );
        }

        const mdText =
            entitiesToMarkdown(raw_text, ask_text_msg.entities) || raw_text;
        const htmlText =
            entitiesToHtml(raw_text, ask_text_msg.entities) || raw_text;
        await ctx.db.setVars(client.me.id, "start_text_template", mdText);
        await ctx.db.setVars(
            client.me.id,
            "start_text_template_html",
            htmlText
        );
        await client.send_message(
            chat_id,
            `${client.ns.emoji.white_check_mark} **Sukses!** Teks /start berhasil diperbarui.`,
            { reply_markup: back_btn }
        );
    } catch (e: any) {
        if (e instanceof UserCancelledError || e instanceof WaitTimeoutError) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} **Proses Dibatalkan**`,
                { reply_markup: back_btn }
            );
        } else {
            throw e;
        }
    }
});

export const check_vvip_status_callback = command(
    (_c: any) => Filters.regex("^check_vvip_status$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            { show_alert: true }
        );
    }

    const chat_id = callback_query.message.chat.id;
    await callback_query.message.delete();

    const status_msg = await client.send_message(
        chat_id,
        `${client.ns.emoji.hourglass} Sedang Memeriksa Status Grup...\nMohon tunggu, proses ini mungkin memakan waktu.`
    );
    const vvip_list = (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    if (!vvip_list.length) {
        return await status_msg.edit(
            `${client.ns.emoji.cross_mark} Belum ada data VVIP.`
        );
    }

    let report_text = `${client.ns.emoji.mag} Laporan Status Grup VVIP\n\n`;
    for (const item of vvip_list) {
        const chat_id_target = item["chat_id_normal"];
        const name = item["name"];
        try {
            const chat = await client.get_chat(chat_id_target);
            const restrictions = (chat as any).restrictions;
            if (restrictions && restrictions.length) {
                const restriction = restrictions[0];
                const reason_text = `${restriction.reason}: ${restriction.text}`;
                report_text +=
                    `${client.ns.emoji.folder} Nama: ${name}\n` +
                    `${client.ns.emoji.bulb} Grup: ${chat.title}\n` +
                    `${client.ns.emoji.cross_mark} STATUS: BANNED/DIBATASI\n` +
                    `${client.ns.emoji.pencil} Alasan: ${reason_text}\n\n`;
            } else {
                const link =
                    (chat as any).inviteLink ||
                    (chat as any).invite_link ||
                    "N/A";
                report_text +=
                    `${client.ns.emoji.folder} Nama: ${name}\n` +
                    `${client.ns.emoji.bulb} Grup: ${chat.title}\n` +
                    `${client.ns.emoji.link} Link: ${link}\n` +
                    `${client.ns.emoji.white_check_mark} Status: Aman\n\n`;
            }
        } catch {
            report_text +=
                `${client.ns.emoji.folder} Nama: ${name}\n` +
                `${client.ns.emoji.cross_mark} Error: Tidak dapat mengakses grup (ID: ${chat_id_target}). Pastikan bot adalah admin.\n\n`;
        }

        if (report_text.length > 3500) {
            await client.send_message(chat_id, report_text);
            report_text = "";
        }
    }

    if (report_text) {
        await client.send_message(chat_id, report_text);
    }

    const btn = client.ns.telegram.button.build_button_grid(_back_layout(client));
    await status_msg.delete();
    await client.send_message(
        chat_id,
        `${client.ns.emoji.white_check_mark} Pemeriksaan Selesai.`,
        { reply_markup: btn }
    );
});

function _make_validator(): (
    msg: any,
    check_func: (t: string) => boolean,
    err_msg_key: string
) => string {
    const validate = (
        msg: any,
        check_func: (t: string) => boolean,
        err_msg_key: string
    ): string => {
        const text_value = String(msg.message || msg.text || "");
        if (text_value.toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        if (!check_func(text_value)) {
            throw new ValueError(
                ERROR_MESSAGES[err_msg_key] || "**Input tidak valid.**"
            );
        }
        return text_value;
    };
    return validate;
}

const _is_digit = (t: string): boolean => /^\d+$/.test(t);

const _is_chatid = (t: string): boolean => /^-?\d+$/.test(t);

export const setup_listvvip = command(
    (_c: any) => Filters.regex("^setup_listvvip$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const chat_id = callback_query.from_user.id;
    await callback_query.message.delete();

    try {
        const ask = (text: string): Promise<any> =>
            client.ask(
                chat_id,
                `${text}\n\nKetik \`/batal\` untuk membatalkan.`,
                600
            );

        const validate = _make_validator();

        const vvip_data: Record<string, any> = {};
        vvip_data["name"] = validate(
            await ask(
                `**${client.ns.emoji.pencil} Langkah 1/8: Nama Kategori**\nContoh: \`VVIP Bulanan\``
            ),
            () => true,
            ""
        );
        vvip_data["price"] = Math.trunc(
            Number(
                validate(
                    await ask(
                        `**${client.ns.emoji.money_bag} Langkah 2/8: Harga Normal**\nContoh: \`50000\``
                    ),
                    _is_digit,
                    "settings.setup_vvip.err_must_be_number"
                )
            )
        );
        vvip_data["duration"] = Math.trunc(
            Number(
                validate(
                    await ask(
                        `**${client.ns.emoji.hourglass} Langkah 3/8: Durasi Keanggotaan (Hari)**\nKirim \`0\` untuk akses permanen.`
                    ),
                    _is_digit,
                    "settings.setup_vvip.err_must_be_number"
                )
            )
        );
        vvip_data["chat_id_normal"] = Math.trunc(
            Number(
                validate(
                    await ask(
                        `**${client.ns.emoji.id_card} Langkah 4/8: Chat ID Grup Normal**\nContoh: \`-100123456789\`.`
                    ),
                    _is_chatid,
                    "settings.setup_vvip.err_must_be_chat_id"
                )
            )
        );
        vvip_data["promo_price"] = Math.trunc(
            Number(
                validate(
                    await ask(
                        `**${client.ns.emoji.party_popper} Langkah 5/8: Harga Promo**\nKirim \`0\` jika tidak ada harga promo.`
                    ),
                    _is_digit,
                    "settings.setup_vvip.err_must_be_number"
                )
            )
        );

        if (vvip_data["promo_price"] > 0) {
            vvip_data["chat_id_promo"] = Math.trunc(
                Number(
                    validate(
                        await ask(
                            `**${client.ns.emoji.id_card} Langkah 6/8: Chat ID Grup Promo**\nDiisi jika Harga Promo > 0.`
                        ),
                        _is_chatid,
                        "settings.setup_vvip.err_must_be_chat_id"
                    )
                )
            );
            const promo_text_msg = await client.ask(
                chat_id,
                `**${client.ns.emoji.pencil} Langkah 7/8: Teks Deskripsi Promo**\n` +
                    "Gunakan `{{name}}` dan `{{promo_price}}`.\n\n" +
                    "Ketik `/skip` untuk menggunakan teks default.\n\n" +
                    "Ketik `/batal` untuk membatalkan.",
                600
            );
            const promo_text_value = String(
                promo_text_msg.message || promo_text_msg.text || ""
            );
            if (promo_text_value.toLowerCase() === "/batal") {
                throw new UserCancelledError();
            }
            vvip_data["promo_text"] =
                promo_text_value.toLowerCase() === "/skip"
                    ? ""
                    : promo_text_value;
        } else {
            vvip_data["chat_id_promo"] = 0;
            vvip_data["promo_text"] = "";
        }

        const normal_text_msg = await client.ask(
            chat_id,
            `**${client.ns.emoji.pencil} Langkah 8/8: Teks Deskripsi Normal**\n` +
                "Gunakan `{{name}}` and `{{price}}`.\n\n" +
                "Ketik `/skip` untuk menggunakan teks default.\n\n" +
                "Ketik `/batal` untuk membatalkan.",
            600
        );
        const normal_text_value = String(
            normal_text_msg.message || normal_text_msg.text || ""
        );
        if (normal_text_value.toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        vvip_data["normal_text"] =
            normal_text_value.toLowerCase() === "/skip"
                ? ""
                : normal_text_value;

        await ctx.db.setListVars(client.me.id, "list_vvip", vvip_data);
        await client.send_message(
            chat_id,
            `${client.ns.emoji.white_check_mark} **Sukses!**\nPaket VVIP **${vvip_data["name"]}** berhasil ditambahkan.`
        );
    } catch (e: any) {
        if (e instanceof UserCancelledError) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} Setup paket VVIP dibatalkan.`
            );
        } else if (e instanceof WaitTimeoutError || e instanceof ValueError) {
            await client.send_message(
                chat_id,
                `**Input Tidak Valid / Timeout**\nProses dibatalkan.\n\`${e.message || e}\``
            );
        } else {
            throw e;
        }
    }
});

async function _build_item_selector(
    client: TelegramClient,
    callback_query: any,
    key_attr: string,
    action: string,
    callback_prefix: string,
    emoji_id: string,
    header_emoji: any,
    header_text: string,
    body_text: string,
    empty_text: string
): Promise<void> {
    const vvip_list = (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    const back_row = _back_layout(client)[0];

    if (!vvip_list.length) {
        const text = empty_text;
        const btn = client.ns.telegram.button.build_button_grid([back_row]);
        return await _reply(client, callback_query, text, btn);
    }

    if (!ctx[key_attr]) {
        ctx[key_attr] = {};
    }

    const layout: any[] = [];
    let button_row: any[] = [];
    const mapping = ctx[key_attr];
    for (const item of vvip_list) {
        const name = item["name"] || "Tanpa Nama";
        const item_id = randomUUID().slice(0, 8);
        mapping[item_id] = name;
        button_row.push({
            text: `${action} ${name}`,
            callback_data: `${callback_prefix} ${item_id}`,
            style: action.startsWith("🗑") ? "red" : "blue",
            emoji: client.ns.emoji.id(emoji_id),
        });
        if (button_row.length === 2) {
            layout.push(button_row);
            button_row = [];
        }
    }
    if (button_row.length) {
        layout.push(button_row);
    }
    layout.push(back_row);

    const text = `**${header_emoji} ${header_text}**\n\n${body_text}`;
    const btn = client.ns.telegram.button.build_button_grid(layout);
    await _reply(client, callback_query, text, btn);
}

export const delete_listvvip = command(
    (_c: any) => Filters.regex("^delete_listvvip$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }
    await _build_item_selector(
        client,
        callback_query,
        "vip_list",
        "🗑️ Hapus",
        "delete_vvip",
        "minus",
        client.ns.emoji.minus,
        "Hapus Paket VVIP",
        "Pilih paket VVIP yang ingin Anda hapus.",
        `${client.ns.emoji.white_check_mark} Tidak ada paket VVIP untuk dihapus.`
    );
});

export const confirm_delete_vvip = command(
    (_c: any) => Filters.regex("^delete_vvip\\s(.+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const item_id = callback_query.data_string.split(" ", 2)[1];
    if (!ctx["vip_list"] || !ctx["vip_list"][item_id]) {
        return await callback_query.answer(
            "Sesi tidak ditemukan atau kedaluwarsa.",
            { show_alert: true }
        );
    }

    const name = ctx["vip_list"][item_id];
    const vvip_list = (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    const item_to_remove = vvip_list.find(
        (item: any) => item["name"] === name
    );
    if (item_to_remove) {
        await ctx.db.removeListVars(client.me.id, "list_vvip", item_to_remove);
        await callback_query.answer("Kategori berhasil dihapus.", {
            show_alert: true,
        });
    }

    await delete_listvvip(client, callback_query);
});

export const edit_price_listvvip_callback = command(
    (_c: any) => Filters.regex("^edit_price_listvvip$"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }
    await _build_item_selector(
        client,
        callback_query,
        "vip_list_edit",
        "✏️ Edit",
        "edit_vvip_price",
        "pencil",
        client.ns.emoji.pencil,
        "Edit Harga VVIP",
        "Pilih paket VVIP yang ingin Anda ubah harganya.",
        `${client.ns.emoji.cross_mark} Belum ada paket VVIP.`
    );
});

export const edit_vvip_price_callback = command(
    (_c: any) => Filters.regex("^edit_vvip_price\\s(.+)"),
    "callback"
)(async (client: TelegramClient, callback_query: any) => {
    if (!(await is_bot_owner(client, callback_query.from_user.id))) {
        return;
    }

    const chat_id = callback_query.from_user.id;
    const item_id = callback_query.data_string.split(" ", 2)[1];

    if (!ctx["vip_list_edit"] || !ctx["vip_list_edit"][item_id]) {
        return await callback_query.answer(
            "Sesi tidak ditemukan atau kedaluwarsa.",
            { show_alert: true }
        );
    }

    const name = ctx["vip_list_edit"][item_id];
    const vvip_list = (await ctx.db.getListVars(client.me.id, "list_vvip")) || [];
    const old_item = vvip_list.find((item: any) => item["name"] === name);
    if (!old_item) {
        return await callback_query.answer("Paket VVIP tidak ditemukan.", {
            show_alert: true,
        });
    }

    await callback_query.message.delete();
    try {
        const ask = (text: string): Promise<any> =>
            client.ask(
                chat_id,
                `${text}\n\nKetik \`/batal\` untuk membatalkan.`,
                300
            );

        const new_price_msg = await ask(
            `**${client.ns.emoji.money_bag} Masukkan Harga Normal Baru**\nContoh: \`50000\`\n\nHarga sebelumnya: \`${old_item["price"] || 0}\``
        );
        const new_price_text = String(
            new_price_msg.message || new_price_msg.text || ""
        );
        if (new_price_text.toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        if (!/^\d+$/.test(new_price_text)) {
            throw new ValueError("");
        }
        const new_price = Math.trunc(Number(new_price_text));

        const new_promo_msg = await ask(
            `**${client.ns.emoji.party_popper} Masukkan Harga Promo Baru**\nContoh: \`25000\` atau \`0\`.\n\nHarga sebelumnya: \`${old_item["promo_price"] || 0}\``
        );
        const new_promo_text = String(
            new_promo_msg.message || new_promo_msg.text || ""
        );
        if (new_promo_text.toLowerCase() === "/batal") {
            throw new UserCancelledError();
        }
        if (!/^\d+$/.test(new_promo_text)) {
            throw new ValueError("");
        }
        const new_promo = Math.trunc(Number(new_promo_text));

        await ctx.db.removeListVars(client.me.id, "list_vvip", old_item);
        old_item["price"] = new_price;
        old_item["promo_price"] = new_promo;
        await ctx.db.setListVars(client.me.id, "list_vvip", old_item);
        delete ctx["vip_list_edit"][item_id];

        await client.send_message(
            chat_id,
            `${client.ns.emoji.white_check_mark} **Sukses!**\nHarga paket VVIP **${name}** berhasil diubah.`
        );
    } catch (e: any) {
        if (e instanceof UserCancelledError) {
            await client.send_message(
                chat_id,
                `${client.ns.emoji.cross_mark} Perubahan dibatalkan.`
            );
        } else if (e instanceof WaitTimeoutError || e instanceof ValueError) {
            await client.send_message(
                chat_id,
                `**Input Tidak Valid / Timeout**\nProses dibatalkan.\n\`${e.message || e}\``
            );
        } else {
            throw e;
        }
    }
});