from pyrogram import Client
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw.types import UpdateBotGuestChatQuery, PeerUser

async def guest_chat_query_handler(client: Client, update, users, chats):
    if isinstance(update, UpdateBotGuestChatQuery):
        msg = update.message
        user_id = None
        
        if hasattr(msg, "from_id") and isinstance(msg.from_id, PeerUser):
            user_id = msg.from_id.user_id
        elif hasattr(msg, "peer_id") and isinstance(msg.peer_id, PeerUser):
            user_id = msg.peer_id.user_id
            
        if user_id == getattr(client, "owner_id", None):
            query_id = update.query_id
            qts = update.qts
            reference_messages = update.reference_messages

def setup_guest_chat_query(client: Client, owner_id: int):
    client.owner_id = owner_id
    client.add_handler(RawUpdateHandler(guest_chat_query_handler), group=1)
