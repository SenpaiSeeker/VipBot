from types import SimpleNamespace

from telethon import TelegramClient

from .argument import Argument
from .button import Button
from .catbox import CatboxUploader
from .dashboard_gen import DashboardGenerator
from .emoji_parse import EmojiParse
from .faker_gen import FakeInfoGenerator
from .gradient import Gradient
from .logger import LoggerHandler
from .monitor import ServerMonitor
from .saweria_scraper import SaweriaScraper


class CleanNamespace:
    def __init__(self, client):
        self.telegram = SimpleNamespace(arg=Argument(client), button=Button())
        self.utils = SimpleNamespace(
            log=LoggerHandler,
            faker=FakeInfoGenerator(),
            grad=Gradient(),
            dashboard=DashboardGenerator(),
            catbox=CatboxUploader(),
        )
        self.server = SimpleNamespace(monitor=ServerMonitor())
        self.payment = SimpleNamespace(SaweriaScraper=SaweriaScraper)
        self.emoji = EmojiParse()

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if not hasattr(instance, "_clean_ns_instance"):
            instance._clean_ns_instance = CleanNamespace(instance)
        return instance._clean_ns_instance


TelegramClient.ns = property(lambda self: CleanNamespace(self))
