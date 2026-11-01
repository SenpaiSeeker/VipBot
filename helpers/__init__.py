from datetime import datetime, timezone

from .argument import Argument
from .button import Button, Buttons
from .dashboard_gen import DashboardGenerator
from .database import DataBase
from .emoji_parse import Emoji, EmojiParse
from .faker_gen import FakeInfoGenerator
from .gradient import Gradient
from .logger import LoggerHandler
from .modules import Modules
from .monitor import ServerMonitor
from .patcher import DataObject, NamespaceProxy, Object
from .saweria_scraper import SaweriaScraper
from .table import Table, TableBuilder


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


__all__ = [
    "Argument",
    "Button",
    "Buttons",
    "DashboardGenerator",
    "DataBase",
    "DataObject",
    "Emoji",
    "EmojiParse",
    "FakeInfoGenerator",
    "Gradient",
    "LoggerHandler",
    "Modules",
    "NamespaceProxy",
    "Object",
    "SaweriaScraper",
    "ServerMonitor",
    "Table",
    "TableBuilder",
    "parse_dt",
]
