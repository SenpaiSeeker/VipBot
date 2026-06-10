import asyncio

from telethon import TelegramClient


class UserCancelled(Exception):
    pass


async def listen(self, chat_id, timeout=None):
    async with self.conversation(chat_id, timeout=timeout) as conv:
        return await conv.get_response()


async def ask(self, chat_id, text, timeout=None, **kwargs):
    async with self.conversation(chat_id, timeout=timeout) as conv:
        await conv.send_message(text, **kwargs)
        try:
            response = await conv.get_response()
            if response.text and response.text.strip().lower() == "/batal":
                raise UserCancelled()
            return response
        except asyncio.TimeoutError:
            raise


TelegramClient.listen = listen
TelegramClient.ask = ask
