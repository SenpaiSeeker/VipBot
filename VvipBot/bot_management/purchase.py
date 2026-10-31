import asyncio
from datetime import datetime, timedelta, timezone
from weakref import WeakValueDictionary

import pyrogram
from pyrogram import filters

from config import BACKUP_BOT
from helpers import parse_dt
from helpers.modules import Modules

from .. import MAX_BOT_CAPACITY
from .pricing import calculate_bot_price, get_bot_purchase_panel

_purchase_locks = WeakValueDictionary()


def _get_purchase_lock(bot_id, transaction_id):
    key = (bot_id, transaction_id)
    lock = _purchase_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _purchase_locks[key] = lock
    return lock


async def create_bot_callback(client, callback_query):
    all_bots_data = await client.db.getBots(is_token=True)

    if len(all_bots_data) >= MAX_BOT_CAPACITY:
        backup_text = f" melalui @{BACKUP_BOT}" if BACKUP_BOT else ""

        text_warning = (
            f"{client.ns.emoji.md('cross_mark')} **Kapasitas Bot Penuh!**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Status', f'Server sudah mencapai batas maksimal pembuatan bot ({MAX_BOT_CAPACITY} Bot)'], ['Saran', f'Silakan buat bot baru{backup_text}']])}"
        )

        layout = [
            [
                {
                    "text": "• Kembali •",
                    "callback_data": "start",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text_warning),
            reply_markup=btn,
        )

    user_id = callback_query.from_user.id
    user_expiry = parse_dt(await client.db.getVars(user_id, "user_expiry_date"))

    if user_expiry and user_expiry > datetime.now(timezone.utc):
        text = (
            f"{client.ns.emoji.md('white_check_mark')} **Anda Sudah Berlangganan!**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Anda sudah memiliki akses untuk membuat bot'], ['Aksi', 'Tekan tombol di bawah untuk memulai proses pembuatan']])}"
        )

        layout = [
            [
                {
                    "text": "▶️ Lanjutkan Membuat Bot",
                    "callback_data": "start_creation_process",
                    "style": "green",
                    "emoji": client.ns.emoji.id("rocket"),
                }
            ],
            [
                {
                    "text": "• Kembali •",
                    "callback_data": "start",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ],
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=btn,
        )

    text, btn = await get_bot_purchase_panel(client, user_id, 1)

    return await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def adjust_bot_month_callback(client, callback_query):
    months = int(callback_query.data.split("_")[-1])

    if 1 <= months <= 12:
        text, btn = await get_bot_purchase_panel(
            client, callback_query.from_user.id, months
        )
        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=btn,
        )
    else:
        await callback_query.answer(
            "Durasi minimal 1 bulan dan maksimal 12 bulan.",
            show_alert=True,
        )


async def proceed_bot_payment_callback(client, callback_query):
    user_id = callback_query.from_user.id
    months = int(callback_query.data.split("_")[-1])

    if not 1 <= months <= 12:
        return await callback_query.answer(
            "Durasi minimal 1 bulan dan maksimal 12 bulan.",
            show_alert=True,
        )

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('hourglass')} **Sedang Memproses**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Sedang memproses'], ['Keterangan', 'Mohon tunggu sebentar']])}"
            )
        )
    )

    saweria_user_id = await client.db.getVars(client.me.id, "SAWERIA_USER_ID")

    if not saweria_user_id:
        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Layanan Pembayaran Tidak Tersedia**\n\n"
                    f"{client.ns.table.md(['Status', 'Keterangan'], [['Tidak Tersedia', 'Layanan pembayaran sedang dinonaktifkan sementara'], ['Tindakan', 'Silakan coba lagi beberapa saat lagi']])}"
                )
            )
        )

    _, _, amount = calculate_bot_price(months)
    fakeinfo = client.ns.utils.faker.generate()
    qr_image_stream = None

    try:
        (
            qr_string,
            transaction_id,
            qr_image_stream,
            amount_raw,
        ) = await client.ns.payment.SaweriaScraper(saweria_user_id).create_payment(
            amount=int(amount),
            name=f"User-{user_id}",
            email=fakeinfo.email,
            message=f"Akses Buat Bot VVIP {months} bulan",
            creator_name=client.me.username,
        )

        order_data = f"{months}|{amount_raw}|{user_id}"
        await client.db.setVars(client.me.id, transaction_id, order_data)

        detail_rows = [
            [
                f"{client.ns.emoji.char('shopping_bags')} Produk",
                f"Akses Buat Bot {months} Bulan",
            ],
            [f"{client.ns.emoji.char('gem')} Jumlah", f"Rp {amount_raw:,}"],
            [f"{client.ns.emoji.char('id_card')} Order ID", f"{transaction_id}"],
        ]

        markdown = (
            f"{client.ns.emoji.md('white_check_mark')} **Pembayaran Siap Dilakukan**\n\n"
            f"Silakan scan QRIS di atas untuk membayar, lalu tekan tombol Konfirmasi Pembayaran.\n\n"
            f"{client.ns.table.md(['Item', 'Keterangan'], detail_rows)}"
        )

        layout = [
            [
                {
                    "text": "✅ Konfirmasi Pembayaran",
                    "callback_data": f"confirm_bot_payment_{transaction_id}",
                    "style": "green",
                    "emoji": client.ns.emoji.id("white_check_mark"),
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        await callback_query.message.delete()

        await client.send_rich_message(
            user_id,
            client.ns.table.rich_photo(
                photo=qr_image_stream,
                markdown=markdown,
                alias=f"qris_{transaction_id}",
            ),
            reply_markup=btn,
        )
        qr_image_stream.close()

    except Exception as e:
        if qr_image_stream is not None:
            qr_image_stream.close()
        await client.send_rich_message(
            user_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], [['Status', 'Terjadi kesalahan'], ['Error', f'`{e}`']])}"
                )
            ),
        )


async def _confirm_bot_payment(client, callback_query, transaction_id, user):
    order_data_str = await client.db.getVars(client.me.id, transaction_id)

    if not order_data_str:
        return await callback_query.answer(
            "<emoji id=6271786398404055377>⚠️</emoji> Invoice ini sudah tidak valid atau telah selesai.",
            show_alert=True,
        )

    parts = order_data_str.split("|")
    if len(parts) < 3:
        return await callback_query.answer(
            "<emoji id=6271786398404055377>⚠️</emoji> Invoice ini sudah tidak valid.",
            show_alert=True,
        )

    months_str, amount_raw_str, buyer_id_str = parts[:3]
    try:
        months = max(1, min(12, int(months_str)))
        amount_raw = max(0, int(amount_raw_str))
        buyer_id = int(buyer_id_str) if buyer_id_str else None
    except (TypeError, ValueError):
        return await callback_query.answer(
            "<emoji id=6271786398404055377>⚠️</emoji> Invoice ini sudah tidak valid.",
            show_alert=True,
        )

    if buyer_id is not None and buyer_id != user.id:
        return await callback_query.answer(
            "<emoji id=6271786398404055377>⚠️</emoji> Invoice ini milik pengguna lain.",
            show_alert=True,
        )

    try:
        is_paid = await client.ns.payment.SaweriaScraper().check_paid_status(
            transaction_id,
            amount_raw or None,
        )

        if is_paid:
            marker_key = f"bot_purchase_done_{transaction_id}"
            already_processed = bool(await client.db.getVars(client.me.id, marker_key))

            if already_processed:
                await client.db.removeVars(client.me.id, transaction_id)
                await client.db.removeVars(client.me.id, marker_key)
                try:
                    await callback_query.message.delete()
                except Exception:
                    pass
                return await callback_query.answer(
                    "✅ Pembayaran ini sudah diproses.",
                    show_alert=False,
                )

            current_expiry = parse_dt(
                await client.db.getVars(user.id, "user_expiry_date")
            )
            start_date = max(
                current_expiry or datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            )
            expiry_date = start_date + timedelta(days=30 * months)

            await client.db.setVars(
                user.id,
                "user_expiry_date",
                expiry_date.isoformat(),
            )
            await client.db.setVars(client.me.id, marker_key, True)
            await client.db.removeVars(client.me.id, transaction_id)
            await client.db.removeVars(client.me.id, marker_key)
            await callback_query.message.delete()

            success_text = (
                f"{client.ns.emoji.md('white_check_mark')} **Pembayaran Berhasil!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], [['Status', f'Langganan Anda untuk membuat bot selama **{months} bulan** telah diaktifkan'], ['Ucapan', 'Terima kasih']])}"
            )

            layout = [
                [
                    {
                        "text": "▶️ Lanjutkan Membuat Bot",
                        "callback_data": "start_creation_process",
                        "style": "green",
                        "emoji": client.ns.emoji.id("rocket"),
                    }
                ]
            ]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_rich_message(
                user.id,
                pyrogram.types.InputRichMessage(markdown=success_text),
                reply_markup=btn,
            )

            owner_name = user.full_name or user.first_name or "Deleted Account"
            owner_mention = f"[{owner_name}](tg://user?id={user.id})"
            formatted_amount = f"{amount_raw:,}"

            owner_notif = (
                f"**{client.ns.emoji.md('money_bag')} Langganan Akses Baru!**\n\n"
                f"| Info | Detail |\n"
                f"| :--- | :---: |\n"
                f"| Pengguna | {owner_mention} |\n"
                f"| Durasi | {months} bulan |\n"
                f"| Jumlah | `Rp {formatted_amount}` |"
            )
            await client.send_rich_message(
                client.owner_id,
                pyrogram.types.InputRichMessage(markdown=owner_notif),
            )
        else:
            await callback_query.answer(
                "❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah beberapa saat.",
                show_alert=True,
            )
    except Exception as e:
        await callback_query.answer(
            f"❌ Terjadi kesalahan: {e}",
            show_alert=True,
        )


async def confirm_bot_payment_callback(client, callback_query):
    prefix = "confirm_bot_payment_"
    transaction_id = callback_query.data[len(prefix) :]
    lock = _get_purchase_lock(client.me.id, transaction_id)
    async with lock:
        await _confirm_bot_payment(
            client,
            callback_query,
            transaction_id,
            callback_query.from_user,
        )


class BotPurchase(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^create_bot$"))(
            self.handle(create_bot_callback)
        )
        self.client.on_callback_query(filters.regex("^adjust_bot_month_(\\d+)"))(
            self.handle(adjust_bot_month_callback)
        )
        self.client.on_callback_query(filters.regex("^pay_bot_qris_(\\d+)"))(
            self.handle(proceed_bot_payment_callback)
        )
        self.client.on_callback_query(filters.regex("^confirm_bot_payment_(.+)"))(
            self.handle(confirm_bot_payment_callback)
        )
