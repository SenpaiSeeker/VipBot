import aiocron

import bot_manager
from helpers.modules import Modules

JOBS = (
    ("*/5 * * * *", bot_manager.flood_retry_method),
    ("0 * * * *", bot_manager.expiration_checker_method),
    ("0 */12 * * *", bot_manager.subscription_checker_method),
    ("*/15 * * * *", bot_manager.watchdog_token_checker),
)


class Scheduler(Modules):
    _cron_started = False

    def __init__(self, client):
        super().__init__(client)

        if Scheduler._cron_started:
            return

        Scheduler._cron_started = True

        for spec, func in JOBS:
            aiocron.crontab(spec, func=func, loop=client.loop)
