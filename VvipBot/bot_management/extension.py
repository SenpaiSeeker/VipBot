import asyncio
from datetime import datetime, timedelta, timezone
from weakref import WeakValueDictionary
from zoneinfo import ZoneInfo

import pyrogram
from pyrogram import filters

from helpers import parse_dt
from helpers.modules import Modules

from .. import SAWERIA_BLOCK_OVERRIDE_ID, set_purchase_block
from ..allbots.helpers import invalidate_page_cache
from .pricing import (
    calculate_bot_price,
    get_bot_base_price,
    get_bot_renewal_panel,
)

_TZ = ZoneInfo("Asia/Jakarta")
_renew_locks = WeakValueDictionary()


def _get_renew_lock(bot_id, transaction_id):
    key = (bot_id, transaction_id)
    lock = _renew_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _renew_locks[key] = lock
    return lock


def _format_rupiah(value):
    try:
        return f"Rp {int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


def _is_main_bot(client, bot_id):
    try:
        return int(client.manager.main_bot_id or 0) == int(bot_id)
    except (TypeError, ValueError):
        return False


async def _can_renew(client, user_id, bot_id):
    owner_id = await client.db.getVars(bot_id, "owner_id")
    if not owner_id:
        return False
    try:
        return int(user_id) in (int(owner_id), int(client.owner_id))
    except (TypeError, ValueError):
        return False


async def _resolve_bot_name(client, bot_id):
    bot_instance = client.manager.running_bots.get(bot_id)
    if bot_instance and bot_instance.me:
        return bot_instance.me.first_name
    return f"ID {bot_id}"


async def _find_bot_data(client, bot_id):
    for bot_data in await client.db.getBots(is_token=True):
        if str(bot_data.get("name")) == str(bot_id):
            return bot_data
    return None


async def _get_renewal_saweria_id(client, bot_id):
    stash = await client.db.getVars(bot_id, "SAWERIA_USER_ID_ORIG")
    if isinstance(stash, dict) and stash.get("had_original"):
        original = stash.get("original")
        if original:
            return original

    current = await client.db.getVars(bot_id, "SAWERIA_USER_ID")
    if current and current != SAWERIA_BLOCK_OVERRIDE_ID:
        return current

    main_bot_id = getattr(client.manager, "main_bot_id", None)
    if main_bot_id and int(main_bot_id) != int(bot_id):
        main_saweria = await client.db.getVars(main_bot_id, "SAWERIA_USER_ID")
        if main_saweria and main_saweria != SAWERIA_BLOCK_OVERRIDE_ID:
            return main_saweria

        main_stash = await client.db.getVars(main_bot_id, "SAWERIA_USER_ID_ORIG")
        if isinstance(main_stash, dict) and main_stash.get("had_original"):
            return main_stash.get("original")

    return None


async def _ensure_bot_running(client, bot_id):
    if bot_id in client.manager.running_bots:
        return "Bot sedang online."

    remaining = await client.manager.flood_remaining(bot_id)
    if remaining > 0:
        mins = max(1, remaining // 60)
        return f"Bot sedang FloodWait ±{mins} menit."

    bot_data = await _find_bot_data(client, bot_id)
    if not bot_data:
        return "Data bot tidak ditemukan."

    try:
        await client.manager.start_bot(bot_data)
    except Exception as e:
        return f"Bot gagal diaktifkan: {e}"

    if not await _find_bot_data(client, bot_id):
        return "Bot gagal diaktifkan dan datanya telah dihapus."

    if bot_id in client.manager.running_bots:
        return "Bot berhasil diaktifkan kembali."

    remaining = await client.manager.flood_remaining(bot_id)
    if remaining > 0:
        mins = max(1, remaining // 60)
        return f"Bot sedang FloodWait ±{mins} menit."

    return "Bot tersimpan dan akan dicoba aktifkan otomatis."


async def _notify_deleted_bot(client, order, transaction_id):
    main_client = getattr(client.manager, "main_bot_client", None) or client
    rows = [
        ["Order ID", f"`{transaction_id}`"],
        ["Bot ID", f"`{order.get('bot_id', '-')}`"],
        ["Status", "Bot sudah dihapus sebelum pembayaran dikonfirmasi"],
    ]
    try:
        await main_client.send_rich_message(
            client.owner_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{main_client.ns.emoji.md('warning')} **Renewal "
                    "Dibatalkan**\n\n"
                    f"{main_client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )
    except Exception:
        pass


async def _send_renewal_notifications(
    client,
    user,
    owner_id,
    bot_id,
    bot_name,
    months,
    amount_raw,
    new_expiry,
):
    new_expiry_text = new_expiry.astimezone(_TZ).strftime("%d-%m-%Y %H:%M WIB")
    user_mention = client.ns.telegram.arg.getMention(user, md=True)

    if int(owner_id) != int(user.id) and int(owner_id) != int(client.owner_id):
        rows = [
            ["Bot", f"**{bot_name}** (`{bot_id}`)"],
            ["Pembayar", user_mention],
            ["Durasi", f"**{months} bulan**"],
            ["Masa Aktif Baru", f"`{new_expiry_text}`"],
        ]
        try:
            await client.send_rich_message(
                owner_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('party_popper')} **Bot Anda "
                        "Berhasil Diperpanjang**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                    )
                ),
            )
        except Exception:
            pass

    if int(client.owner_id) == int(user.id):
        return

    main_client = getattr(client.manager, "main_bot_client", None) or client
    rows = [
        ["Pembayar", user_mention],
        ["Bot", f"**{bot_name}** (`{bot_id}`)"],
        ["Durasi", f"**{months} bulan**"],
        ["Jumlah", f"**`{_format_rupiah(amount_raw)}`**"],
        ["Masa Aktif Baru", f"`{new_expiry_text}`"],
    ]
    try:
        await main_client.send_rich_message(
            client.owner_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{main_client.ns.emoji.md('money_bag')} **Pendapatan "
                    "Perpanjangan Bot**\n\n"
                    f"{main_client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )
    except Exception:
        pass


async def request_extend_duration_callback(client, callback_query):
    bot_id_to_request = int(callback_query.data.split(" ", 1)[1])
    requester = callback_query.from_user
    bot_name = f"ID {bot_id_to_request}"

    try:
        bot_instance = client.manager.running_bots.get(bot_id_to_request)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
    except Exception:
        pass

    try:
        main_bot_client = client.manager.main_bot_client
        if not main_bot_client or not main_bot_client.is_connected:
            raise ConnectionError(
                "Bot utama sedang tidak aktif, tidak dapat mengirim notifikasi."
            )

        requester_name = (
            requester.full_name or requester.first_name or "Deleted Account"
        )
        requester_mention = f"[{requester_name}](tg://user?id={requester.id})"
        rows = [
            ["Pengguna", f"{requester_mention} (`{requester.id}`)"],
            ["Bot", f"**{bot_name}** (`{bot_id_to_request}`)"],
            [
                "Aksi",
                "Setujui untuk menambah masa aktif bot ini sebanyak 30 hari",
            ],
        ]
        txt_owner = (
            f"**{main_bot_client.ns.emoji.md('bell')} Permintaan "
            "Perpanjangan Durasi**\n\n"
            f"{main_bot_client.ns.table.md(['Info', 'Nilai'], rows)}"
        )

        layout_owner = [
            [
                {
                    "text": "✅ Setujui (+30 Hari)",
                    "callback_data": (
                        f"approve_extension {bot_id_to_request} " f"{requester.id}"
                    ),
                    "style": "green",
                    "emoji": main_bot_client.ns.emoji.id("white_check_mark"),
                },
                {
                    "text": "❌ Tolak Permintaan",
                    "callback_data": f"close_req {bot_id_to_request} {requester.id}",
                    "style": "red",
                    "emoji": main_bot_client.ns.emoji.id("cross_mark"),
                },
            ]
        ]
        btn_owner = main_bot_client.ns.telegram.button.build_button_grid(layout_owner)

        await main_bot_client.send_rich_message(
            client.owner_id,
            pyrogram.types.InputRichMessage(markdown=txt_owner),
            reply_markup=btn_owner,
        )
        await callback_query.answer(
            "✅ Permintaan perpanjangan telah dikirim ke Owner Utama. Anda "
            "akan dihubungi jika disetujui.",
            show_alert=True,
        )
    except Exception as e:
        await callback_query.answer(
            f"❌ Gagal mengirim permintaan ke Owner: {e}",
            show_alert=True,
        )


async def renew_bot_callback(client, callback_query):
    bot_id = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id

    if _is_main_bot(client, bot_id):
        return await callback_query.answer(
            "Bot utama tidak dapat diperpanjang.",
            show_alert=True,
        )

    if not await _can_renew(client, user_id, bot_id):
        return await callback_query.answer(
            "Ini bukan bot milik Anda.",
            show_alert=True,
        )

    text, btn = await get_bot_renewal_panel(client, bot_id, 1)
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def adjust_renew_month_callback(client, callback_query):
    bot_id = int(callback_query.matches[0].group(1))
    months = int(callback_query.matches[0].group(2))
    user_id = callback_query.from_user.id

    if _is_main_bot(client, bot_id):
        return await callback_query.answer(
            "Bot utama tidak dapat diperpanjang.",
            show_alert=True,
        )

    if not await _can_renew(client, user_id, bot_id):
        return await callback_query.answer(
            "Ini bukan bot milik Anda.",
            show_alert=True,
        )

    if not 1 <= months <= 12:
        return await callback_query.answer(
            "Durasi minimal 1 bulan dan maksimal 12 bulan.",
            show_alert=True,
        )

    text, btn = await get_bot_renewal_panel(client, bot_id, months)
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def proceed_bot_renewal_callback(client, callback_query):
    bot_id = int(callback_query.matches[0].group(1))
    months = int(callback_query.matches[0].group(2))
    user_id = callback_query.from_user.id

    if not await _can_renew(client, user_id, bot_id):
        return await callback_query.answer(
            "Ini bukan bot milik Anda.",
            show_alert=True,
        )

    if _is_main_bot(client, bot_id):
        return await callback_query.answer(
            "Bot utama tidak dapat diperpanjang.",
            show_alert=True,
        )

    if not 1 <= months <= 12:
        return await callback_query.answer(
            "Durasi minimal 1 bulan dan maksimal 12 bulan.",
            show_alert=True,
        )

    rows = [
        ["Status", "Sedang memproses"],
        ["Keterangan", "Mohon tunggu sebentar"],
    ]
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('hourglass')} **Sedang Memproses**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
    )

    saweria_user_id = await _get_renewal_saweria_id(client, bot_id)
    if not saweria_user_id:
        rows = [
            ["Status", "Layanan pembayaran belum tersedia"],
            ["Tindakan", "Silakan hubungi Owner Utama"],
        ]
        return await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Pembayaran Tidak "
                    "Tersedia**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

    owner_id = await client.db.getVars(bot_id, "owner_id")
    if not owner_id:
        return await callback_query.answer(
            "Data pemilik bot tidak ditemukan.",
            show_alert=True,
        )

    base_price = await get_bot_base_price(client)
    _, _, amount = calculate_bot_price(months, base_price)
    bot_name = await _resolve_bot_name(client, bot_id)
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
            name=f"Renew-{bot_id}",
            email=fakeinfo.email,
            message=f"Perpanjangan Bot {bot_id} selama {months} bulan",
            creator_name=client.me.username or client.me.first_name,
        )

        order_key = f"bot_renew_{transaction_id}"
        order_data = {
            "bot_id": bot_id,
            "buyer_id": user_id,
            "owner_id": int(owner_id),
            "months": months,
            "amount_raw": amount_raw,
        }
        await client.db.setVars(client.me.id, order_key, order_data)

        detail_rows = [
            [
                f"{client.ns.emoji.char('robot')} Bot",
                f"**{bot_name}** (`{bot_id}`)",
            ],
            [
                f"{client.ns.emoji.char('calendar')} Durasi",
                f"{months} bulan",
            ],
            [f"{client.ns.emoji.char('gem')} Jumlah", f"Rp {amount_raw:,}"],
            [f"{client.ns.emoji.char('id_card')} Order ID", f"`{transaction_id}`"],
        ]

        markdown = (
            f"{client.ns.emoji.md('white_check_mark')} **Pembayaran Siap "
            "Dilakukan**\n\n"
            "Silakan scan QRIS di atas untuk membayar, lalu tekan tombol "
            "Konfirmasi Pembayaran.\n\n"
            f"{client.ns.table.md(['Item', 'Keterangan'], detail_rows)}"
        )

        layout = [
            [
                {
                    "text": "✅ Konfirmasi Pembayaran",
                    "callback_data": f"confirm_bot_renew_{transaction_id}",
                    "style": "green",
                    "emoji": client.ns.emoji.id("white_check_mark"),
                }
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(layout)

        try:
            await callback_query.message.delete()
        except Exception:
            pass

        await client.send_rich_message(
            user_id,
            client.ns.table.rich_photo(
                photo=qr_image_stream,
                markdown=markdown,
                alias=f"renew_qris_{transaction_id}",
            ),
            reply_markup=btn,
        )
    except Exception as e:
        rows = [
            ["Status", "Terjadi kesalahan"],
            ["Error", f"`{e}`"],
        ]
        await client.send_rich_message(
            user_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Terjadi Kesalahan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )
    finally:
        if qr_image_stream is not None:
            qr_image_stream.close()


async def _confirm_bot_renewal(client, callback_query, transaction_id, user):
    order_key = f"bot_renew_{transaction_id}"
    order = await client.db.getVars(client.me.id, order_key)

    if not isinstance(order, dict):
        return await callback_query.answer(
            "Invoice ini sudah tidak valid atau telah selesai.",
            show_alert=True,
        )

    try:
        bot_id = int(order.get("bot_id"))
        buyer_id = int(order.get("buyer_id") or 0)
        months = max(1, min(12, int(order.get("months") or 1)))
        amount_raw = max(0, int(order.get("amount_raw") or 0))
    except (TypeError, ValueError):
        return await callback_query.answer(
            "Invoice ini sudah tidak valid.",
            show_alert=True,
        )

    if buyer_id != user.id:
        return await callback_query.answer(
            "Invoice ini milik pengguna lain.",
            show_alert=True,
        )

    owner_id = await client.db.getVars(bot_id, "owner_id")
    if not owner_id:
        await client.db.removeVars(client.me.id, order_key)
        await _notify_deleted_bot(client, order, transaction_id)
        return await callback_query.answer(
            "Bot sudah dihapus. Pembayaran tidak dapat diproses.",
            show_alert=True,
        )

    try:
        is_paid = await client.ns.payment.SaweriaScraper().check_paid_status(
            transaction_id,
            amount_raw or None,
        )
    except Exception as e:
        return await callback_query.answer(
            f"❌ Gagal memeriksa pembayaran: {e}",
            show_alert=True,
        )

    if not is_paid:
        return await callback_query.answer(
            "❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah "
            "beberapa saat.",
            show_alert=True,
        )

    marker_key = f"bot_renew_done_{transaction_id}"
    if not await client.db.setVarsOnce(client.me.id, marker_key, True):
        await client.db.removeVars(client.me.id, order_key)
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        return await callback_query.answer(
            "✅ Pembayaran ini sudah diproses.",
            show_alert=False,
        )

    try:
        now = datetime.now(timezone.utc)
        current_expiry = parse_dt(
            await client.db.getVars(bot_id, "bot_expiration_date")
        )
        start_date = current_expiry if current_expiry and current_expiry > now else now
        new_expiry = start_date + timedelta(days=30 * months)

        await client.db.setVars(
            bot_id,
            "bot_expiration_date",
            new_expiry.isoformat(),
        )
        await set_purchase_block(client.db, bot_id, False)
        if (new_expiry - now).days > 10:
            await client.db.removeVars(bot_id, "last_warning_notification_date")
    except Exception as e:
        await client.db.removeVars(client.me.id, marker_key)
        return await callback_query.answer(
            f"❌ Gagal memperpanjang bot: {e}",
            show_alert=True,
        )

    await client.db.removeVars(client.me.id, order_key)
    await client.db.removeVars(client.me.id, marker_key)
    invalidate_page_cache()

    runtime_status = await _ensure_bot_running(client, bot_id)
    bot_name = await _resolve_bot_name(client, bot_id)
    new_expiry_text = new_expiry.astimezone(_TZ).strftime("%d-%m-%Y %H:%M WIB")

    try:
        await callback_query.message.delete()
    except Exception:
        pass

    try:
        await callback_query.answer(
            "✅ Pembayaran berhasil diproses.",
            show_alert=False,
        )
    except Exception:
        pass

    rows = [
        ["Bot", f"**{bot_name}** (`{bot_id}`)"],
        ["Durasi", f"**{months} bulan**"],
        ["Jumlah", f"`{_format_rupiah(amount_raw)}`"],
        ["Masa Aktif Baru", f"`{new_expiry_text}`"],
        ["Status", runtime_status],
    ]
    layout = [
        [
            {
                "text": "🔄 Perpanjang Lagi",
                "callback_data": f"renew_bot {bot_id}",
                "style": "green",
                "emoji": client.ns.emoji.id("repeat"),
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
    await client.send_rich_message(
        user.id,
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('white_check_mark')} **Pembayaran "
                "Berhasil!**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        ),
        reply_markup=btn,
    )

    await _send_renewal_notifications(
        client=client,
        user=user,
        owner_id=owner_id,
        bot_id=bot_id,
        bot_name=bot_name,
        months=months,
        amount_raw=amount_raw,
        new_expiry=new_expiry,
    )


async def confirm_bot_renewal_callback(client, callback_query):
    prefix = "confirm_bot_renew_"
    transaction_id = callback_query.data[len(prefix) :]
    lock = _get_renew_lock(client.me.id, transaction_id)
    async with lock:
        try:
            await _confirm_bot_renewal(
                client,
                callback_query,
                transaction_id,
                callback_query.from_user,
            )
        except Exception as e:
            await callback_query.answer(
                f"❌ Terjadi kesalahan: {e}",
                show_alert=True,
            )


async def owner_approve_extension_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa menyetujui permintaan ini.",
            show_alert=True,
        )

    try:
        _, bot_id_str, requester_id_str = callback_query.data.split()
        bot_id_to_extend, requester_id, days_to_add = (
            int(bot_id_str),
            int(requester_id_str),
            30,
        )

        exp_date_str = await client.db.getVars(bot_id_to_extend, "bot_expiration_date")
        current_exp_date = (
            parse_dt(exp_date_str) if exp_date_str else datetime.now(timezone.utc)
        )

        new_exp_date = current_exp_date + timedelta(days=days_to_add)
        await client.db.setVars(
            bot_id_to_extend,
            "bot_expiration_date",
            new_exp_date.isoformat(),
        )
        await set_purchase_block(client.db, bot_id_to_extend, False)

        rows = [
            ["Bot", f"`{bot_id_to_extend}`"],
            ["Tambahan", f"**{days_to_add} hari**"],
            ["Status", "Durasi telah ditambah"],
        ]
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Persetujuan "
                    "Berhasil!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

        try:
            bot_instance = client.manager.running_bots.get(bot_id_to_extend)
            bot_name = (
                bot_instance.me.first_name
                if bot_instance and bot_instance.is_connected
                else f"ID {bot_id_to_extend}"
            )

            rows = [
                ["Bot", f"**{bot_name}**"],
                [
                    "Status",
                    "Permintaan perpanjangan Anda telah disetujui dan " "diperpanjang",
                ],
            ]
            await client.send_rich_message(
                requester_id,
                pyrogram.types.InputRichMessage(
                    markdown=(
                        f"{client.ns.emoji.md('party_popper')} **Kabar Baik!**\n\n"
                        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                    )
                ),
            )
        except Exception as e:
            client.log.print(f"Gagal kirim notif persetujuan ke {requester_id}: {e}")
    except Exception as e:
        rows = [
            ["Status", "Gagal menyetujui permintaan"],
            ["Error", f"`{e}`"],
        ]
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Gagal Menyetujui**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )


async def owner_close_request_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return await callback_query.answer(
            "Hanya Owner Utama yang bisa melakukan ini.",
            show_alert=True,
        )

    try:
        rows = [
            ["Status", "Permintaan telah ditolak/ditutup oleh Owner Utama"],
        ]
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Permintaan "
                    "Ditutup**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )
    except Exception:
        pass


class BotExtension(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(
            filters.regex("^request_extend_duration\\s(\\d+)")
        )(self.handle(request_extend_duration_callback))
        self.client.on_callback_query(filters.regex("^renew_bot\\s(\\d+)$"))(
            self.handle(renew_bot_callback)
        )
        self.client.on_callback_query(
            filters.regex("^adjust_renew_month_(\\d+)_(\\d+)$")
        )(self.handle(adjust_renew_month_callback))
        self.client.on_callback_query(
            filters.regex("^pay_bot_renew_qris_(\\d+)_(\\d+)$")
        )(self.handle(proceed_bot_renewal_callback))
        self.client.on_callback_query(filters.regex("^confirm_bot_renew_(.+)$"))(
            self.handle(confirm_bot_renewal_callback)
        )
        self.client.on_callback_query(
            filters.regex("^approve_extension\\s(\\d+)\\s(\\d+)")
        )(self.handle(owner_approve_extension_callback))
        self.client.on_callback_query(filters.regex("^close_req\\s(\\d+)\\s(\\d+)"))(
            self.handle(owner_close_request_callback)
        )
