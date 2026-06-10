import asyncio
from datetime import datetime, timedelta, timezone

from telethon import events, functions

from .. import command, ctx, is_bot_owner


@command(lambda ctx: events.CallbackQuery(pattern=b"^list_gift$"))
async def list_gift_handler(client, event):
    em = client.ns.emoji
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []

    if not vvip_list:
        return await event.answer(
            "Tidak ada paket VVIP tersedia untuk dikirim sebagai hadiah.", alert=True
        )

    layout = []
    for index, item in enumerate(vvip_list):
        name = item.get("name", f"Paket {index + 1}")
        layout.append(
            [
                {
                    "text": f"🎁 Kirim '{name}' ke Teman",
                    "callback_data": f"gift_send_{index}",
                    "style": "primary",
                    "emoji": 5199749070830197566,
                },
                {
                    "text": f"🎯 Klaim '{name}' Sendiri",
                    "callback_data": f"gift_claim_self_{index}",
                    "style": "primary",
                    "emoji": 5373012449597335010,
                },
            ]
        )

    layout.append([{"text": "◀️ Kembali", "callback_data": "start", "style": "primary", "emoji": 5373098009640836781}])
    btn = client.ns.telegram.button.build_button_grid(layout)

    text = (
        f"{em.gift} <b>Hadiah Akses VIP</b>\n\n"
        f"Anda telah menerima hadiah akses VIP gratis!\n\n"
        f"Pilih aksi di bawah ini:"
    )
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^gift_claim_self_"))
async def gift_claim_self_handler(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return await event.answer(
            "⛔ Anda tidak memiliki akses ke menu ini.", alert=True
        )

    payload = event.data.decode("utf-8")
    item_index = int(payload.split("_")[-1])
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []

    try:
        item = vvip_list[item_index]
    except IndexError:
        return await event.answer("Paket tidak ditemukan.", alert=True)

    name = item.get("name")
    target_chat_id = item.get("chat_id_normal")

    if not target_chat_id:
        return await event.answer("Chat ID tidak valid.", alert=True)

    try:
        expire_date_link = datetime.now(timezone.utc) + timedelta(minutes=60)
        res = await client(
            functions.messages.ExportChatInviteRequest(
                peer=await client.get_input_entity(target_chat_id),
                expire_date=expire_date_link,
                usage_limit=1,
            )
        )
        link = res.link

        member_data = {
            "user_id": sender.id,
            "vvip_name": name,
            "join_date": datetime.now(timezone.utc).isoformat(),
            "payment_type": "gift",
            "chat_id_kick": target_chat_id,
        }
        duration = item.get("duration", 0)
        if duration > 0:
            expiry_date = datetime.now(timezone.utc) + timedelta(days=duration)
            member_data["expiry_date"] = expiry_date.isoformat()

        await ctx.db.setListVars(client.uid, "vvip_members", member_data)

        await event.edit(
            f"{em.party_popper} <b>Hadiah Berhasil Diklaim!</b>\n\n"
            f"Berikut link akses Anda untuk paket <b>{name}</b>:\n\n"
            f"{link}\n\n"
            f"{em.alarm_clock} Link berlaku 1 kali klik dan kedaluwarsa dalam 60 menit.",
            parse_mode="html",
        )
    except Exception as e:
        await event.answer(f"❌ Gagal klaim: {e}", alert=True)


@command(lambda ctx: events.CallbackQuery(pattern=b"^gift_send_"))
async def gift_send_ask_handler(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return await event.answer(
            "⛔ Anda tidak memiliki akses ke menu ini.", alert=True
        )

    payload = event.data.decode("utf-8")
    item_index = int(payload.split("_")[-1])
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []

    try:
        item = vvip_list[item_index]
    except IndexError:
        return await event.answer("Paket tidak ditemukan.", alert=True)

    await event.delete()
    name = item.get("name")

    try:
        ask_msg = await client.ask(
            sender.id,
            f"{em.busts_in_silhouette} Masukkan <b>Username atau ID</b> teman yang ingin Anda hadiahi paket <b>{name}</b>.",
            parse_mode="html",
        )
        recipient_input = ask_msg.text.strip()

        try:
            recipient = await client.get_entity(
                int(recipient_input)
                if recipient_input.lstrip("-").isdigit()
                else recipient_input
            )
        except Exception:
            raise ValueError(f"Pengguna '{recipient_input}' tidak ditemukan.")

        target_chat_id = item.get("chat_id_normal")
        if not target_chat_id:
            raise ValueError("Chat ID tidak valid.")

        expire_date_link = datetime.now(timezone.utc) + timedelta(minutes=60)
        res = await client(
            functions.messages.ExportChatInviteRequest(
                peer=await client.get_input_entity(target_chat_id),
                expire_date=expire_date_link,
                usage_limit=1,
            )
        )
        link = res.link

        member_data = {
            "user_id": recipient.id,
            "vvip_name": name,
            "join_date": datetime.now(timezone.utc).isoformat(),
            "payment_type": "gift",
            "chat_id_kick": target_chat_id,
        }
        duration = item.get("duration", 0)
        if duration > 0:
            expiry_date = datetime.now(timezone.utc) + timedelta(days=duration)
            member_data["expiry_date"] = expiry_date.isoformat()

        await ctx.db.setListVars(client.uid, "vvip_members", member_data)

        await client.send_message(
            recipient.id,
            f"{em.gift} <b>Anda Mendapat Hadiah!</b>\n\n"
            f"Seseorang telah menghadiahi Anda akses ke paket VVIP <b>{name}</b>.\n\n"
            f"Berikut link akses Anda:\n{link}\n\n"
            f"{em.alarm_clock} Link berlaku 1 kali klik dan kedaluwarsa dalam 60 menit.",
            parse_mode="html",
        )

        await client.send_message(
            sender.id,
            f"{em.white_check_mark} <b>Berhasil!</b>\n"
            f"Hadiah akses <b>{name}</b> telah berhasil dikirim ke "
            f"{client.ns.telegram.arg.getMention(recipient)}.",
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        await client.send_message(
            sender.id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses pengiriman hadiah dibatalkan.",
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(
            sender.id,
            f"{em.cross_mark} <b>Gagal Mengirim Hadiah:</b> <code>{e}</code>",
            parse_mode="html",
        )
