import asyncio
from datetime import datetime, timedelta, timezone
from weakref import WeakValueDictionary
from zoneinfo import ZoneInfo

import pyrogram
from pyrogram import filters

from helpers import listen, parse_dt
from helpers.modules import Modules

from .. import set_purchase_block
from .helpers import _resolve_owner_text, invalidate_page_cache, send_allbots_list

_TZ = ZoneInfo("Asia/Jakarta")
_restart_locks = WeakValueDictionary()


def _get_restart_lock(bot_id):
    bot_id = int(bot_id)
    lock = _restart_locks.get(bot_id)
    if lock is None:
        lock = asyncio.Lock()
        _restart_locks[bot_id] = lock
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


async def _find_bot_data(client, bot_id):
    for bot_data in await client.db.getBots(is_token=True):
        if str(bot_data.get("name")) == str(bot_id):
            return bot_data
    return None


async def _bot_runtime(client, bot_id):
    bot_instance = client.manager.running_bots.get(bot_id)
    if bot_instance and bot_instance.is_connected:
        return "Online", bot_instance

    if bot_id in getattr(client.manager, "_starting_bots", set()):
        return "Sedang dimulai", bot_instance

    remaining = await client.manager.flood_remaining(bot_id)
    if remaining > 0:
        mins = max(1, remaining // 60)
        return f"FloodWait ±{mins} menit", bot_instance

    return "Offline", bot_instance


async def _expiry_info(client, bot_id):
    expiry = parse_dt(await client.db.getVars(bot_id, "bot_expiration_date"))
    if not expiry:
        return "Belum diatur", None

    days_left = max(0, (expiry - datetime.now(timezone.utc)).days)
    date_text = expiry.astimezone(_TZ).strftime("%d-%m-%Y %H:%M WIB")
    return f"{date_text} ({days_left} hari)", expiry


async def _collect_stats(client, bot_id):
    user_ids = await client.db.getListVars(bot_id, "user_ids") or []
    members = await client.db.getListVars(bot_id, "vvip_members") or []
    coupons = await client.db.getListVars(bot_id, "coupons") or []
    packages = await client.db.getListVars(bot_id, "list_vvip") or []
    history = await client.db.getListVars(bot_id, "vip_revenue_history") or []

    sales_count = await client.db.getVars(bot_id, "sales_count")
    if sales_count is None:
        sales_count = len(history)
    try:
        sales_count = int(sales_count)
    except (TypeError, ValueError):
        sales_count = 0

    normal_members = 0
    hidden_members = 0
    for member in members:
        if isinstance(member, dict):
            if member.get("hidden"):
                hidden_members += 1
            else:
                normal_members += 1
        else:
            normal_members += 1

    revenue = 0
    revenue_today = 0
    revenue_week = 0
    revenue_month = 0
    now = datetime.now(_TZ)
    week_start = now - timedelta(days=7)

    for record in history:
        if not isinstance(record, dict):
            continue
        try:
            amount = int(record.get("amount", 0) or 0)
        except (TypeError, ValueError):
            continue

        revenue += amount
        try:
            record_date = parse_dt(record.get("date"))
        except (TypeError, ValueError):
            record_date = None
        if not record_date:
            continue

        local_date = record_date.astimezone(_TZ)
        if local_date.date() == now.date():
            revenue_today += amount
        if week_start <= local_date <= now:
            revenue_week += amount
        if local_date.year == now.year and local_date.month == now.month:
            revenue_month += amount

    return {
        "users": len(user_ids),
        "vvip_normal": normal_members,
        "vvip_hidden": hidden_members,
        "coupons": len(coupons),
        "packages": len(packages),
        "sales": sales_count,
        "revenue": revenue,
        "revenue_today": revenue_today,
        "revenue_week": revenue_week,
        "revenue_month": revenue_month,
    }


async def _build_detail(client, bot_id, page):
    status, bot_instance = await _bot_runtime(client, bot_id)
    bot_name = f"ID {bot_id}"
    bot_username = "Tidak tersedia"

    if bot_instance and bot_instance.me:
        bot_name = bot_instance.me.first_name
        if bot_instance.me.username:
            bot_username = f"@{bot_instance.me.username}"

    owner_id = await client.db.getVars(bot_id, "owner_id")
    owner_text = await _resolve_owner_text(client, owner_id)
    expiry_text, _ = await _expiry_info(client, bot_id)
    block_mode = bool(await client.db.getVars(bot_id, "purchase_block") or False)
    stats = await _collect_stats(client, bot_id)

    rows = [
        ["Nama Bot", bot_name],
        ["ID Bot", f"`{bot_id}`"],
        ["Username", bot_username],
        ["Status Koneksi", status],
        ["Block Mode", "ON" if block_mode else "OFF"],
        ["Pemilik", owner_text],
        ["Masa Aktif", expiry_text],
        ["Pengguna", f"`{stats['users']}`"],
        [
            "VVIP",
            f"`{stats['vvip_normal']}` normal / `{stats['vvip_hidden']}` hidden",
        ],
        ["Kupon", f"`{stats['coupons']}`"],
        ["Penjualan", f"`{stats['sales']}`"],
        ["Pendapatan", f"`{_format_rupiah(stats['revenue'])}`"],
    ]

    text = (
        f"**{client.ns.emoji.md('toolbox')} Kelola Bot Spesifik**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
    )

    restart_text = "🔄 Restart Bot" if status == "Online" else "▶️ Start Bot"
    block_text = "🔓 Matikan Block" if block_mode else "🔒 Aktifkan Block"

    layout = [
        [
            {
                "text": restart_text,
                "callback_data": f"allbots_restart_{bot_id}_{page}",
                "style": "green",
                "emoji": client.ns.emoji.id("repeat"),
            },
            {
                "text": block_text,
                "callback_data": f"allbots_toggle_block_{bot_id}_{page}",
                "style": "red" if block_mode else "blue",
                "emoji": client.ns.emoji.id("lock"),
            },
        ],
        [
            {
                "text": "📊 Ringkasan Performa",
                "callback_data": f"allbots_stats_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("chart_bar"),
            },
            {
                "text": "✉️ Kirim Pesan ke Owner",
                "callback_data": f"allbots_message_owner_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("envelope"),
            },
        ],
        [
            {
                "text": "🗑️ Hapus Bot",
                "callback_data": f"allbots_confirm_delete_{bot_id}_{page}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": "🗓️ Kelola Masa Aktif",
                "callback_data": f"allbots_duration_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            },
        ],
        [
            {
                "text": "🔙 Kembali ke Daftar",
                "callback_data": f"allbots_back_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]

    return text, layout


async def _show_detail(client, callback_query, bot_id, page, notice=None):
    text, layout = await _build_detail(client, bot_id, page)
    if notice:
        text = f"{notice}\n\n{text}"
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


async def allbots_detail_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))
    await _show_detail(client, callback_query, bot_id, page)


async def allbots_back_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    page = int(callback_query.matches[0].group(1))
    await send_allbots_list(client, callback_query, page)


async def allbots_stats_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))

    status, bot_instance = await _bot_runtime(client, bot_id)
    bot_name = (
        bot_instance.me.first_name
        if bot_instance and bot_instance.me
        else f"ID {bot_id}"
    )
    expiry_text, _ = await _expiry_info(client, bot_id)
    stats = await _collect_stats(client, bot_id)

    rows = [
        ["Bot", f"**{bot_name}** (`{bot_id}`)"],
        ["Status", status],
        ["Masa Aktif", expiry_text],
        ["Pengguna", f"`{stats['users']}`"],
        ["VVIP Normal", f"`{stats['vvip_normal']}`"],
        ["VVIP Hidden", f"`{stats['vvip_hidden']}`"],
        ["Kupon", f"`{stats['coupons']}`"],
        ["Paket VVIP", f"`{stats['packages']}`"],
        ["Penjualan", f"`{stats['sales']}`"],
        ["Pendapatan Hari Ini", f"`{_format_rupiah(stats['revenue_today'])}`"],
        ["Pendapatan 7 Hari", f"`{_format_rupiah(stats['revenue_week'])}`"],
        ["Pendapatan Bulan Ini", f"`{_format_rupiah(stats['revenue_month'])}`"],
        ["Total Pendapatan", f"**`{_format_rupiah(stats['revenue'])}`**"],
    ]
    text = (
        f"**{client.ns.emoji.md('chart_bar')} Ringkasan Performa Bot**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
    )
    layout = [
        [
            {
                "text": "• Kembali ke Detail •",
                "callback_data": f"allbots_detail_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=client.ns.telegram.button.build_button_grid(layout),
    )


async def allbots_restart_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))

    if _is_main_bot(client, bot_id):
        return await callback_query.answer(
            "Bot utama tidak dapat di-restart dari panel ini.",
            show_alert=True,
        )

    if bot_id in getattr(client.manager, "_starting_bots", set()):
        return await callback_query.answer(
            "Bot ini sedang dalam proses dimulai.",
            show_alert=True,
        )

    lock = _get_restart_lock(bot_id)
    if lock.locked():
        return await callback_query.answer(
            "Bot ini sedang dalam proses restart.",
            show_alert=True,
        )

    async with lock:
        remaining = await client.manager.flood_remaining(bot_id)
        if remaining > 0:
            mins = max(1, remaining // 60)
            return await callback_query.answer(
                f"Bot masih FloodWait ±{mins} menit.",
                show_alert=True,
            )

        bot_data = await _find_bot_data(client, bot_id)
        if not bot_data:
            return await callback_query.answer(
                "Data bot tidak ditemukan.",
                show_alert=True,
            )

        try:
            await callback_query.answer()
        except Exception:
            pass

        rows = [["Status", "Memproses restart bot"]]
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('hourglass')} **Memproses**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )

        try:
            if bot_id in client.manager.running_bots:
                await client.manager.stop_bot(bot_id)
                await asyncio.sleep(1)

            await client.manager.start_bot(bot_data)

            if bot_id in client.manager.running_bots:
                result = "✅ Bot berhasil dijalankan."
            else:
                remaining = await client.manager.flood_remaining(bot_id)
                if remaining > 0:
                    mins = max(1, remaining // 60)
                    result = f"⚠️ Bot masih FloodWait ±{mins} menit."
                else:
                    result = "❌ Bot gagal dijalankan. Cek log untuk detail."
        except Exception as e:
            result = f"❌ Gagal restart bot: {e}"

        invalidate_page_cache(page)
        await _show_detail(client, callback_query, bot_id, page, notice=result)


async def allbots_toggle_block_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))

    if _is_main_bot(client, bot_id):
        return await callback_query.answer(
            "Bot utama tidak dapat diubah block mode-nya dari panel ini.",
            show_alert=True,
        )

    current = bool(await client.db.getVars(bot_id, "purchase_block") or False)
    try:
        await set_purchase_block(client.db, bot_id, not current)
    except Exception as e:
        return await callback_query.answer(
            f"Gagal mengubah block mode: {e}",
            show_alert=True,
        )

    invalidate_page_cache(page)
    try:
        await callback_query.answer(
            f"Block mode {'ON' if not current else 'OFF'}.",
            show_alert=True,
        )
    except Exception:
        pass
    await _show_detail(client, callback_query, bot_id, page)


async def allbots_message_owner_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    page = int(callback_query.matches[0].group(2))

    owner_id = await client.db.getVars(bot_id, "owner_id")
    if not owner_id:
        return await callback_query.answer(
            "Owner bot tidak ditemukan.",
            show_alert=True,
        )

    try:
        await callback_query.answer()
    except Exception:
        pass

    prompt = (
        "**✉️ Kirim Pesan ke Owner Bot**\n\n"
        "Kirim teks, foto, atau media yang ingin diteruskan ke owner bot.\n"
        "Ketik `/batal` untuk membatalkan."
    )

    try:
        message = await client.ask(client.owner_id, prompt, timeout=300)
        if not message:
            raise asyncio.TimeoutError

        if message.text and message.text.strip().lower() == "/batal":
            raise listen.UserCancelled

        await message.copy(chat_id=int(owner_id))
        result = "✅ Pesan berhasil dikirim ke owner bot."
    except listen.UserCancelled:
        result = "❌ Pengiriman pesan dibatalkan."
    except asyncio.TimeoutError:
        result = "❌ Waktu pengiriman pesan habis."
    except pyrogram.errors.UserIsBlocked:
        result = "❌ Owner bot memblokir bot utama."
    except pyrogram.errors.PeerIdInvalid:
        result = "❌ Owner bot tidak dapat dihubungi."
    except Exception as e:
        result = f"❌ Gagal mengirim pesan: {e}"

    rows = [
        ["Bot", f"`{bot_id}`"],
        ["Tujuan", f"`{int(owner_id)}`"],
        ["Status", result],
    ]
    text = (
        f"{client.ns.emoji.md('envelope')} **Status Pengiriman Pesan**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
    )
    layout = [
        [
            {
                "text": "• Kembali ke Detail •",
                "callback_data": f"allbots_detail_{bot_id}_{page}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    ]
    try:
        await client.send_rich_message(
            client.owner_id,
            pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=client.ns.telegram.button.build_button_grid(layout),
        )
    except Exception as e:
        client.log.print(f"Gagal mengirim status pesan owner: {e}")


class AllBotsDetail(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^allbots_detail_(\\d+)_(\\d+)"))(
            self.handle(allbots_detail_callback)
        )
        self.client.on_callback_query(filters.regex("^allbots_back_(\\d+)"))(
            self.handle(allbots_back_callback)
        )
        self.client.on_callback_query(filters.regex("^allbots_stats_(\\d+)_(\\d+)"))(
            self.handle(allbots_stats_callback)
        )
        self.client.on_callback_query(filters.regex("^allbots_restart_(\\d+)_(\\d+)"))(
            self.handle(allbots_restart_callback)
        )
        self.client.on_callback_query(
            filters.regex("^allbots_toggle_block_(\\d+)_(\\d+)")
        )(self.handle(allbots_toggle_block_callback))
        self.client.on_callback_query(
            filters.regex("^allbots_message_owner_(\\d+)_(\\d+)")
        )(self.handle(allbots_message_owner_callback))
