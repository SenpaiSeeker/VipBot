import pyrogram
from pyrogram import enums, filters

from helpers.modules import Modules

from .. import is_bot_owner

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

    owner_id = await client.db.getVars(client.me.id, "owner_id") or client.owner_id
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
            [
                {
                    "text": "❌ Tolak & Keluar",
                    "callback_data": f"reject_chat {chat.id}",
                    "style": "red",
                    "emoji": client.ns.emoji.id("cross_mark"),
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
        client.log.print(f"Gagal mengirim notifikasi bot ditambahkan ke chat: {e}")


async def reject_chat_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    try:
        chat_id = int(callback_query.data.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        return await callback_query.answer("Chat ID tidak valid.", show_alert=True)

    try:
        await client.leave_chat(chat_id)
    except Exception as e:
        client.log.print(f"Gagal keluar dari chat {chat_id}: {e}")
        return await callback_query.answer(
            "Gagal keluar dari chat. Coba lagi.", show_alert=True
        )

    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.answer("Bot berhasil keluar dari chat.")
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('white_check_mark')} **Chat Ditolak**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Bot sudah keluar dari chat'], ['Chat ID', f'`{chat_id}`']])}"
            )
        ),
        reply_markup=back_btn,
    )


class SettingsChatAdded(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_chat_member_updated(bot_added_filter)(
            self.handle(notify_bot_added_to_chat)
        )
        self.client.on_callback_query(filters.regex(r"^reject_chat\s(-?\d+)$"))(
            self.handle(reject_chat_callback)
        )
