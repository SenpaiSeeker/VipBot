from telethon import utils
from telethon.extensions.html import unparse as html_unparse


class Argument:
    def __init__(self, client):
        self.client = client

    def getMention(
        self,
        user,
        logs=False,
        no_tag=False,
        tag_and_id=False,
    ) -> str:
        name = utils.get_display_name(user)

        if logs:
            return f"{name} ({user.id})"

        if no_tag:
            return name

        mention = f'<a href="tg://user?id={user.id}">{name}</a>'

        if tag_and_id:
            mention += f" (<code>{user.id}</code>)"

        return mention

    async def getNamebot(self, bot_token: str):
        from telethon import TelegramClient
        from telethon.sessions import MemorySession

        temp_bot_client = TelegramClient(
            MemorySession(),
            api_id=self.client.api_id,
            api_hash=self.client.api_hash,
        )

        try:
            await temp_bot_client.start(bot_token=bot_token)
            me = await temp_bot_client.get_me()
            await temp_bot_client.disconnect()
            return me
        except Exception:
            return "invalid"

    async def getMessage(
        self,
        message,
        is_arg=False,
        is_tuple=False,
        raw=False,
    ):
        msg = (
            message.message
            if hasattr(message, "message") and not isinstance(message.message, str)
            else message
        )
        full_text = msg.message or ""
        full_html = (
            full_text
            if raw
            else (
                html_unparse(msg.message, msg.entities) if msg.entities else full_text
            )
        )
        command_parts = full_text.split()

        replied = await message.get_reply_message() if message.is_reply else None
        replied_text = replied.message if replied else None

        if is_tuple:
            part1 = command_parts[1] if len(command_parts) > 1 else None
            part2 = None

            if len(command_parts) > 2:
                part2 = " ".join(command_parts[2:]).strip()
                if part2 == "":
                    part2 = None
            else:
                if replied_text:
                    part2 = (
                        html_unparse(replied.message, replied.entities)
                        if replied.entities
                        else replied.message
                    )

            return part1, part2

        if is_arg:
            if len(command_parts) > 1:
                command_str = command_parts[0]
                args_html = full_html[len(command_str) :].strip()
                return args_html

            if replied and replied_text:
                return (
                    html_unparse(replied.message, replied.entities)
                    if replied.entities
                    else replied.message
                )

            return ""

        if replied:
            return replied

        if len(command_parts) > 1:
            command_str = command_parts[0]
            args_html = full_html[len(command_str) :].strip()
            return args_html

        return ""

    async def getReasonAndId(
        self,
        message,
        sender_chat=False,
    ):
        msg = (
            message.message
            if hasattr(message, "message") and not isinstance(message.message, str)
            else message
        )
        full_text = msg.message or ""
        args = full_text.strip().split()

        replied = await message.get_reply_message() if message.is_reply else None
        target_id = None
        reason = None

        if replied:
            target_id = replied.sender_id
            if len(args) > 1:
                reason = " ".join(args[1:])
        elif len(args) > 1:
            try:
                target_user = await self.client.get_entity(args[1])
                target_id = target_user.id
                if len(args) > 2:
                    reason = " ".join(args[2:])
            except Exception:
                return None, None

        return target_id, reason
