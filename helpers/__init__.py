from datetime import datetime, timezone
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
from .table import TableBuilder
from .table import TableBuilder


def parse_dt(value) -> "datetime | None":
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
        self.table = TableBuilder()
        self.rich = SimpleNamespace(photo=self.table.rich_photo)


def get_ns(self):
    if not hasattr(self, "_clean_ns_instance"):
        self._clean_ns_instance = CleanNamespace(self)
    return self._clean_ns_instance


Client.ns = property(get_ns)
