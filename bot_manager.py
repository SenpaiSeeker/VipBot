import asyncio
from datetime import datetime, timezone
import pyrogram
from nsdev import LoggerHandler
from services import initialize_bot_services
import VvipBot as handlers

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
            log.print(f"{log.YELLOW}Bot {bot_id} sudah berjalan.")
            return

        try:
            log.print(f"{log.CYAN}Mencoba memulai bot: {bot_id}")
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
            log.print(
                f"{log.GREEN}Bot {client.me.first_name} (ID: {client.me.id}) berhasil dimulai."
            )
        except Exception as e:
            log.print(f"{log.RED}Gagal memulai bot {bot_id}: {e}")
            if (
                "USER_DEACTIVATED_BAN" in str(e).upper()
                or "BOT_TOKEN_INVALID" in str(e).upper()
            ):
                self.db.removeBot(bot_id)
                log.print(
                    f"{log.ORANGE}Data bot {bot_id} dihapus karena token tidak valid/terblokir."
                )

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
                log.print(f"{log.YELLOW}Bot {bot_id} berhasil dihentikan.")
            except Exception as e:
                log.print(f"{log.RED}Error saat menghentikan bot {bot_id}: {e}")
            finally:
                del self.running_bots[bot_id]

    async def expiration_checker(self):
        while True:
            await asyncio.sleep(3600)
            log.print(f"{log.CYAN}Menjalankan pemeriksaan masa aktif bot...")
            all_bot_ids = [bot["name"] for bot in self.db.getBots(is_token=True)]
            for bot_id_str in all_bot_ids:
                bot_id = int(bot_id_str)
                try:
                    expiry_date_str = self.db.getVars(bot_id, "bot_expiration_date")
                    if not expiry_date_str:
                        continue
                    expiry_date = datetime.fromisoformat(expiry_date_str)
                    if datetime.now(timezone.utc) > expiry_date:
                        log.print(
                            f"{log.ORANGE}Masa aktif bot {bot_id} telah habis. Menghapus bot..."
                        )
                        await self.stop_bot(bot_id)
                        self.db.removeBot(bot_id)
                        self.db.removeAllVars(bot_id)
                        log.print(
                            f"{log.YELLOW}Bot {bot_id} telah dihapus karena kedaluwarsa."
                        )
                except Exception as e:
                    log.print(
                        f"{log.RED}Error saat memeriksa masa aktif bot {bot_id}: {e}"
                    )
