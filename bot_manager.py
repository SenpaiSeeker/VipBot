import asyncio
import time
from datetime import datetime, timedelta, timezone

import pyrogram
from pyrogram.types import InputRichMessage

import VvipBot as handlers
from database import schedule
from helpers import parse_dt
from helpers.logger import LoggerHandler
from VvipBot import ctx

log = LoggerHandler()

START_CONCURRENCY = 3
START_STAGGER_SECONDS = 0.75


class BotManager:
    def __init__(self, db_instance, owner_id):
        self.db = db_instance
        self.owner_id = owner_id
        self.running_bots = {}
        self.main_bot_client = None
        self.main_bot_id = None
        self._flood_until = {}

    async def flood_remaining(self, bot_id):
        try:
            bot_id = int(bot_id)
        except (TypeError, ValueError):
            return 0
        until = self._flood_until.get(bot_id, 0)
        if not until:
            try:
                until = float(await self.db.getVars(bot_id, "flood_until") or 0)
            except Exception:
                until = 0
            if until:
                self._flood_until[bot_id] = until
        return max(0, int(until - time.time()))

    async def _mark_flood(self, bot_id, wait):
        until = time.time() + max(0, int(wait or 0))
        self._flood_until[bot_id] = until
        try:
            await self.db.setVars(bot_id, "flood_until", until)
        except Exception as e:
            log.print(f"{log.RED}Gagal menyimpan FloodWait {bot_id}: {e}")

    async def start_bot(self, bot_data):
        bot_id = int(bot_data["name"])
        if bot_id in self.running_bots:
            log.warning(f"Bot {bot_id} sudah berjalan.")
            return

        remaining = await self.flood_remaining(bot_id)
        if remaining > 0:
            log.warning(
                f"Bot {bot_id} masih FloodWait ({remaining}s), lewati percobaan start."
            )
            return

        try:
            client = pyrogram.Client(
                name=str(bot_id),
                api_id=bot_data["api_id"],
                api_hash=bot_data["api_hash"],
                bot_token=bot_data["bot_token"],
                in_memory=True,
            )

            handlers.register_all_handlers(client, self.db, self, self.owner_id)

            await client.start()

            self.running_bots[client.me.id] = client
            log.info(
                f"Bot {client.me.first_name} (ID: {client.me.id}) berhasil diaktifkan."
            )
        except Exception as e:
            error_str = str(e).upper()
            common_errors = [
                "USER_DEACTIVATED_BAN",
                "BOT_TOKEN_INVALID",
                "ACCESS_TOKEN_EXPIRED",
            ]

            log.print(f"{log.RED}Gagal memulai bot {bot_id}: {e}")
            if isinstance(e, pyrogram.errors.FloodWait):
                wait = int(getattr(e, "value", 0) or 0)
                await self._mark_flood(bot_id, wait)
                log.print(
                    f"{log.RED}Bot {bot_id} kena FloodWait {wait}s, start dijeda."
                )
                return
            if any(err in error_str for err in common_errors):
                await self.db.removeBot(bot_id)
                log.debug(
                    f"Data bot {bot_id} dihapus karena token tidak valid/terblokir."
                )

    async def start_all_bots(self):
        all_bots_data = await self.db.getBots(is_token=True)
        semaphore = asyncio.Semaphore(START_CONCURRENCY)

        async def start_one(bot_data):
            async with semaphore:
                await self.start_bot(bot_data)
                await asyncio.sleep(START_STAGGER_SECONDS)

        await asyncio.gather(*(start_one(bot_data) for bot_data in all_bots_data))

    async def stop_bot(self, bot_id):
        if bot_id in self.running_bots:
            try:
                client = self.running_bots[bot_id]
                if client.is_connected:
                    await client.stop()
                log.debug(f"Bot {bot_id} berhasil dihentikan.")
            except Exception as e:
                log.error(f"Error saat menghentikan bot {bot_id}: {e}")
            finally:
                del self.running_bots[bot_id]


@schedule.cron("*/5 * * * *")
async def flood_retry_method():
    manager = ctx.manager
    if not manager:
        return

    try:
        all_bots_data = await manager.db.getBots(is_token=True)
    except Exception as e:
        log.error(f"Gagal memuat daftar bot untuk retry FloodWait: {e}")
        return

    for bot_data in all_bots_data:
        try:
            bot_id = int(bot_data.get("name"))
        except (TypeError, ValueError):
            continue

        if bot_id in manager.running_bots:
            continue

        remaining = await manager.flood_remaining(bot_id)
        if remaining > 0:
            continue

        log.info(f"Mencoba mengaktifkan kembali bot {bot_id} setelah FloodWait.")
        await manager.start_bot(bot_data)


@schedule.cron("0 * * * *")
async def expiration_checker_method():
    log.info(f"Menjalankan pemeriksaan masa aktif bot...")
    manager = ctx.manager
    if not manager:
        log.warning("BotManager belum diinisialisasi di ctx. Melewati pemeriksaan.")
        return

    all_bot_ids = [bot["name"] for bot in await manager.db.getBots(is_token=True)]

    for bot_id_str in all_bot_ids:
        bot_id = int(bot_id_str)
        try:
            expiry_date_str = await manager.db.getVars(bot_id, "bot_expiration_date")
            if not expiry_date_str:
                continue

            expiry_date = parse_dt(expiry_date_str)
            if not expiry_date:
                continue
            time_remaining = expiry_date - datetime.now(timezone.utc)
            days_left = time_remaining.days

            owner_id = await manager.db.getVars(bot_id, "owner_id")
            if not owner_id:
                continue

            main_client = manager.main_bot_client
            if not main_client:
                continue

            if days_left < 1:
                bot_instance = manager.running_bots.get(bot_id)
                log.debug(f"Masa aktif bot {bot_id} telah habis. Menghapus bot...")
                try:
                    bot_name = (
                        bot_instance.me.first_name
                        if bot_instance and bot_instance.is_connected
                        else f"ID {bot_id}"
                    )
                    expired_message = (
                        f"{main_client.ns.emoji.md('cross_mark')} **Masa Aktif Habis**\n\n"
                        f"{main_client.ns.table.md(['Info', 'Nilai'], [['Bot', f'**{bot_name}**'], ['Status', 'Masa aktif sudah habis']])}"
                    )
                    await main_client.send_rich_message(
                        owner_id,
                        InputRichMessage(markdown=expired_message),
                    )
                except Exception:
                    await bot_instance.send_rich_message(
                        owner_id,
                        InputRichMessage(markdown=expired_message),
                    )

                await manager.stop_bot(bot_id)
                await manager.db.removeBot(bot_id)
                log.warning(f"Bot {bot_id} telah dihapus karena kedaluwarsa.")
                continue

            target_warning_days = [10, 5, 3, 1]
            if days_left in target_warning_days:
                last_notif_date_key = "last_warning_notification_date"
                last_notif_date_str = await manager.db.getVars(
                    bot_id, last_notif_date_key
                )
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                if last_notif_date_str != today_str:
                    try:
                        bot_instance = manager.running_bots.get(bot_id)
                        bot_name = (
                            bot_instance.me.first_name
                            if bot_instance and bot_instance.is_connected
                            else f"ID {bot_id}"
                        )

                        notif_client = bot_instance if bot_instance else main_client
                        owner_user = await notif_client.get_users(owner_id)
                        mention_owner = notif_client.ns.telegram.arg.getMention(
                            owner_user, md=True
                        )

                        warning_message = (
                            f"{notif_client.ns.emoji.md('bell')} **Notifikasi Masa Aktif**\n\n"
                            f"{notif_client.ns.table.md(['Info', 'Nilai'], [['Pengguna', f'{mention_owner}'], ['Bot', f'**{bot_name}**'], ['Sisa Aktif', f'**{days_left} hari**'], ['Aksi', 'Silakan hubungi @NorSodikin jika mau diperpanjang']])}"
                        )
                        try:
                            await main_client.send_rich_message(
                                owner_id,
                                InputRichMessage(markdown=warning_message),
                            )
                        except Exception:
                            await bot_instance.send_rich_message(
                                owner_id,
                                InputRichMessage(markdown=warning_message),
                            )
                        await manager.db.setVars(
                            bot_id,
                            last_notif_date_key,
                            today_str,
                        )
                        log.print(
                            f"{log.CYAN}Mengirim notifikasi sisa {days_left} hari ke owner {owner_id} untuk bot {bot_id}"
                        )
                    except Exception as e:
                        log.print(
                            f"{log.RED}Gagal mengirim notifikasi perpanjangan ke owner {owner_id}: {e}"
                        )

            elif days_left > 10:
                last_notif_date_key = "last_warning_notification_date"
                if await manager.db.getVars(bot_id, last_notif_date_key):
                    await manager.db.removeVars(bot_id, last_notif_date_key)
                    log.info(f"Mereset flag tanggal notifikasi untuk bot {bot_id}.")

        except Exception as e:
            log.error(f"Error saat memeriksa masa aktif bot {bot_id}: {e}")


@schedule.cron("0 */12 * * *")
async def subscription_checker_method():
    log.info(f"Menjalankan pemeriksaan langganan anggota...")

    manager = ctx.manager
    if not manager:
        log.warning("BotManager belum diinisialisasi di ctx. Melewati pemeriksaan.")
        return

    now = datetime.now(timezone.utc)
    all_bot_ids_data = await manager.db.getBots(is_token=True)
    all_bot_ids = []
    for bot in all_bot_ids_data:
        try:
            all_bot_ids.append(int(bot["name"]))
        except (KeyError, TypeError, ValueError):
            continue

    for bot_id in all_bot_ids:
        bot_client = manager.running_bots.get(bot_id)
        if not bot_client or not bot_client.is_connected:
            continue

        members = await manager.db.getListVars(bot_id, "vvip_members") or []
        vvip_list = await manager.db.getListVars(bot_id, "list_vvip") or []
        expired_keys = set()

        for member in members:
            try:
                expiry_date_str = member.get("expiry_date")
                if not expiry_date_str:
                    continue

                expiry_date = parse_dt(expiry_date_str)
                if not expiry_date:
                    continue

                user_id = member["user_id"]
            except (KeyError, TypeError, ValueError) as e:
                log.error(f"Data member tidak valid di bot {bot_id}: {e}")
                continue
            if now > expiry_date:
                try:
                    chat_id = member["chat_id_kick"]
                    await bot_client.ban_chat_member(chat_id, user_id)
                    await asyncio.sleep(1)
                    await bot_client.unban_chat_member(chat_id, user_id)

                    vvip_name_val = member["vvip_name"]
                    expired_message_text = (
                        f"{bot_client.ns.emoji.md('hourglass_done')} **Langganan Berakhir**\n\n"
                        f"| Info | Detail |\n"
                        f"| :--- | :--- |\n"
                        f"| Paket | **{vvip_name_val}** |\n"
                        f"| Status | Berakhir - dikeluarkan dari grup |"
                    )
                    await bot_client.send_rich_message(
                        user_id,
                        InputRichMessage(markdown=expired_message_text),
                    )
                    expired_keys.add((str(user_id), str(chat_id)))
                    log.debug(
                        f"Langganan {user_id} di bot {bot_id} habis. Dikeluarkan dari grup."
                    )
                except Exception as e:
                    log.error(f"Gagal kick member {user_id} dari grup: {e}")
                continue

            time_left = expiry_date - now
            if timedelta(days=2) < time_left <= timedelta(days=3):
                last_notif_key = "last_renewal_notification_date"
                last_notif_date_str = await manager.db.getVars(
                    user_id,
                    f"{last_notif_key}_{bot_id}",
                )
                today_str = now.strftime("%Y-%m-%d")

                if last_notif_date_str != today_str:
                    try:
                        item_index = -1
                        for i, vvip_item in enumerate(vvip_list):
                            if vvip_item.get("name") == member["vvip_name"]:
                                item_index = i
                                break

                        if item_index != -1:
                            vvip_name_val = member["vvip_name"]
                            days_left_val = time_left.days
                            text = (
                                f"{bot_client.ns.emoji.md('bell')} **Pengingat Langganan**\n\n"
                                f"| Info | Detail |\n"
                                f"| :--- | :---: |\n"
                                f"| Paket | **{vvip_name_val}** |\n"
                                f"| Sisa Waktu | **{days_left_val} hari** |\n\n"
                                f"Perpanjang sekarang agar tidak kehilangan akses!"
                            )
                            layout = [
                                [
                                    {
                                        "text": "🔄 Perpanjang Sekarang",
                                        "callback_data": f"renew_sub_{item_index}",
                                        "style": "blue",
                                        "emoji": bot_client.ns.emoji.id("repeat"),
                                    }
                                ]
                            ]
                            btn = bot_client.ns.telegram.button.build_button_grid(
                                layout
                            )
                            await bot_client.send_rich_message(
                                user_id,
                                InputRichMessage(markdown=text),
                                reply_markup=btn,
                            )
                            await manager.db.setVars(
                                user_id,
                                f"{last_notif_key}_{bot_id}",
                                today_str,
                            )

                    except Exception as e:
                        log.print(
                            f"{ctx.log.RED}Gagal kirim notif perpanjangan ke {user_id}: {e}"
                        )

        if expired_keys:
            async with handlers.get_member_lock(bot_id):

                async def remove_expired(current_members):
                    filtered = []
                    for member in current_members:
                        key = (
                            str(member.get("user_id")),
                            str(member.get("chat_id_kick")),
                        )
                        if key not in expired_keys:
                            filtered.append(member)
                            continue

                        member_expiry = parse_dt(member.get("expiry_date"))
                        if member_expiry and member_expiry < datetime.now(
                            timezone.utc
                        ):
                            continue

                        filtered.append(member)

                    return (
                        filtered
                        if len(filtered) != len(current_members)
                        else None
                    )

                await manager.db.updateListVars(
                    bot_id,
                    "vvip_members",
                    remove_expired,
                )


_WATCHDOG_AUTH_ERRORS = (
    pyrogram.errors.SessionRevoked,
    pyrogram.errors.AuthKeyInvalid,
    pyrogram.errors.AuthKeyUnregistered,
    pyrogram.errors.UserDeactivatedBan,
    pyrogram.errors.AccessTokenExpired,
    pyrogram.errors.AccessTokenInvalid,
)

_WATCHDOG_AUTH_LABELS = {
    "SessionRevoked": "Sesi dicabut (SESSION_REVOKED)",
    "AuthKeyInvalid": "Sesi tidak valid",
    "AuthKeyUnregistered": "Sesi tidak terdaftar",
    "UserDeactivatedBan": "Akun dibanned",
    "AccessTokenExpired": "Token kedaluwarsa",
    "AccessTokenInvalid": "Token tidak valid",
}


@schedule.cron("*/15 * * * *")
async def watchdog_token_checker():
    log.info(f"Menjalankan watchdog token bot...")
    manager = ctx.manager
    if not manager:
        log.warning("BotManager belum diinisialisasi di ctx. Melewati pemeriksaan.")
        return

    main_client = manager.main_bot_client
    if not main_client:
        return

    for bot_id, bot_client in list(manager.running_bots.items()):
        if bot_id == manager.main_bot_id:
            continue
        try:
            await bot_client.get_me()
        except _WATCHDOG_AUTH_ERRORS as e:
            label = _WATCHDOG_AUTH_LABELS.get(
                type(e).__name__, "Token/sesi tidak valid"
            )
            try:
                bot_name = bot_client.me.first_name if bot_client.me else f"ID {bot_id}"
            except Exception:
                bot_name = f"ID {bot_id}"
            try:
                owner_id = await manager.db.getVars(bot_id, "owner_id")
            except Exception:
                owner_id = None

            log.print(
                f"{log.RED}Watchdog: bot {bot_id} ({bot_name}) {label}, menghapus..."
            )
            try:
                await manager.stop_bot(bot_id)
            except Exception:
                pass

            try:
                owner_text = f"`{owner_id}`" if owner_id else "Tidak diketahui"
                notif_text = (
                    f"{main_client.ns.emoji.md('shield')} **Watchdog: Bot Dihapus Otomatis**\n\n"
                    f"{main_client.ns.table.md(['Info', 'Nilai'], [['Bot', f'**{bot_name}** (`{bot_id}`)'], ['Penyebab', f'{label}'], ['Aksi', 'Bot dihentikan (data bot disimpan)'], ['Owner', f'{owner_text}'], ['Saran', 'Login ulang dengan token baru via `/login`']])}"
                )
                await main_client.send_rich_message(
                    manager.owner_id,
                    InputRichMessage(markdown=notif_text),
                )
            except Exception as notif_e:
                log.error(
                    f"Watchdog: gagal mengirim notifikasi hapus bot {bot_id}: {notif_e}"
                )
        except Exception:
            continue
