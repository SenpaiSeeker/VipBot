from types import SimpleNamespace

from nsdev import LoggerHandler

log = LoggerHandler()


def initialize_bot_services(client, db_instance):
    bot_id = client.me.id
    client.services = SimpleNamespace(saweria=None, gemini=None)

    saweria_api_key = db_instance.getVars(bot_id, "SAWERIA_API_KEY")
    if saweria_api_key:
        try:
            client.services.saweria = client.ns.payment.Saweria(
                api_key=saweria_api_key,
            )
        except Exception as e:
            log.print(f"{log.RED}Gagal inisialisasi Saweria untuk Bot ID {bot_id}: {e}")

    gemini_api_key = db_instance.getVars(bot_id, "GEMINI_API_KEY")
    if gemini_api_key:
        try:
            client.services.gemini = client.ns.ai.gemini(api_key=gemini_api_key)
        except Exception as e:
            log.print(f"{log.RED}Gagal inisialisasi Gemini untuk Bot ID {bot_id}: {e}")
