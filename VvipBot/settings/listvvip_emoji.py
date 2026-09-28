import asyncio

import pyrogram
from pyrogram import filters

from .. import (
    LIST_VVIP_ICON_DEFAULT,
    _sanitize_emoji_id,
    command,
    ctx,
    get_list_vvip_icon,
    is_bot_owner,
    listen,
)

KIND_LABEL = {
    "normal": "Icon Normal",
    "promo": "Icon Promo",
}


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


def build_menu_layout():
    return [
        [
            {
                "text": "📂 Ubah Icon Normal",
                "callback_data": "set_listvvip_icon_normal",
                "style": "blue",
                "emoji": "open_folder",
            },
            {
                "text": "🎉 Ubah Icon Promo",
                "callback_data": "set_listvvip_icon_promo",
                "style": "green",
                "emoji": "party_popper",
            },
        ],
        [
            {
                "text": "♻️ Kembalikan ke Bawaan",
                "callback_data": "reset_listvvip_icon",
                "style": "red",
                "emoji": "repeat",
            }
        ],
        build_back_layout()[0],
    ]


def extract_custom_emoji_id(message):
    for entity in getattr(message, "entities", None) or []:
        if entity.type != pyrogram.enums.MessageEntityType.CUSTOM_EMOJI:
            continue

        emoji_id = _sanitize_emoji_id(getattr(entity, "custom_emoji_id", None))
        if emoji_id:
            return emoji_id

    return None


async def render_list_vvip_icon_menu(client, callback_query):
    normal_icon = await get_list_vvip_icon(client, "normal")
    promo_icon = await get_list_vvip_icon(client, "promo")
    saved = await ctx.db.getVars(client.me.id, "list_vvip_icon")
    saved = saved if isinstance(saved, dict) else {}

    normal_note = f"kustom `{saved['normal']}`" if saved.get("normal") else "bawaan"
    promo_note = f"kustom `{saved['promo']}`" if saved.get("promo") else "bawaan"

    layout = build_menu_layout()
    for row in layout:
        for btn in row:
            btn["emoji"] = client.ns.emoji.id(btn["emoji"])

    btn = client.ns.telegram.button.build_button_grid(layout)

    text = (
        f"**{client.ns.emoji.art} Atur Icon List VVIP**\n\n"
        f"Kustomisasi icon tombol pada daftar paket VVIP "
        f"(icon `{client.ns.emoji.open_folder}` normal dan "
        f"`{client.ns.emoji.party_popper}` promo).\n\n"
        f"**Icon Normal:** `{normal_icon}` ({normal_note})\n"
        f"**Icon Promo:** `{promo_icon}` ({promo_note})\n\n"
        f"Kirim **custom emoji** atau **ID custom emoji** yang ingin dipakai.\n"
        f"Jika tidak diatur, bot akan memakai **ID bawaan**."
    )

    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)


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

    await render_list_vvip_icon_menu(client, callback_query)


@command(
    lambda ctx: filters.regex("^set_listvvip_icon_(normal|promo)$"),
    handler_type="callback",
)
async def set_listvvip_icon_prompt(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    kind = callback_query.matches[0].group(1)
    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    layout = build_back_layout("• Kembali ke Menu Icon •")
    for btn in layout[0]:
        btn["emoji"] = client.ns.emoji.id(btn["emoji"])
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    default_id = client.ns.emoji.id(LIST_VVIP_ICON_DEFAULT[kind])

    try:
        prompt = (
            f"**{client.ns.emoji.art} Atur {KIND_LABEL[kind]}**\n\n"
            f"Kirim **custom emoji** yang ingin digunakan, "
            f"atau tulis **ID custom emoji** secara langsung.\n\n"
            f"ID bawaan saat ini: `{default_id}`\n\n"
            f"Ketik `/default` untuk kembali ke ID bawaan.\n"
            f"Ketik `/batal` untuk membatalkan."
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
        else:
            emoji_id = extract_custom_emoji_id(ask_msg) or _sanitize_emoji_id(
                ask_msg.text
            )

            if not emoji_id:
                return await client.send_message(
                    chat_id,
                    f"{client.ns.emoji.cross_mark} **Gagal:** "
                    f"Tidak ada custom emoji yang detected.\n\n"
                    f"Kirim pesan yang berisi **custom emoji**, "
                    f"atau tulis **ID custom emoji** berupa angka.",
                    reply_markup=back_btn,
                )

        saved = await ctx.db.getVars(client.me.id, "list_vvip_icon")
        saved = saved if isinstance(saved, dict) else {}

        if emoji_id:
            saved[kind] = emoji_id
        else:
            saved.pop(kind, None)

        if saved:
            await ctx.db.setVars(client.me.id, "list_vvip_icon", saved)
        else:
            await ctx.db.removeVars(client.me.id, "list_vvip_icon")

        result = await get_list_vvip_icon(client, kind)
        status = "diubah" if emoji_id else "dikembalikan ke ID bawaan"

        await client.send_message(
            chat_id,
            f"{client.ns.emoji.white_check_mark} **Sukses!**\n"
            f"{KIND_LABEL[kind]} daftar VVIP {status}.\n\n"
            f"ID aktif: `{result}`",
            reply_markup=back_btn,
        )

    except (listen.UserCancelled, asyncio.TimeoutError):
        await client.send_message(
            chat_id,
            f"{client.ns.emoji.cross_mark} **Proses Dibatalkan**",
            reply_markup=back_btn,
        )


@command(
    lambda ctx: filters.regex("^reset_listvvip_icon$"),
    handler_type="callback",
)
async def reset_listvvip_icon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    await ctx.db.removeVars(client.me.id, "list_vvip_icon")
    await callback_query.answer(
        "Icon list VVIP dikembalikan ke ID bawaan.",
        show_alert=True,
    )

    await render_list_vvip_icon_menu(client, callback_query)
