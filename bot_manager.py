import asyncio
from datetime import datetime, timezone, timedelta

import pyrogram
from nsdev import LoggerHandler

import VvipBot as handlers
from services import initialize_bot_services
from strings import Language

log = LoggerHandler()


class BotManager:
    def __init__(self, db_instance, owner_id):
        self.db = db_instance
        self.owner_id = owner_id
        self.running_bots = {}
        self.main_bot_client = None
        self.main_bot_id = None

    async def start_bot(self, bot_data):
        bot_id = int(bot_data["name"])
        if bot_id in self.running_bots:
            log.warning(f"Bot {bot_id} sudah berjalan.")
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

            initialize_bot_services(client, self.db)

            self.running_bots[client.me.id] = client
            log.info(f"Bot {client.me.first_name} (ID: {client.me.id}) berhasil diaktifkan.")
        except Exception as e:
            error_str = str(e).upper()
            common_errors = ["USER_DEACTIVATED_BAN", "BOT_TOKEN_INVALID", "ACCESS_TOKEN_EXPIRED"]

            log.print(f"{log.RED}Gagal memulai bot {bot_id}: {e}")
            if any(err in error_str for err in common_errors):
                self.db.removeBot(bot_id)
                log.debug(f"Data bot {bot_id} dihapus karena token tidak valid/terblokir.")

    async def start_all_bots(self):
        all_bots_data = self.db.getBots(is_token=True)
        tasks = [self.start_bot(bot_data) for bot_data in all_bots_data]
        await asyncio.gather(*tasks)

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

    async def expiration_checker(self):
        while True:
            await asyncio.sleep(60 * 60)
            log.info(f"Menjalankan pemeriksaan masa aktif bot...")

            all_bot_ids = [bot["name"] for bot in self.db.getBots(is_token=True)]

            for bot_id_str in all_bot_ids:
                bot_id = int(bot_id_str)
                try:
                    expiry_date_str = self.db.getVars(bot_id, "bot_expiration_date")
                    if not expiry_date_str:
                        continue

                    expiry_date = datetime.fromisoformat(expiry_date_str)
                    time_remaining = expiry_date - datetime.now(timezone.utc)
                    days_left = time_remaining.days

                    owner_id = self.db.getVars(bot_id, "owner_id")
                    if not owner_id:
                        continue

                    main_client = self.main_bot_client
                    if not main_client:
                        continue

                    if days_left < 1:
                        log.debug(f"Masa aktif bot {bot_id} telah habis. Menghapus bot...")
                        try:
                            bot_instance = self.running_bots.get(bot_id)
                            bot_name = (
                                bot_instance.me.first_name
                                if bot_instance and bot_instance.is_connected
                                else f"ID {bot_id}"
                            )
                            expired_message = f"Masa aktif bot Anda **{bot_name}** sudah habis."
                            await main_client.send_message(owner_id, expired_message)
                        except Exception as e:
                            log.print(f"{log.RED}Gagal mengirim notifikasi kedaluwarsa ke owner {owner_id}: {e}")

                        await self.stop_bot(bot_id)
                        self.db.removeBot(bot_id)
                        self.db.removeAllVars(bot_id)
                        log.warning(f"Bot {bot_id} telah dihapus karena kedaluwarsa.")
                        continue

                    target_warning_days = [10, 5, 3, 1]
                    if days_left in target_warning_days:
                        last_notif_date_key = "last_warning_notification_date"
                        last_notif_date_str = self.db.getVars(bot_id, last_notif_date_key)
                        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                        if last_notif_date_str != today_str:
                            try:
                                owner_user = await main_client.get_users(owner_id)
                                mention_owner = main_client.ns.telegram.arg.getMention(owner_user)

                                bot_instance = self.running_bots.get(bot_id)
                                bot_name = (
                                    bot_instance.me.first_name
                                    if bot_instance and bot_instance.is_connected
                                    else f"ID {bot_id}"
                                )

                                warning_message = (
                                    f"🔔 **Notifikasi Masa Aktif** 🔔\n\n"
                                    f"Halo {mention_owner},\n"
                                    f"Masa aktif bot Anda (**{bot_name}**) tinggal **{days_left} hari** lagi.\n\n"
                                    "Silakan hubungi @NorSodikin jika mau diperpanjang."
                                )

                                await main_client.send_message(owner_id, warning_message)
                                self.db.setVars(bot_id, last_notif_date_key, today_str)
                                log.print(
                                    f"{log.CYAN}Mengirim notifikasi sisa {days_left} hari ke owner {owner_id} untuk bot {bot_id}"
                                )
                            except Exception as e:
                                log.print(f"{log.RED}Gagal mengirim notifikasi perpanjangan ke owner {owner_id}: {e}")

                    elif days_left > 10:
                        last_notif_date_key = "last_warning_notification_date"
                        if self.db.getVars(bot_id, last_notif_date_key):
                            self.db.removeVars(bot_id, last_notif_date_key)
                            log.info(f"Mereset flag tanggal notifikasi untuk bot {bot_id}.")

                except Exception as e:
                    log.error(f"Error saat memeriksa masa aktif bot {bot_id}: {e}")

    async def subscription_checker(self):
        while True:
            await asyncio.sleep(60 * 60 * 12)
            log.info(f"Menjalankan pemeriksaan langganan anggota...")
            
            now = datetime.now(timezone.utc)
            all_bot_ids = [int(bot["name"]) for bot in self.db.getBots(is_token=True)]

            for bot_id in all_bot_ids:
                bot_client = self.running_bots.get(bot_id)
                if not bot_client or not bot_client.is_connected:
                    continue

                members = self.db.getListVars(bot_id, "vvip_members") or []
                members_to_keep = []
                
                for member in members:
                    expiry_date_str = member.get("expiry_date")
                    if not expiry_date_str:
                        members_to_keep.append(member)
                        continue
                    
                    expiry_date = datetime.fromisoformat(expiry_date_str)
                    user_id = member["user_id"]
                    lang = Language(self.db, user_id)
                    
                    if now > expiry_date:
                        try:
                            chat_id = member["chat_id_kick"]
                            await bot_client.ban_chat_member(chat_id, user_id)
                            await asyncio.sleep(1)
                            await bot_client.unban_chat_member(chat_id, user_id)
                            await bot_client.send_message(user_id, lang.get("subscription.expired_kick_notif", name=member["vvip_name"]))
                            log.debug(f"Langganan {user_id} di bot {bot_id} habis. Dikeluarkan dari grup.")
                        except Exception as e:
                            log.error(f"Gagal kick member {user_id} dari grup: {e}")
                        continue

                    time_left = expiry_date - now
                    if timedelta(days=2) < time_left <= timedelta(days=3):
                        last_notif_key = "last_renewal_notification_date"
                        last_notif_date_str = self.db.getVars(user_id, f"{last_notif_key}_{bot_id}")
                        today_str = now.strftime("%Y-%m-%d")

                        if last_notif_date_str != today_str:
                            try:
                                btn, txt = bot_client.ns.telegram.button.create_inline_keyboard(f"{lang.get('subscription.renewal_reminder', name=member['vvip_name'], days=time_left.days)}\n\n| {lang.get('subscription.renew_button')} - renew_sub {member['vvip_name']} |")
                                await bot_client.send_message(user_id, txt, reply_markup=btn)
                                self.db.setVars(user_id, f"{last_notif_key}_{bot_id}", today_str)
                            except Exception as e:
                                log.print(f"{log.RED}Gagal kirim notif perpanjangan ke {user_id}: {e}")

                    members_to_keep.append(member)
                
                if len(members_to_keep) != len(members):
                    self.db.removeVars(bot_id, "vvip_members")
                    if members_to_keep:
                        for m in members_to_keep:
                            self.db.setListVars(bot_id, "vvip_members", m)
