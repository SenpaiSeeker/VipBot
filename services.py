from types import SimpleNamespace

from helpers.logger import LoggerHandler

log = LoggerHandler()


async def initialize_bot_services(client, db_instance):
    bot_id = client.me.id
    client.services = SimpleNamespace(saweria=None)

    saweria_user_id = await db_instance.getVars(bot_id, "SAWERIA_USER_ID")
    if saweria_user_id:
        try:
            client.services.saweria = client.ns.payment.SaweriaScraper()
        except Exception as e:
            log.print(
                f"{log.RED}Gagal inisialisasi SaweriaScraper untuk Bot ID {bot_id}: {e}"
            )
