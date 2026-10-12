import asyncio
import uuid

import pyrogram
from pyrogram import filters

from .. import (
    LIST_VVIP_ICON_BUY_ALL_KEY,
    LIST_VVIP_ICON_DEFAULT,
    _sanitize_emoji_id,
    command,
    ctx,
    get_list_vvip_icons,
    is_bot_owner,
    listen,
)


def build_back_layout(label="• Kembali ke Pengaturan •"):
    return [
        [
            {
                "text": label,
                "callback_data": "settings",
                "style": "blue",
                "emoji": "back_arrow",
            }
        ]
    ]


def extract_custom_emoji(message):
    for entity in getattr(message, "entities", None) or []:
        if entity.type != pyrogram.enums.MessageEntityType.CUSTOM_EMOJI:
            continue

        emoji_id = _sanitize_emoji_id(getattr(entity, "custom_emoji_id", None))
        if not emoji_id:
            continue

        offset = getattr(entity, "offset", 0)
        length = getattr(entity, "length", 0)
        char = (message.text or "")[offset : offset + length]

        return emoji_id, char

    return None, None


async def render_list_vvip_icon_menu(client, callback_query):
    vvip_list = await ctx.db.getListVars(client.me.id, "list_vvip") or []
    icons = await get_list_vvip_icons(client)

    if not hasattr(ctx, "vip_list_icon"):
        ctx.vip_list_icon = {}

    layout = []
    if not vvip_list:
        table = client.ns.table
        empty_rows = [
            ["Jumlah Paket", "`0`"],
            ["Status", "Belum ada paket VVIP"],
            ["Saran", "Tambahkan paket terlebih dahulu"],
        ]
        text = (
            f"{client.ns.emoji.md('cross_mark')} **Daftar Paket VVIP**\n\n"
            f"{table.md(['Info', 'Nilai'], empty_rows)}"
        )
        back_row = build_back_layout()[0]
        back_row[0]["emoji"] = client.ns.emoji.id(back_row[0]["emoji"])
        layout.append(back_row)
        btn = client.ns.telegram.button.build_button_grid(layout)

        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=btn,
        )

    button_row = []
    for item in vvip_list:
        name = item.get("name", "Tanpa Nama")
        item_id = uuid.uuid4().hex[:8]
        ctx.vip_list_icon[item_id] = item

        status_icon = (
            icons[name]["id"]
            if name in icons
            else client.ns.emoji.id(LIST_VVIP_ICON_DEFAULT["normal"])
        )

        button_row.append(
            {
                "text": f"{name} ✓" if name in icons else name,
                "callback_data": f"set_listvvip_icon_item {item_id}",
                "style": "blue",
                "emoji": status_icon,
            }
        )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []

    if button_row:
        layout.append(button_row)

    buy_all_entry = icons.get(LIST_VVIP_ICON_BUY_ALL_KEY)
    buy_all_icon = (
        buy_all_entry["id"] if buy_all_entry else client.ns.emoji.id("shopping_cart")
    )
    buy_all_label = "Ambil Semua VIP ✓" if buy_all_entry else "Ambil Semua VIP"
    layout.append(
        [
            {
                "text": buy_all_label,
                "callback_data": "set_listvvip_icon_item buy_all",
                "style": "green",
                "emoji": buy_all_icon,
            }
        ]
    )

    layout.append(
        [
            {
                "text": "♻️ Kembalikan Semua ke Bawaan",
                "callback_data": "reset_listvvip_icon",
                "style": "red",
                "emoji": "repeat",
            }
        ]
    )
    layout.append(build_back_layout()[0])

    for row in layout:
        for btn_cfg in row:
            if not isinstance(btn_cfg.get("emoji"), int):
                btn_cfg["emoji"] = client.ns.emoji.id(btn_cfg["emoji"])

    btn = client.ns.telegram.button.build_button_grid(layout)

    text = (
        f"{client.ns.emoji.md('art')} **Atur Icon List VVIP**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], [['Tujuan', 'Kustomisasi icon tiap paket VVIP secara individu'], ['Cara', 'Pilih paket berdasarkan nama, lalu kirim custom emoji atau ID custom emoji'], ['Icon Bawaan', f"{client.ns.emoji.md(LIST_VVIP_ICON_DEFAULT['normal'])} normal / {client.ns.emoji.md(LIST_VVIP_ICON_DEFAULT['promo'])} promo"], ['Penerapan', 'Icon kustom dipakai di tombol paket pada menu daftar VVIP'], ['Tambahan', 'Tombol Ambil Semua VIP juga bisa diubah iconnya']])}"
    )

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


@command(
    lambda ctx: filters.regex("^set_listvvip_icon$"),
    handler_type="callback",
)
async def set_listvvip_icon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    if not hasattr(ctx, "vip_list_icon"):
        ctx.vip_list_icon = {}

    await render_list_vvip_icon_menu(client, callback_query)


@command(
    lambda ctx: filters.regex("^set_listvvip_icon_item\\s(.+)"),
    handler_type="callback",
)
async def set_listvvip_icon_item_prompt(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    _, item_id = callback_query.data.split(" ", 1)
    if item_id == "buy_all":
        name = LIST_VVIP_ICON_BUY_ALL_KEY
        display_name = "Ambil Semua VIP"
    else:
        if not hasattr(ctx, "vip_list_icon") or item_id not in ctx.vip_list_icon:
            return await callback_query.answer(
                "Sesi tidak ditemukan atau kedaluwarsa. Buka kembali menu dari Pengaturan.",
                show_alert=True,
            )

        item = ctx.vip_list_icon[item_id]
        name = item.get("name", "Tanpa Nama")
        display_name = name

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    layout = build_back_layout("• Kembali ke Menu Icon •")
    layout[0][0]["callback_data"] = "set_listvvip_icon"
    for btn_cfg in layout[0]:
        btn_cfg["emoji"] = client.ns.emoji.id(btn_cfg["emoji"])
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    default_id = client.ns.emoji.id(LIST_VVIP_ICON_DEFAULT["normal"])
    current_id = await ctx.db.getVars(client.me.id, "list_vvip_icon")
    raw_current = current_id.get(name) if isinstance(current_id, dict) else None
    if isinstance(raw_current, dict):
        current_display = f"`{raw_current.get('id')}`"
    elif raw_current:
        current_display = f"`{raw_current}`"
    else:
        current_display = "bawaan"

    try:
        prompt = (
            f"**{client.ns.emoji.md('art')} Atur Icon Paket `{display_name}`**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Icon Saat Ini', f'{current_display}'], ['ID Bawaan', f'`{default_id}`'], ['Instruksi', 'Kirim **custom emoji** yang ingin digunakan, atau tulis **ID custom emoji** secara langsung'], ['Default', 'Ketik `/default` untuk kembali ke ID bawaan'], ['Batal', 'Ketik `/batal` untuk membatalkan']])}"
        )
        ask_msg = await client.ask(chat_id, prompt, timeout=600)

        if ask_msg.text and ask_msg.text.strip().lower() in ("/batal", "/cancel"):
            raise listen.UserCancelled

        if ask_msg.text and ask_msg.text.strip().lower() in (
            "/default",
            "/empty",
            "/none",
            "/reset",
        ):
            emoji_id = None
            emoji_char = None
        else:
            emoji_id, emoji_char = extract_custom_emoji(ask_msg)
            if not emoji_id:
                emoji_id = _sanitize_emoji_id(ask_msg.text)
                emoji_char = None

            if not emoji_id:
                return await client.send_rich_message(
                    chat_id,
                    pyrogram.types.InputRichMessage(
                        markdown=(
                            f"{client.ns.emoji.md('cross_mark')} **Gagal: Custom Emoji Tidak Ditemukan**\n\n"
                            f"{client.ns.table.md(['Info', 'Keterangan'], [['Status', 'Tidak ada custom emoji terdeteksi'], ['Solusi', 'Kirim pesan berisi custom emoji'], ['Alternatif', 'Tulis ID custom emoji berupa angka']])}"
                        )
                    ),
                    reply_markup=back_btn,
                )

        saved = await ctx.db.getVars(client.me.id, "list_vvip_icon")
        saved = saved if isinstance(saved, dict) else {}

        if emoji_id:
            if emoji_char:
                saved[name] = {"id": emoji_id, "char": emoji_char}
            else:
                saved[name] = emoji_id
        else:
            saved.pop(name, None)

        if saved:
            await ctx.db.setVars(client.me.id, "list_vvip_icon", saved)
        else:
            await ctx.db.removeVars(client.me.id, "list_vvip_icon")

        status = "diubah" if emoji_id else "dikembalikan ke ID bawaan"
        result_display = (
            (client.ns.emoji.md(emoji_char) if emoji_char else f"`{emoji_id}`")
            if emoji_id
            else client.ns.emoji.md(LIST_VVIP_ICON_DEFAULT["normal"])
        )

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Sukses!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Paket', f'**{display_name}**'], ['Status', f'Icon {status}'], ['ID Aktif', f'{result_display}']])}"
                )
            ),
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Proses Dibatalkan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Dibatalkan']])}"
                )
            ),
            reply_markup=back_btn,
        )


@command(
    lambda ctx: filters.regex("^reset_listvvip_icon$"),
    handler_type="callback",
)
async def reset_listvvip_icon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    await ctx.db.removeVars(client.me.id, "list_vvip_icon")
    await callback_query.answer(
        "Semua icon list VVIP dikembalikan ke ID bawaan.",
        show_alert=True,
    )

    await render_list_vvip_icon_menu(client, callback_query)
