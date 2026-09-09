from types import SimpleNamespace

from pyrogram import Client

from .argument import Argument
from .button import Button
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
        )
        self.server = SimpleNamespace(monitor=ServerMonitor())
        self.payment = SimpleNamespace(SaweriaScraper=SaweriaScraper)
        self.emoji = EmojiParse()


def get_ns(self):
    if not hasattr(self, "_clean_ns_instance"):
        self._clean_ns_instance = CleanNamespace(self)
    return self._clean_ns_instance


Client.ns = property(get_ns)
