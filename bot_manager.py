import asyncio
from datetime import datetime, timedelta, timezone

import pyrogram

import VvipBot as handlers
from database import schedule
from helpers.logger import LoggerHandler
from services import initialize_bot_services
from VvipBot import ctx

log = LoggerHandler()

INVALID_TOKEN_ERRORS = (
    "USER_DEACTIVATED_BAN",
    "BOT_TOKEN_INVALID",
    "ACCESS_TOKEN_EXPIRED",
)

WARNING_DAYS = (10, 5, 3, 1)


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
            await initialize_bot_services(client, self.db)
            self.running_bots[client.me.id] = client
            log.info(
                f"Bot {client.me.first_name} (ID: {client.me.id}) berhasil diaktifkan."
            )
        except Exception as e:
            log.print(f"{log.RED}Gagal memulai bot {bot_id}: {e}")
            if any(err in str(e).upper() for err in INVALID_TOKEN_ERRORS):
                await self.db.removeBot(bot_id)
                log.debug(
                    f"Data bot {bot_id} dihapus karena token tidak valid/terblokir."
                )

    async def start_all_bots(self):
        all_bots_data = await self.db.getBots(is_token=True)
        await asyncio.gather(*(self.start_bot(bot_data) for bot_data in all_bots_data))

    async def stop_bot(self, bot_id):
        client = self.running_bots.pop(bot_id, None)
        if client is None:
            return
        try:
            if client.is_connected:
                await client.stop()
            log.debug(f"Bot {bot_id} berhasil dihentikan.")
        except Exception as e:
            log.error(f"Error saat menghentikan bot {bot_id}: {e}")

    def bot_display_name(self, bot_id):
        bot_instance = self.running_bots.get(bot_id)
        if bot_instance is not None and bot_instance.is_connected:
            return bot_instance.me.first_name
        return f"ID {bot_id}"

    async def relay_message(self, receiver_id, text, fallback_client=None, reply_markup=None):
        try:
            await self.main_bot_client.send_message(
                receiver_id, text, reply_markup=reply_markup
            )
        except Exception:
            await fallback_client.send_message(
                receiver_id, text, reply_markup=reply_markup
            )


async def purge_expired_bot(manager, bot_id, owner_id):
    log.debug(f"Masa aktif bot {bot_id} telah habis. Menghapus bot...")
    bot_name = manager.bot_display_name(bot_id)
    expired_message = f"Masa aktif bot Anda **{bot_name}** sudah habis."
    await manager.relay_message(
        owner_id, expired_message, fallback_client=manager.running_bots.get(bot_id)
    )
    await manager.stop_bot(bot_id)
    await manager.db.removeBot(bot_id)
    log.warning(f"Bot {bot_id} telah dihapus karena kedaluwarsa.")


async def send_expiry_warning(manager, bot_id, owner_id, days_left):
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    notif_key = "last_warning_notification_date"
    if await manager.db.getVars(bot_id, notif_key) == today_str:
        return
    try:
        owner_user = await manager.main_bot_client.get_users(owner_id)
        mention_owner = manager.main_bot_client.ns.telegram.arg.getMention(owner_user)
        bot_name = manager.bot_display_name(bot_id)
        warning_message = (
            f"{manager.main_bot_client.ns.emoji.bell} **Notifikasi Masa Aktif** "
            f"{manager.main_bot_client.ns.emoji.bell}\n\n"
            f"Halo {mention_owner},\n"
            f"Masa aktif bot Anda (**{bot_name}**) tinggal **{days_left} hari** lagi.\n\n"
            "Silakan hubungi @NorSodikin jika mau diperpanjang."
        )
        await manager.relay_message(
            owner_id, warning_message, fallback_client=manager.running_bots.get(bot_id)
        )
        await manager.db.setVars(bot_id, notif_key, today_str)
        log.print(
            f"{log.CYAN}Mengirim notifikasi sisa {days_left} hari ke owner {owner_id} "
            f"untuk bot {bot_id}"
        )
    except Exception as e:
        log.print(
            f"{log.RED}Gagal mengirim notifikasi perpanjangan ke owner {owner_id}: {e}"
        )


@schedule.cron("0 * * * *")
async def expiration_checker_method():
    log.info("Menjalankan pemeriksaan masa aktif bot...")
    manager = ctx.manager
    if not manager:
        log.warning("BotManager belum diinisialisasi di ctx. Melewati pemeriksaan.")
        return
    all_bot_ids = [bot["name"] for bot in await manager.db.getBots(is_token=True)]
    for bot_id_str in all_bot_ids:
        bot_id = int(bot_id_str)
        try:
            expiry_str = await manager.db.getVars(bot_id, "bot_expiration_date")
            if not expiry_str:
                continue
            expiry_date = datetime.fromisoformat(expiry_str)
            days_left = (expiry_date - datetime.now(timezone.utc)).days
            owner_id = await manager.db.getVars(bot_id, "owner_id")
            if not owner_id or not manager.main_bot_client:
                continue
            if days_left < 1:
                await purge_expired_bot(manager, bot_id, owner_id)
            elif days_left in WARNING_DAYS:
                await send_expiry_warning(manager, bot_id, owner_id, days_left)
            elif days_left > 10:
                notif_key = "last_warning_notification_date"
                if await manager.db.getVars(bot_id, notif_key):
                    await manager.db.removeVars(bot_id, notif_key)
                    log.info(f"Mereset flag tanggal notifikasi untuk bot {bot_id}.")
        except Exception as e:
            log.error(f"Error saat memeriksa masa aktif bot {bot_id}: {e}")


async def send_renewal_reminder(manager, bot_client, bot_id, vvip_list, member, time_left, now):
    user_id = member["user_id"]
    vvip_name_val = member["vvip_name"]
    notif_key = f"last_renewal_notification_date_{bot_id}"
    today_str = now.strftime("%Y-%m-%d")
    if await manager.db.getVars(user_id, notif_key) == today_str:
        return
    try:
        item_index = next(
            (
                i
                for i, vvip_item in enumerate(vvip_list)
                if vvip_item.get("name") == vvip_name_val
            ),
            -1,
        )
        if item_index == -1:
            return
        text = (
            f"{bot_client.ns.emoji.bell} **Pengingat Langganan**\n\n"
            f"Langganan Anda untuk paket **{vvip_name_val}** akan berakhir dalam "
            f"**{time_left.days} hari** lagi. Perpanjang sekarang agar tidak "
            f"kehilangan akses!"
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
        btn = bot_client.ns.telegram.button.build_button_grid(layout)
        await bot_client.send_message(user_id, text, reply_markup=btn)
        await manager.db.setVars(user_id, notif_key, today_str)
    except Exception as e:
        log.print(f"{ctx.log.RED}Gagal kirim notif perpanjangan ke {user_id}: {e}")


@schedule.cron("0 */12 * * *")
async def subscription_checker_method():
    log.info("Menjalankan pemeriksaan langganan anggota...")
    manager = ctx.manager
    if not manager:
        log.warning("BotManager belum diinisialisasi di ctx. Melewati pemeriksaan.")
        return
    now = datetime.now(timezone.utc)
    all_bot_ids_data = await manager.db.getBots(is_token=True)
    all_bot_ids = [int(bot["name"]) for bot in all_bot_ids_data]

    for bot_id in all_bot_ids:
        bot_client = manager.running_bots.get(bot_id)
        if bot_client is None or not bot_client.is_connected:
            continue
        members = await manager.db.getListVars(bot_id, "vvip_members") or []
        vvip_list = await manager.db.getListVars(bot_id, "list_vvip") or []
        members_to_keep = []

        for member in members:
            expiry_str = member.get("expiry_date")
            if not expiry_str:
                members_to_keep.append(member)
                continue
            expiry_date = datetime.fromisoformat(expiry_str)
            user_id = member["user_id"]
            if now > expiry_date:
                try:
                    chat_id = member["chat_id_kick"]
                    await bot_client.ban_chat_member(chat_id, user_id)
                    await asyncio.sleep(1)
                    await bot_client.unban_chat_member(chat_id, user_id)
                    vvip_name_val = member["vvip_name"]
                    expired_message_text = (
                        f"{bot_client.ns.emoji.hourglass_done} **Langganan Berakhir**\n\n"
                        f"Langganan Anda untuk paket **{vvip_name_val}** telah "
                        f"berakhir. Anda telah dikeluarkan dari grup."
                    )
                    await bot_client.send_message(user_id, expired_message_text)
                    log.debug(
                        f"Langganan {user_id} di bot {bot_id} habis. "
                        f"Dikeluarkan dari grup."
                    )
                except Exception as e:
                    log.error(f"Gagal kick member {user_id} dari grup: {e}")
                continue

            time_left = expiry_date - now
            if timedelta(days=2) < time_left <= timedelta(days=3):
                await send_renewal_reminder(
                    manager, bot_client, bot_id, vvip_list, member, time_left, now
                )
            members_to_keep.append(member)

        if len(members_to_keep) != len(members):
            await manager.db.removeVars(bot_id, "vvip_members")
            for m in members_to_keep:
                await manager.db.setListVars(bot_id, "vvip_members", m)