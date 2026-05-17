from pyrogram import Client
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw.types import (
    UpdateBotGuestChatQuery, 
    PeerUser, 
    InputBotInlineResult, 
    InputBotInlineMessageText
)
from pyrogram.raw.functions.messages import SetBotGuestChatResult

async def guest_chat_query_handler(client: Client, update, users, chats):
    if isinstance(update, UpdateBotGuestChatQuery):
        msg = update.message
        user_id = None
        
        if hasattr(msg, "from_id") and isinstance(msg.from_id, PeerUser):
            user_id = msg.from_id.user_id
        elif hasattr(msg, "peer_id") and isinstance(msg.peer_id, PeerUser):
            user_id = msg.peer_id.user_id
            
        if user_id == getattr(client, "owner_id", None):
            user = await client.get_users(user_id)
            mention = client.ns.telegram.arg.getMention(user)
            parsed_text, parsed_entities = await client.parser.parse(f"halo {mention}", "html")
            
            result = InputBotInlineResult(
                id="0",
                type="article",
                title="Send",
                send_message=InputBotInlineMessageText(
                    message=parsed_text,
                    entities=parsed_entities
                )
            )
            
            await client.invoke(SetBotGuestChatResult(
                query_id=update.query_id,
                result=result
            ))

def setup_guest_chat_query(client: Client, owner_id: int):
    client.owner_id = owner_id
    client.add_handler(RawUpdateHandler(guest_chat_query_handler), group=1)
