import asyncio
from time import time

import pyrogram

from .. import ctx


async def verify_user_join(client, user, chat_id, link_msg):
    verification_timeout = 3600
    start_time = time()
    is_joined = False

    while time() - start_time < verification_timeout:
        try:
            member = await client.get_chat_member(chat_id, user.id)

            if member.status not in [
                pyrogram.enums.ChatMemberStatus.LEFT,
                pyrogram.enums.ChatMemberStatus.BANNED,
            ]:
                is_joined = True

                ctx.log.print(
                    f"{ctx.log.GREEN}User {user.id} berhasil bergabung ke {chat_id}."
                )
                break

        except pyrogram.errors.UserNotParticipant:
            await asyncio.sleep(15)

        except Exception as e:
            ctx.log.print(f"Error verifikasi join {user.id}: {e}")
            break

    try:
        await link_msg.delete()
    except Exception:
        pass

    if not is_joined:
        await client.send_rich_message(
            user.id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('exclamation')} **Peringatan!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Link undangan Anda telah kedaluwarsa'], ['Sebab', 'Anda tidak bergabung dalam 60 menit']])}"
                )
            ),
        )


async def verify_user_join_multiple(client, user, invite_payloads, link_msg):
    verification_timeout = 3600
    start_time = time()

    while time() - start_time < verification_timeout:
        pending_payloads = []

        for payload in invite_payloads:
            chat_id = payload.get("chat_id")

            try:
                member = await client.get_chat_member(chat_id, user.id)

                if member.status in [
                    pyrogram.enums.ChatMemberStatus.LEFT,
                    pyrogram.enums.ChatMemberStatus.BANNED,
                ]:
                    pending_payloads.append(payload)

            except pyrogram.errors.UserNotParticipant:
                pending_payloads.append(payload)

            except Exception as e:
                ctx.log.print(f"Error verifikasi multi-join {user.id}: {e}")
                pending_payloads.append(payload)

        if not pending_payloads:
            try:
                await link_msg.delete()
            except Exception:
                pass

            return

        await asyncio.sleep(15)

    pending_lines = []

    for item in pending_payloads:
        pending_lines.append(f"- {item.get('name')}: {item.get('link')}")

    try:
        await client.send_rich_message(
            user.id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('exclamation')} **Belum Join Semua Grup**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Anda belum join ke semua grup VIP dalam waktu 60 menit'], ['Aksi', 'Silakan join grup berikut']])}\n\n"
                    + "\n".join(pending_lines)
                )
            ),
            protect_content=True,
        )
    except Exception:
        pass


def _get_all_vvip_items(vvip_list):
    selected_items = []

    for index, item in enumerate(vvip_list):
        price = int(item.get("price", 0) or 0)
        chat_id_normal = item.get("chat_id_normal")

        if price > 0 and chat_id_normal:
            selected_items.append(
                {
                    "index": index,
                    "name": item.get("name", f"Paket {index + 1}"),
                    "price": price,
                    "chat_id": chat_id_normal,
                    "duration": item.get("duration", 0),
                }
            )

    return selected_items
