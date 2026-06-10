from types import SimpleNamespace

from helpers.logger import LoggerHandler

log = LoggerHandler()


async def initialize_bot_services(client, db_instance):
    bot_id = getattr(client, "uid", None)

    if not bot_id:
        try:
            me = await client.get_me()
            bot_id = me.id
            client.uid = me.id
            client.me = me
        except Exception:
            return

    client.services = SimpleNamespace(saweria=None)
    saweria_user_id = await db_instance.getVars(bot_id, "SAWERIA_USER_ID")

    if saweria_user_id:
        try:
            client.services.saweria = client.ns.payment.SaweriaScraper()
        except Exception as e:
            log.print(
                f"{log.RED}Gagal inisialisasi SaweriaScraper untuk Bot ID {bot_id}: {e}"
            )
