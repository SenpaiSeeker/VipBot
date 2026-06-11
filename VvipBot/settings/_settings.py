import asyncio
import binascii
import os
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from telethon import events
from telethon.extensions.html import unparse as html_unparse
from telethon.tl import functions, types

from .. import command, ctx, is_bot_owner
from ..core._core import invalidate_setting_cache


@command(lambda ctx: events.CallbackQuery(pattern=b"^settings$"))
async def settings(client, event):
    sender = await event.get_sender()

    if not await is_bot_owner(client, sender.id):
        return await event.answer(
            "⛔ Anda tidak memiliki akses ke menu ini.", alert=True
        )

    layout = [
        [
            {
                "text": "📷 Atur Foto Start",
                "callback_data": "set_start_photo",
                "style": "primary",
                "emoji": 5375074927252621134,
            },
            {
                "text": "📝 Atur Teks Start",
                "callback_data": "set_start_text",
                "style": "primary",
                "emoji": 5334673106202010226,
            },
        ],
        [
            {
                "text": "➕ Tambah VVIP",
                "callback_data": "setup_listvvip",
                "style": "success",
                "emoji": 5226945370684140473,
            },
            {
                "text": "🗑️ Hapus VVIP",
                "callback_data": "delete_listvvip",
                "style": "danger",
                "emoji": 5229113891081956317,
            },
        ],
        [
            {
                "text": "✏️ Edit Harga VVIP",
                "callback_data": "edit_price_listvvip",
                "style": "primary",
                "emoji": 5334882760735598374,
            },
        ],
        [
            {
                "text": "👥 Total Pengguna",
                "callback_data": "total_users_count",
                "style": "primary",
                "emoji": 5372926953978341366,
            },
            {
                "text": "🔍 Cek Member VVIP",
                "callback_data": "list_members_0",
                "style": "primary",
                "emoji": 5372926953978341366,
            },
        ],
        [
            {
                "text": "✅ Cek Member Aktif",
                "callback_data": "check_active_menu_init",
                "style": "primary",
                "emoji": 5188217332748527444,
            },
            {
                "text": "🔎 Cek Status Grup VVIP",
                "callback_data": "check_vvip_status",
                "style": "primary",
                "emoji": 5188311512791393083,
            },
        ],
        [
            {
                "text": "📢 Buat Broadcast",
                "callback_data": "broadcast",
                "style": "primary",
                "emoji": 5469903029144657419,
            },
            {
                "text": "⭐ Harga Broadcast Paid",
                "callback_data": "set_broadcast_price",
                "style": "primary",
                "emoji": 5458799228719472718,
            },
        ],
        [
            {
                "text": "🔑 Kelola Kunci API",
                "callback_data": "api_settings",
                "style": "primary",
                "emoji": 5330115548900501467,
            },
            {
                "text": "🎟️ Kelola Kupon",
                "callback_data": "manage_coupons",
                "style": "primary",
                "emoji": 5418010521309815154,
            },
        ],
        [
            {
                "text": "💰 Pendapatan VIP",
                "callback_data": "vip_revenue_menu",
                "style": "primary",
                "emoji": 5375296873982604963,
            },
            {
                "text": "📊 Statistik Stars",
                "callback_data": "stats_0",
                "style": "primary",
                "emoji": 5458799228719472718,
            },
        ],
        [
            {
                "text": "◀️ Kembali ke Menu Utama",
                "callback_data": "start",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ],
    ]

    em = client.ns.emoji
    txt_content = (
        f"{em.toolbox} <b>Panel Pengaturan Owner</b>\n\n"
        f"Selamat datang di pusat kendali bot Anda! "
        f"Silakan pilih menu di bawah untuk mengelola berbagai aspek bot."
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit(txt_content, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^check_vvip_status$"))
async def check_vvip_status_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return await event.answer(
            "⛔ Anda tidak memiliki akses ke menu ini.", alert=True
        )

    chat_id = event.chat_id
    await event.delete()

    status_msg = await client.send_message(
        chat_id,
        f"{em.hourglass} Sedang Memeriksa Status Grup...\nMohon tunggu, proses ini mungkin memakan waktu.",
        parse_mode="html",
    )

    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []

    if not vvip_list:
        return await status_msg.edit(
            f"{em.cross_mark} Belum ada data VVIP.", parse_mode="html"
        )

    report_text = f"{em.mag} Laporan Status Grup VVIP\n\n"

    for item in vvip_list:
        chat_id_target = item.get("chat_id_normal")
        name = item.get("name")

        try:
            chat = await client.get_entity(chat_id_target)

            invite_link = "Tidak Ada"
            if getattr(chat, "username", None):
                invite_link = f"https://t.me/{chat.username}"
            else:
                try:
                    if isinstance(chat, types.Channel):
                        full_chat = await client(
                            functions.channels.GetFullChannelRequest(channel=chat)
                        )
                    else:
                        full_chat = await client(
                            functions.messages.GetFullChatRequest(chat_id=chat.id)
                        )

                    exported = getattr(full_chat.full_chat, "exported_invite", None)
                    if exported and getattr(exported, "link", None):
                        invite_link = exported.link
                except Exception:
                    pass

            if getattr(chat, "restricted", False):
                reason_text = "Dibatasi oleh Telegram"
                if getattr(chat, "restriction_reason", None):
                    reason_text = f"{chat.restriction_reason[0].platform}: {chat.restriction_reason[0].reason}"
                report_text += (
                    f"{em.card_index_dividers} Nama: {name}\n"
                    f"{em.bulb} Grup: {chat.title}\n"
                    f"{em.link} Link: {invite_link}\n"
                    f"{em.hot_springs} STATUS: BANNED/DIBATASI\n"
                    f"Alasan: {reason_text}\n\n"
                )
            else:
                report_text += (
                    f"{em.card_index_dividers} Nama: {name}\n"
                    f"{em.bulb} Grup: {chat.title}\n"
                    f"{em.link} Link: {invite_link}\n"
                    f"{em.white_check_mark} Status: Aman\n\n"
                )
        except Exception:
            report_text += (
                f"{em.card_index_dividers} Nama: {name}\n"
                f"{em.cross_mark} Error: Tidak dapat mengakses grup (ID: {chat_id_target}). Pastikan bot adalah admin.\n\n"
            )

        if len(report_text) > 3500:
            await client.send_message(chat_id, report_text, parse_mode="html")
            report_text = ""

    if report_text:
        await client.send_message(chat_id, report_text, parse_mode="html")

    layout = [
        [
            {
                "text": "◀️ Kembali ke Pengaturan",
                "callback_data": "settings",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await status_msg.delete()
    await client.send_message(
        chat_id,
        f"{em.white_check_mark} Pemeriksaan Selesai.",
        buttons=btn,
        parse_mode="html",
    )


@command(lambda ctx: events.CallbackQuery(pattern=b"^vip_revenue_menu$"))
async def vip_revenue_menu_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    text = (
        f"{em.money_bag} <b>Cek Pendapatan VIP</b>\n\n"
        f"Pilih periode waktu untuk melihat total pendapatan dari penjualan paket VIP."
    )
    layout = [
        [
            {
                "text": "📅 Harian (Hari Ini)",
                "callback_data": "show_revenue_daily",
                "style": "primary",
                "emoji": 5431897022456145283,
            },
            {
                "text": "📅 Mingguan (7 Hari)",
                "callback_data": "show_revenue_weekly",
                "style": "primary",
                "emoji": 5431897022456145283,
            },
        ],
        [
            {
                "text": "📅 Bulanan (Bulan Ini)",
                "callback_data": "show_revenue_monthly",
                "style": "primary",
                "emoji": 5431897022456145283,
            }
        ],
        [
            {
                "text": "◀️ Kembali ke Pengaturan",
                "callback_data": "settings",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^show_revenue_"))
async def show_vip_revenue_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    payload = event.data.decode("utf-8")
    period = payload.split("_")[2]

    revenue_history = await ctx.db.getListVars(client.uid, "vip_revenue_history") or []
    now = datetime.now(ZoneInfo("Asia/Jakarta"))

    total_amount = 0
    transaction_count = 0

    for record in revenue_history:
        try:
            record_date = datetime.fromisoformat(record["date"]).astimezone(
                ZoneInfo("Asia/Jakarta")
            )
            include_record = False

            if period == "daily":
                if record_date.date() == now.date():
                    include_record = True
            elif period == "weekly":
                if now - timedelta(days=7) <= record_date <= now:
                    include_record = True
            elif period == "monthly":
                if record_date.year == now.year and record_date.month == now.month:
                    include_record = True

            if include_record:
                total_amount += int(record["amount"])
                transaction_count += 1
        except Exception:
            continue

    period_text = {
        "daily": "Harian",
        "weekly": "Mingguan",
        "monthly": "Bulanan",
    }.get(period, "Harian")

    text = (
        f"{em.chart_bar} <b>Laporan Pendapatan VIP</b>\n\n"
        f"<b>Periode:</b> {period_text}\n\n"
        f"{em.money_bag} <b>Total Pendapatan:</b> <code>Rp {total_amount:,}</code>\n"
        f"{em.repeat} <b>Jumlah Transaksi:</b> <code>{transaction_count}</code>"
    )

    layout = [
        [
            {
                "text": "◀️ Kembali",
                "callback_data": "vip_revenue_menu",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ]
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^set_start_photo$"))
async def set_start_photo_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return await event.answer(
            "⛔ Anda tidak memiliki akses ke menu ini.", alert=True
        )

    chat_id = sender.id
    await event.delete()

    layout = [
        [
            {
                "text": "◀️ Kembali ke Pengaturan",
                "callback_data": "settings",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        prompt = (
            f"{em.frame} <b>Atur Foto Start</b>\n\n"
            f"Silakan kirim foto baru yang ingin Anda gunakan sebagai gambar di pesan /start.\n\n"
            f"Ketik <code>/empty</code> untuk menghapus foto saat ini dan kembali ke default.\n\n"
            f"Ketik <code>/batal</code> untuk membatalkan."
        )
        ask_photo_msg = await client.ask(chat_id, prompt, parse_mode="html")

        if ask_photo_msg.text:
            if ask_photo_msg.text.lower() == "/empty":
                await ctx.db.removeVars(client.uid, "start_photo_id")
                invalidate_setting_cache(client.uid, "start_photo_id")
                return await client.send_message(
                    chat_id,
                    f"{em.white_check_mark} <b>Sukses!</b> Foto /start telah dihapus dan akan kembali ke default.",
                    buttons=back_btn,
                    parse_mode="html",
                )

        if not ask_photo_msg.photo:
            return await client.send_message(
                chat_id,
                f"{em.cross_mark} <b>Gagal:</b> Pesan yang dikirim bukan foto. Proses dibatalkan.",
                buttons=back_btn,
                parse_mode="html",
            )

        photo = ask_photo_msg.photo
        photo_data = {
            "id": photo.id,
            "access_hash": photo.access_hash,
            "file_reference": binascii.hexlify(photo.file_reference).decode("utf-8"),
        }

        await ctx.db.setVars(client.uid, "start_photo_id", photo_data)
        invalidate_setting_cache(client.uid, "start_photo_id")

        await client.send_message(
            chat_id,
            f"{em.white_check_mark} <b>Sukses!</b> Foto /start telah berhasil diperbarui.",
            buttons=back_btn,
            parse_mode="html",
        )
    except client.userCancel:
        await client.send_message(
            chat_id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            buttons=back_btn,
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses telah dibatalkan otomatis.",
            buttons=back_btn,
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            f"{em.cross_mark} <b>Terjadi Kesalahan</b>\n<pre>{e}</pre>",
            buttons=back_btn,
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^set_start_text$"))
async def set_start_text_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    chat_id = sender.id
    await event.delete()

    layout = [
        [
            {
                "text": "◀️ Kembali ke Pengaturan",
                "callback_data": "settings",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        prompt = (
            f"{em.pen} <b>Atur Teks Start</b>\n\n"
            f"Silakan kirim teks baru untuk pesan /start. Anda dapat menggunakan variabel "
            f"<code>{{mention}}</code> untuk menyapa pengguna.\n\n"
            f"<b>Contoh:</b> <code>Halo {{mention}}, selamat datang di bot saya!</code>\n\n"
            f"Ketik <code>/empty</code> untuk menghapus teks kustom dan kembali ke default.\n\n"
            f"Ketik <code>/batal</code> untuk membatalkan."
        )
        ask_text_msg = await client.ask(chat_id, prompt, parse_mode="html")

        if not ask_text_msg.text:
            return await client.send_message(
                chat_id,
                f"{em.cross_mark} <b>Gagal:</b> Pesan yang dikirim tidak berisi teks. Proses dibatalkan.",
                buttons=back_btn,
                parse_mode="html",
            )

        if ask_text_msg.text.lower() == "/empty":
            await ctx.db.removeVars(client.uid, "start_text_template")
            invalidate_setting_cache(client.uid, "start_text_template")
            return await client.send_message(
                chat_id,
                f"{em.white_check_mark} <b>Sukses!</b> Teks /start telah dihapus dan akan kembali ke default.",
                buttons=back_btn,
                parse_mode="html",
            )

        html_text = (
            html_unparse(ask_text_msg.message, ask_text_msg.entities)
            if ask_text_msg.entities
            else ask_text_msg.message
        )
        await ctx.db.setVars(client.uid, "start_text_template", html_text)
        invalidate_setting_cache(client.uid, "start_text_template")

        await client.send_message(
            chat_id,
            f"{em.white_check_mark} <b>Sukses!</b> Teks /start telah berhasil diperbarui.",
            buttons=back_btn,
            parse_mode="html",
        )
    except client.userCancel:
        await client.send_message(
            chat_id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            buttons=back_btn,
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses telah dibatalkan otomatis.",
            buttons=back_btn,
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            f"{em.cross_mark} <b>Terjadi Kesalahan</b>\n<pre>{e}</pre>",
            buttons=back_btn,
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^set_broadcast_price$"))
async def set_broadcast_price_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    chat_id = sender.id
    await event.delete()

    layout = [
        [
            {
                "text": "◀️ Kembali ke Pengaturan",
                "callback_data": "settings",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        prompt = (
            f"{em.glowing_star} <b>Atur Harga Broadcast Paid</b>\n\n"
            f"Masukkan jumlah Bintang (Stars) yang harus dibayar pengguna untuk melihat media broadcast.\n\n"
            f"Ketik <code>0</code> atau <code>/empty</code> untuk menonaktifkan fitur ini.\n\n"
            f"Ketik <code>/batal</code> untuk membatalkan."
        )
        ask_msg = await client.ask(chat_id, prompt, parse_mode="html")

        if ask_msg.text:
            if ask_msg.text.lower() in ["/empty", "0"]:
                await ctx.db.removeVars(client.uid, "broadcast_price")
                return await client.send_message(
                    chat_id,
                    f"{em.white_check_mark} <b>Sukses!</b> Fitur Paid Broadcast dinonaktifkan.",
                    buttons=back_btn,
                    parse_mode="html",
                )

        if not ask_msg.text.isdigit():
            raise ValueError("Format Salah")

        stars_amount = int(ask_msg.text)
        await ctx.db.setVars(client.uid, "broadcast_price", stars_amount)

        await client.send_message(
            chat_id,
            f"{em.white_check_mark} <b>Sukses!</b> Harga broadcast telah diatur menjadi "
            f"<code>{stars_amount}</code> Stars.",
            buttons=back_btn,
            parse_mode="html",
        )
    except client.userCancel:
        await client.send_message(
            chat_id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            buttons=back_btn,
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses telah dibatalkan otomatis.",
            buttons=back_btn,
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            f"{em.cross_mark} <b>Terjadi Kesalahan</b>\n<pre>{e}</pre>",
            buttons=back_btn,
            parse_mode="html",
        )


async def _send_broadcast_message(
    client, target_user_id, source_message, broadcast_price=0
):
    raw_text = source_message.message or ""
    reply_markup, cleaned_text = client.ns.telegram.button.create_inline_keyboard(
        raw_text
    )
    final_markup = reply_markup if reply_markup else source_message.reply_markup

    if broadcast_price > 0 and (source_message.photo or source_message.video):
        media_list = []
        temp_file = await client.download_media(source_message)
        uploaded_file = await client.upload_file(temp_file)

        if source_message.photo:
            media_list.append(types.InputMediaUploadedPhoto(file=uploaded_file))
        elif source_message.video:
            media_list.append(
                types.InputMediaUploadedDocument(
                    file=uploaded_file,
                    mime_type="video/mp4",
                    attributes=[
                        types.DocumentAttributeVideo(
                            duration=(
                                source_message.video.duration
                                if hasattr(source_message.video, "duration")
                                else 10
                            ),
                            w=(
                                source_message.video.w
                                if hasattr(source_message.video, "w")
                                else 640
                            ),
                            h=(
                                source_message.video.h
                                if hasattr(source_message.video, "h")
                                else 360
                            ),
                        )
                    ],
                )
            )

        await client.send_message(
            target_user_id,
            message=cleaned_text,
            file=types.InputMediaPaidMedia(
                stars_amount=broadcast_price, extended_media=media_list
            ),
            buttons=final_markup,
        )

        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return

    if source_message.photo:
        await client.send_message(
            target_user_id,
            message=cleaned_text,
            file=source_message.photo,
            buttons=final_markup,
        )
    elif source_message.text:
        await client.send_message(
            target_user_id, message=cleaned_text, buttons=final_markup
        )
    else:
        await client.send_message(
            target_user_id,
            message=cleaned_text,
            file=source_message.media,
            buttons=final_markup,
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^broadcast$"))
async def broadcast_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return await event.answer(
            "⛔ Anda tidak memiliki akses ke menu ini.", alert=True
        )

    chat_id = event.chat_id
    bot_id = client.uid

    try:
        await event.delete()
        prompt = (
            f"{em.loudspeaker} <b>Kirim Pesan Broadcast</b>\n\n"
            f"Silakan teruskan (forward) atau kirim pesan yang ingin Anda siarkan.\n\n"
            f"Ketik <code>/batal</code> untuk membatalkan."
        )
        ask_message = await client.ask(chat_id, prompt, parse_mode="html")

        broadcast_price = await ctx.db.getVars(bot_id, "broadcast_price") or 0
        broadcast_price = int(broadcast_price)

        if broadcast_price > 0 and (not (ask_message.photo or ask_message.video)):
            raise ValueError(
                f"{em.cross_mark} <b>Gagal:</b> Fitur Paid Broadcast sedang aktif seharga "
                f"{broadcast_price} Stars. Harus berupa Foto/Video!"
            )

        user_ids = await ctx.db.getListVars(client.uid, "user_ids") or []

        if not user_ids:
            return await client.send_message(
                chat_id,
                f"{em.cross_mark} <b>Gagal:</b> Tidak ada pengguna untuk disiarkan.",
                parse_mode="html",
            )

        progress_msg = await client.send_message(
            chat_id,
            f"{em.white_check_mark} Memulai siaran ke <code>{len(user_ids)}</code> pengguna...",
            parse_mode="html",
        )
        success_count, fail_count = 0, 0

        async def send_to_user(target_user_id):
            nonlocal success_count, fail_count
            try:
                await _send_broadcast_message(
                    client, target_user_id, ask_message, broadcast_price
                )
                success_count += 1
            except Exception:
                await ctx.db.removeListVars(client.uid, "user_ids", target_user_id)
                fail_count += 1
            await asyncio.sleep(0.1)

        for user_id in user_ids:
            if user_id != ctx.owner_id:
                await send_to_user(user_id)

        await progress_msg.delete()
        await client.send_message(
            chat_id,
            f"{em.loudspeaker} <b>Siaran Selesai!</b>\n"
            f"{em.white_check_mark} <b>Terkirim:</b> <code>{success_count}</code>\n"
            f"{em.cross_mark} <b>Gagal:</b> <code>{fail_count}</code>",
            parse_mode="html",
        )
    except client.userCancel:
        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        back_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(
            chat_id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            buttons=back_btn,
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        back_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(
            chat_id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses telah dibatalkan otomatis.",
            buttons=back_btn,
            parse_mode="html",
        )
    except Exception as e:
        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        back_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(
            chat_id,
            f"{em.cross_mark} <b>Terjadi Kesalahan</b>\n<pre>{e}</pre>",
            buttons=back_btn,
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^setup_listvvip$"))
async def setup_listvvip(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    chat_id = sender.id
    await event.delete()

    try:

        def ask(text):
            return client.ask(
                chat_id,
                text + "\n\nKetik <code>/batal</code> untuk membatalkan.",
                parse_mode="html",
            )

        def is_digit(t):
            return t.isdigit()

        def is_chatid(t):
            return t.lstrip("-").isdigit()

        vvip_data = {}

        name_msg = await ask(
            f"{em.pen} <b>Langkah 1/8: Nama Kategori</b>\nContoh: <code>VVIP Bulanan</code>"
        )
        vvip_data["name"] = name_msg.text.strip()

        price_msg = await ask(
            f"{em.money_bag} <b>Langkah 2/8: Harga Normal</b>\nContoh: <code>50000</code> (tanpa titik/koma)"
        )
        if not is_digit(price_msg.text.strip()):
            raise ValueError("Nilai harus berupa angka.")
        vvip_data["price"] = int(price_msg.text.strip())

        duration_msg = await ask(
            f"{em.hourglass} <b>Langkah 3/8: Durasi (Hari)</b>\nKirim <code>0</code> untuk permanen."
        )
        if not is_digit(duration_msg.text.strip()):
            raise ValueError("Nilai harus berupa angka.")
        vvip_data["duration"] = int(duration_msg.text.strip())

        chat_msg = await ask(
            f"<b>Langkah 4/8: Chat ID Grup Normal</b>\nContoh: <code>-100123456789</code>"
        )
        if not is_chatid(chat_msg.text.strip()):
            raise ValueError("ID harus berupa angka bulat.")
        vvip_data["chat_id_normal"] = int(chat_msg.text.strip())

        promo_msg = await ask(
            f"{em.party_popper} <b>Langkah 5/8: Harga Promo</b>\nKirim <code>0</code> jika tidak ada."
        )
        if not is_digit(promo_msg.text.strip()):
            raise ValueError("Nilai harus berupa angka.")
        vvip_data["promo_price"] = int(promo_msg.text.strip())

        if vvip_data["promo_price"] > 0:
            chat_promo_msg = await ask(f"<b>Langkah 6/8: Chat ID Grup Promo</b>")
            if not is_chatid(chat_promo_msg.text.strip()):
                raise ValueError("ID harus berupa angka bulat.")
            vvip_data["chat_id_promo"] = int(chat_promo_msg.text.strip())

            promo_text_msg = await ask(
                f"{em.pencil} <b>Langkah 7/8: Deskripsi Promo</b>\nKirim <code>/skip</code> untuk default."
            )
            vvip_data["promo_text"] = (
                ""
                if promo_text_msg.text.strip().lower() == "/skip"
                else (
                    html_unparse(promo_text_msg.message, promo_text_msg.entities)
                    if promo_text_msg.entities
                    else promo_text_msg.message
                )
            )
        else:
            vvip_data["chat_id_promo"], vvip_data["promo_text"] = 0, ""

        normal_text_msg = await ask(
            f"{em.pencil} <b>Langkah 8/8: Deskripsi Normal</b>\nKirim <code>/skip</code> untuk default."
        )
        vvip_data["normal_text"] = (
            ""
            if normal_text_msg.text.strip().lower() == "/skip"
            else (
                html_unparse(normal_text_msg.message, normal_text_msg.entities)
                if normal_text_msg.entities
                else normal_text_msg.message
            )
        )

        await ctx.db.setListVars(client.uid, "list_vvip", vvip_data)
        await client.send_message(
            chat_id,
            f"{em.white_check_mark} <b>Sukses!</b> Paket VVIP <b>{vvip_data['name']}</b> berhasil ditambahkan.",
            parse_mode="html",
        )
    except client.userCancel:
        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        back_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(
            chat_id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            buttons=back_btn,
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        back_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(
            chat_id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses telah dibatalkan otomatis.",
            buttons=back_btn,
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            f"{em.cross_mark} <b>Gagal Setup:</b> <code>{e}</code>",
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^delete_listvvip$"))
async def delete_listvvip(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    back_row = [
        {
            "text": "◀️ Kembali ke Pengaturan",
            "callback_data": "settings",
            "style": "primary",
            "emoji": 5373098009640836781,
        }
    ]

    if not vvip_list:
        text = f"{em.white_check_mark} Tidak ada paket VVIP untuk dihapus."
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await event.edit(text, buttons=btn, parse_mode="html")

    if not hasattr(ctx, "vip_list"):
        ctx.vip_list = {}

    layout = []
    button_row = []

    for item in vvip_list:
        name = item.get("name", "Tanpa Nama")
        item_id = uuid.uuid4().hex[:8]
        ctx.vip_list[item_id] = name
        button_row.append(
            {
                "text": f"🗑️ Hapus {name}",
                "callback_data": f"delete_vvip {item_id}",
                "style": "danger",
                "emoji": 5229113891081956317,
            }
        )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []

    if button_row:
        layout.append(button_row)

    layout.append(back_row)
    text = f"{em.shopping_bags} <b>Hapus Paket VVIP</b>\n\nPilih paket VVIP yang ingin Anda hapus."
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^delete_vvip "))
async def confirm_delete_vvip(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    payload = event.data.decode("utf-8")
    _, item_id = payload.split(" ", 1)

    if not hasattr(ctx, "vip_list") or item_id not in ctx.vip_list:
        return await event.answer("Sesi tidak ditemukan.", alert=True)

    name = ctx.vip_list[item_id]
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    item_to_remove = next(
        (item for item in vvip_list if item.get("name") == name), None
    )

    back_row = [
        {
            "text": "◀️ Kembali",
            "callback_data": "delete_listvvip",
            "style": "primary",
            "emoji": 5373098009640836781,
        }
    ]

    if item_to_remove:
        await ctx.db.removeListVars(client.uid, "list_vvip", item_to_remove)
        message = (
            f"{em.white_check_mark} <b>Berhasil!</b> Paket <b>{name}</b> telah dihapus."
        )
        del ctx.vip_list[item_id]
    else:
        message = f"{em.cross_mark} <b>Gagal!</b> Paket <b>{name}</b> tidak ditemukan."

    btn = client.ns.telegram.button.build_button_grid([back_row])
    await event.edit(message, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^edit_price_listvvip$"))
async def edit_price_listvvip_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    back_row = [
        {
            "text": "◀️ Kembali ke Pengaturan",
            "callback_data": "settings",
            "style": "primary",
            "emoji": 5373098009640836781,
        }
    ]

    if not vvip_list:
        text = f"{em.cross_mark} Belum ada paket VVIP."
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await event.edit(text, buttons=btn, parse_mode="html")

    if not hasattr(ctx, "vip_list_edit"):
        ctx.vip_list_edit = {}

    layout = []
    button_row = []

    for item in vvip_list:
        name = item.get("name", "Tanpa Nama")
        item_id = uuid.uuid4().hex[:8]
        ctx.vip_list_edit[item_id] = name
        button_row.append(
            {
                "text": f"✏️ Edit {name}",
                "callback_data": f"edit_vvip_price {item_id}",
                "style": "primary",
                "emoji": 5334882760735598374,
            }
        )
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []

    if button_row:
        layout.append(button_row)

    layout.append(back_row)
    text = f"{em.pencil} <b>Edit Harga VVIP</b>\n\nPilih paket VVIP yang ingin Anda ubah harganya."
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^edit_vvip_price "))
async def edit_vvip_price_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    chat_id = sender.id
    payload = event.data.decode("utf-8")
    _, item_id = payload.split(" ", 1)

    if not hasattr(ctx, "vip_list_edit") or item_id not in ctx.vip_list_edit:
        return await event.answer("Sesi tidak ditemukan.", alert=True)

    name = ctx.vip_list_edit[item_id]
    vvip_list = await ctx.db.getListVars(client.uid, "list_vvip") or []
    old_item = next((item for item in vvip_list if item.get("name") == name), None)

    if not old_item:
        return await event.answer("Paket tidak ditemukan.", alert=True)

    await event.delete()
    try:

        def ask(text):
            return client.ask(
                chat_id,
                text + "\n\nKetik <code>/batal</code> untuk membatalkan.",
                parse_mode="html",
            )

        new_price_msg = await ask(
            f"{em.money_bag} <b>Masukkan Harga Normal Baru</b>\n"
            f"Harga sebelumnya: <code>{old_item.get('price', 0)}</code>"
        )
        if not new_price_msg.text.strip().isdigit():
            raise ValueError("Harga harus berupa angka.")
        new_normal_price = int(new_price_msg.text.strip())

        new_promo_msg = await ask(
            f"{em.party_popper} <b>Masukkan Harga Promo Baru</b>\n"
            f"Harga sebelumnya: <code>{old_item.get('promo_price', 0)}</code>"
        )
        if not new_promo_msg.text.strip().isdigit():
            raise ValueError("Harga harus berupa angka.")
        new_promo_price = int(new_promo_msg.text.strip())

        new_item = old_item.copy()
        new_item["price"] = new_normal_price
        new_item["promo_price"] = new_promo_price

        await ctx.db.removeListVars(client.uid, "list_vvip", old_item)
        await ctx.db.setListVars(client.uid, "list_vvip", new_item)
        del ctx.vip_list_edit[item_id]

        await client.send_message(
            chat_id,
            f"{em.white_check_mark} <b>Sukses!</b>\n"
            f"Harga paket VVIP <b>{name}</b> berhasil diubah.\n"
            f"Normal: <code>Rp {new_normal_price:,}</code>\n"
            f"Promo: <code>Rp {new_promo_price:,}</code>",
            parse_mode="html",
        )
    except client.userCancel:
        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        back_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(
            chat_id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            buttons=back_btn,
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        back_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(
            chat_id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses telah dibatalkan otomatis.",
            buttons=back_btn,
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            f"{em.cross_mark} <b>Terjadi Kesalahan:</b> <code>{e}</code>",
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^api_settings$"))
async def api_settings_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    saweria_user_id = await ctx.db.getVars(client.uid, "SAWERIA_USER_ID")
    saweria_status = (
        f"{em.white_check_mark} Aktif"
        if saweria_user_id
        else f"{em.cross_mark} Belum Diatur"
    )

    layout = [
        [
            {
                "text": "🔑 Atur Kunci Saweria",
                "callback_data": "set_api SAWERIA",
                "style": "primary",
                "emoji": 5330115548900501467,
            }
        ],
        [
            {
                "text": "🗑️ Hapus Semua Kunci",
                "callback_data": "del_api_confirm",
                "style": "danger",
                "emoji": 5229113891081956317,
            }
        ],
        [
            {
                "text": "◀️ Kembali ke Pengaturan",
                "callback_data": "settings",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ],
    ]

    text = (
        f"{em.key} <b>Pengelola Kunci API</b>\n\n"
        f"Atur koneksi pembayaran Saweria untuk bot Anda.\n\n"
        f"<b>Status Layanan:</b>\n"
        f"- <code>Gateway Pembayaran (Saweria)</code>: <b>{saweria_status}</b>"
    )
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^set_api "))
async def set_api_key_prompt(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    chat_id = sender.id
    payload = event.data.decode("utf-8")
    _, key_name = payload.split(" ", 1)
    await event.delete()

    layout = [
        [
            {
                "text": "◀️ Kembali ke Pengaturan API",
                "callback_data": "api_settings",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ]
    ]
    back_btn = client.ns.telegram.button.build_button_grid(layout)

    try:
        if key_name == "SAWERIA":
            username_msg = await client.ask(
                chat_id,
                f"Kirim <b>Username Saweria</b> Anda.\n\nKetik <code>/batal</code> untuk membatalkan.",
                parse_mode="html",
            )
            username_val = username_msg.text.strip()

            processing_msg = await client.send_message(
                chat_id,
                f"{em.hourglass} <b>Sedang Memproses...</b>",
                parse_mode="html",
            )

            try:
                saweria_temp = client.ns.payment.SaweriaScraper()
                user_id_saweria = await saweria_temp.get_user_id(username=username_val)

                if not user_id_saweria:
                    raise Exception("Username tidak ditemukan.")

                await ctx.db.setVars(client.uid, "SAWERIA_USER_ID", user_id_saweria)
                await processing_msg.delete()
                await client.send_message(
                    chat_id,
                    f"{em.white_check_mark} <b>Sukses!</b> Kunci Saweria berhasil disimpan.",
                    buttons=back_btn,
                    parse_mode="html",
                )
            except Exception as e:
                await processing_msg.edit(
                    f"{em.cross_mark} <b>Gagal!</b>\nUsername Saweria tidak ditemukan.\n\n"
                    f"<code>Error: {e}</code>",
                    buttons=back_btn,
                    parse_mode="html",
                )
                return

        from services import initialize_bot_services

        await initialize_bot_services(client, ctx.db)
    except client.userCancel:
        await client.send_message(
            chat_id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            buttons=back_btn,
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        await client.send_message(
            chat_id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses telah dibatalkan otomatis.",
            buttons=back_btn,
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            f"{em.cross_mark} <b>Terjadi Kesalahan:</b> <code>{e}</code>",
            buttons=back_btn,
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^del_api_confirm$"))
async def confirm_delete_api_keys(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    text = (
        f"{em.anger} <b>Konfirmasi</b>\n\n"
        f"Anda yakin ingin menghapus <b>SEMUA</b> kunci API untuk bot ini?"
    )
    layout = [
        [
            {
                "text": "🗑️ Ya, Hapus Semua",
                "callback_data": "do_del_api",
                "style": "danger",
                "emoji": 5229113891081956317,
            },
            {
                "text": "❌ Tidak, Batalkan",
                "callback_data": "api_settings",
                "style": "primary",
                "emoji": 5465665476971471368,
            },
        ]
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^do_del_api$"))
async def do_delete_api_keys(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    await ctx.db.removeVars(client.uid, "SAWERIA_USER_ID")

    from services import initialize_bot_services

    await initialize_bot_services(client, ctx.db)

    await event.answer("✅ Semua kunci API berhasil dihapus.", alert=True)
    await api_settings_callback(client, event)


@command(lambda ctx: events.CallbackQuery(pattern=b"^manage_coupons"))
async def manage_coupons_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    text = f"{em.ticket} <b>Manajemen Kupon</b>\nKelola kode diskon untuk VVIP Anda."
    layout = [
        [
            {
                "text": "➕ Buat Kupon Baru",
                "callback_data": "add_coupon",
                "style": "success",
                "emoji": 5226945370684140473,
            }
        ],
        [
            {
                "text": "📋 Lihat Kupon",
                "callback_data": "list_coupons_0",
                "style": "primary",
                "emoji": 5372926953978341366,
            }
        ],
        [
            {
                "text": "◀️ Kembali ke Pengaturan",
                "callback_data": "settings",
                "style": "primary",
                "emoji": 5373098009640836781,
            }
        ],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^add_coupon"))
async def add_coupon_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    chat_id = sender.id
    await event.delete()

    try:

        def ask(text):
            return client.ask(
                chat_id,
                text + "\n\nKetik <code>/batal</code> untuk membatalkan.",
                parse_mode="html",
            )

        code_msg = await ask(
            f"Masukkan kode kupon unik (misal: <code>DISKONBARU</code>)."
        )
        code = code_msg.text.strip().upper()

        type_msg = await ask(
            f"Pilih tipe diskon:\n"
            f"<code>1</code>. Persentase (%)\n"
            f"<code>2</code>. Potongan Harga Tetap"
        )
        discount_type = "percentage" if "1" in type_msg.text else "fixed"

        val_prompt = (
            f"Masukkan nilai persentase (misal: <code>15</code>)."
            if discount_type == "percentage"
            else f"Masukkan jumlah potongan harga (misal: <code>10000</code>)."
        )
        val_msg = await ask(val_prompt)
        discount_value = int(val_msg.text.strip())

        uses_msg = await ask("Berapa kali kupon ini bisa digunakan? (masukkan angka)")
        uses_left = int(uses_msg.text.strip())

        expiry_msg = await ask("Berapa hari kupon ini akan berlaku? (masukkan angka)")
        expiry_days = int(expiry_msg.text.strip())

        expiry_date = (
            (datetime.now(timezone.utc) + timedelta(days=expiry_days)).isoformat()
            if expiry_days > 0
            else None
        )

        coupon_data = {
            "code": code,
            "discount_type": discount_type,
            "discount_value": discount_value,
            "uses_left": uses_left,
            "expiry_date": expiry_date,
        }

        await ctx.db.setListVars(client.uid, "coupons", coupon_data)
        await client.send_message(
            chat_id,
            f"{em.white_check_mark} Kupon <code>{code}</code> berhasil dibuat.",
            parse_mode="html",
        )
    except client.userCancel:
        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        back_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(
            chat_id,
            f"{em.no_entry_age} <b>Proses Dibatalkan</b>",
            buttons=back_btn,
            parse_mode="html",
        )
    except asyncio.TimeoutError:
        layout = [
            [
                {
                    "text": "◀️ Kembali ke Pengaturan",
                    "callback_data": "settings",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                }
            ]
        ]
        back_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(
            chat_id,
            f"{em.alarm_clock} <b>Waktu Habis</b>\nProses telah dibatalkan otomatis.",
            buttons=back_btn,
            parse_mode="html",
        )
    except Exception as e:
        await client.send_message(
            chat_id,
            f"{em.cross_mark} <b>Gagal Membuat Kupon:</b> <code>{e}</code>",
            parse_mode="html",
        )


@command(lambda ctx: events.CallbackQuery(pattern=b"^list_coupons_"))
async def list_coupons_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    payload = event.data.decode("utf-8")
    page = int(payload.split("_")[2])

    coupons = await ctx.db.getListVars(client.uid, "coupons") or []
    back_row = [
        {
            "text": "◀️ Kembali",
            "callback_data": "manage_coupons",
            "style": "primary",
            "emoji": 5373098009640836781,
        }
    ]

    if not coupons:
        btn = client.ns.telegram.button.build_button_grid([back_row])
        return await event.edit("Tidak ada kupon yang dibuat.", buttons=btn)

    total_pages = len(coupons)
    page = max(0, min(page, total_pages - 1))
    coupon = coupons[page]

    expiry_text = "Permanent"
    if coupon.get("expiry_date"):
        expiry_text = datetime.fromisoformat(coupon["expiry_date"]).strftime("%d %b %Y")

    text = (
        f"{em.ticket} <b>Detail Kupon ({page + 1}/{total_pages})</b>\n"
        f"- Kode: <code>{coupon['code']}</code>\n"
        f"- Tipe: <code>{coupon['discount_type']}</code>\n"
        f"- Nilai: <code>{coupon['discount_value']}</code>\n"
        f"- Sisa Penggunaan: <code>{coupon['uses_left']}</code>\n"
        f"- Berlaku hingga: <code>{expiry_text}</code>"
    )

    layout = []
    pagination_row = []

    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = page + 1 if page + 1 < total_pages else page
        pagination_row.extend(
            [
                {
                    "text": "«",
                    "callback_data": f"list_coupons_{prev_page}",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                },
                {
                    "text": "»",
                    "callback_data": f"list_coupons_{next_page}",
                    "style": "primary",
                    "emoji": 5373098009640836781,
                },
            ]
        )

    layout.append(
        [
            {
                "text": "🗑️ Hapus Kupon Ini",
                "callback_data": f"delete_coupon {coupon['code']} {page}",
                "style": "danger",
                "emoji": 5229113891081956317,
            }
        ]
    )

    if pagination_row:
        layout.append(pagination_row)

    layout.append(back_row)
    btn = client.ns.telegram.button.build_button_grid(layout)

    await event.edit(text, buttons=btn, parse_mode="html")


@command(lambda ctx: events.CallbackQuery(pattern=b"^delete_coupon "))
async def delete_coupon_callback(client, event):
    sender = await event.get_sender()
    em = client.ns.emoji

    if not await is_bot_owner(client, sender.id):
        return

    payload = event.data.decode("utf-8")
    _, code, page_str = payload.split()

    coupons = await ctx.db.getListVars(client.uid, "coupons") or []
    coupon_to_remove = next((c for c in coupons if c.get("code") == code), None)

    if coupon_to_remove:
        await ctx.db.removeListVars(client.uid, "coupons", coupon_to_remove)
        await event.answer("✅ Kupon berhasil dihapus.", alert=True)

    new_page = int(page_str)
    remaining_coupons = await ctx.db.getListVars(client.uid, "coupons") or []

    if new_page >= len(remaining_coupons) and len(remaining_coupons) > 0:
        new_page = len(remaining_coupons) - 1

    event.data = f"list_coupons_{new_page}".encode("utf-8")
    await list_coupons_callback(client, event)
