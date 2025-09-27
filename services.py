from types import SimpleNamespace

from nsdev import LoggerHandler

log = LoggerHandler()


def initialize_bot_services(client, db_instance):
    bot_id = client.me.id
    client.services = SimpleNamespace(vmp=None, gemini=None)

    violet_api_key = db_instance.getVars(bot_id, "VIOLET_API_KEY")
    violet_secret_key = db_instance.getVars(bot_id, "VIOLET_SECRET_KEY")
    if violet_api_key and violet_secret_key:
        try:
            client.services.vmp = client.ns.payment.Violet(
                api_key=violet_api_key,
                secret_key=violet_secret_key,
                live=True,
            )
        except Exception as e:
            log.print(f"{log.RED}Gagal inisialisasi Violet untuk Bot ID {bot_id}: {e}")

    gemini_api_key = db_instance.getVars(bot_id, "GEMINI_API_KEY")
    if gemini_api_key:
        try:
            client.services.gemini = client.ns.ai.gemini(api_key=gemini_api_key)
        except Exception as e:
            log.print(f"{log.RED}Gagal inisialisasi Gemini untuk Bot ID {bot_id}: {e}")
