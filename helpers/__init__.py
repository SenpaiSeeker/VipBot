from types import SimpleNamespace

from pyrogram import Client

from .argument import Argument
from .button import Button
from .dashboard_gen import DashboardGenerator
from .faker_gen import FakeInfoGenerator
from .gradient import Gradient
from .logger import LoggerHandler
from .monitor import ServerMonitor
from .saweria_scraper import SaweriaScraper


class MockUtils:
    def __init__(self):
        self.log = LoggerHandler
        self.faker = FakeInfoGenerator()
        self.grad = Gradient()
        self.dashboard = DashboardGenerator()


class MockTelegram:
    def __init__(self, client):
        self.arg = Argument(client)
        self.button = Button()


class MockServer:
    def __init__(self):
        self.monitor = ServerMonitor()


class MockPayment:
    def __init__(self):
        self.SaweriaScraper = SaweriaScraper


class MockNS:
    def __init__(self, client):
        self.telegram = MockTelegram(client)
        self.utils = MockUtils()
        self.server = MockServer()
        self.payment = MockPayment()


def get_ns(self):
    if not hasattr(self, "_mock_ns_instance"):
        self._mock_ns_instance = MockNS(self)
    return self._mock_ns_instance


Client.ns = property(get_ns)
