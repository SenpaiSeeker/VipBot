import io
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
            update_str = str(update)
            
            if len(update_str) > 4000:
                file = io.BytesIO(update_str.encode("utf-8"))
                file.name = "update.txt"
                await client.send_document(user_id, document=file)
                text_to_send = "Pesan melebihi batas, dikirim ke PM sebagai dokumen .txt"
            else:
                text_to_send = update_str

            result = InputBotInlineResult(
                id="0",
                type="article",
                title="Send",
                send_message=InputBotInlineMessageText(
                    message=text_to_send
                )
            )
            
            await client.invoke(SetBotGuestChatResult(
                query_id=update.query_id,
                result=result
            ))

def setup_guest_chat_query(client: Client, owner_id: int):
    client.owner_id = owner_id
    client.add_handler(RawUpdateHandler(guest_chat_query_handler), group=1)
