from types import SimpleNamespace

from pyrogram import Client

from .argument import Argument
from .button import Button
from .faker_gen import FakeInfoGenerator
from .gemini import ChatbotGemini
from .gradient import Gradient
from .logger import LoggerHandler
from .monitor import ServerMonitor
from .saweria_scraper import SaweriaScraper


class MockUtils:
    def __init__(self):
        self.log = LoggerHandler()
        self.faker = FakeInfoGenerator()
        self.grad = Gradient()


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


class MockAI:
    def __init__(self):
        self.gemini = ChatbotGemini


class MockNS:
    def __init__(self, client):
        self.telegram = MockTelegram(client)
        self.utils = MockUtils()
        self.server = MockServer()
        self.payment = MockPayment()
        self.ai = MockAI()


Client.ns = property(lambda self: MockNS(self))
