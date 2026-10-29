import pyrogram
from pyrogram import enums, filters

from .. import command, ctx

_ACTIVE_STATUSES = {
    enums.ChatMemberStatus.MEMBER,
    enums.ChatMemberStatus.ADMINISTRATOR,
    enums.ChatMemberStatus.OWNER,
}

_TARGET_CHAT_TYPES = {
    enums.ChatType.GROUP,
    enums.ChatType.SUPERGROUP,
    enums.ChatType.CHANNEL,
    enums.ChatType.FORUM,
}

_CHAT_TYPE_LABELS = {
    enums.ChatType.GROUP: "Grup",
    enums.ChatType.SUPERGROUP: "Supergrup",
    enums.ChatType.CHANNEL: "Channel",
    enums.ChatType.FORUM: "Forum",
}


def _bot_added_filter(_, client, update):
    new_member = getattr(update, "new_chat_member", None)
    user = getattr(new_member, "user", None)
    return bool(user and user.id == client.me.id)


bot_added_filter = filters.create(_bot_added_filter)


@command(lambda ctx: bot_added_filter, handler_type="chat_member")
async def notify_bot_added_to_chat(client, update):
    new_member = getattr(update, "new_chat_member", None)
    old_member = getattr(update, "old_chat_member", None)

    if not new_member or new_member.status not in _ACTIVE_STATUSES:
        return

    if old_member and old_member.status in _ACTIVE_STATUSES:
        return

    chat = update.chat
    if chat.type not in _TARGET_CHAT_TYPES:
        return

    owner_id = await ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id
    chat_type = _CHAT_TYPE_LABELS.get(chat.type, "Chat")
    chat_title = chat.title or chat.username or str(chat.id)

    try:
        bot_mention = client.ns.telegram.arg.getMention(client.me, md=True)
        actor_mention = client.ns.telegram.arg.getMention(update.from_user, md=True)
        notification_text = (
            f"{client.ns.emoji.md('bell')} **Bot Ditambahkan ke {chat_type}**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Bot', bot_mention], ['Nama', f'**{chat_title}**'], ['Tipe', chat_type], ['Chat ID', f'`{chat.id}`'], ['Ditambahkan Oleh', actor_mention]])}\n\n"
            f"Pilih tindakan untuk {chat_type.lower()} ini."
        )

        layout = [
            [
                {
                    "text": "➕ Add VVIP",
                    "callback_data": f"setup_listvvip_from_chat {chat.id}",
                    "style": "green",
                    "emoji": client.ns.emoji.id("plus"),
                }
            ],
            [
                {
                    "text": "🔔 Add Notifikasi Payment",
                    "callback_data": f"set_notif_payment {chat.id}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("bell"),
                }
            ],
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await client.send_rich_message(
            owner_id,
            pyrogram.types.InputRichMessage(markdown=notification_text),
            reply_markup=btn,
        )
    except Exception as e:
        ctx.log.print(f"Gagal mengirim notifikasi bot ditambahkan ke chat: {e}")
