from datetime import datetime, timezone

from pyrogram import filters

from . import command, ctx


@command(lambda ctx: filters.all, handler_type="chat_join_request")
async def auto_approve_join_request(client, join_request):
    user = join_request.from_user
    chat = join_request.chat

    members_list = await ctx.db.getListVars(client.me.id, "vvip_members") or []
    is_authorized = False

    for member in members_list:
        if member.get("user_id") == user.id and member.get("chat_id_kick") == chat.id:
            expiry_date_str = member.get("expiry_date")
            if not expiry_date_str:
                is_authorized = True
                break

            expiry_date = datetime.fromisoformat(expiry_date_str)
            if datetime.now(timezone.utc) < expiry_date:
                is_authorized = True
                break

    try:
        if is_authorized:
            await client.approve_chat_join_request(chat.id, user.id)
            ctx.log.print(f"{ctx.log.GREEN}User {user.id} disetujui otomatis masuk ke grup {chat.id}")
        else:
            await client.decline_chat_join_request(chat.id, user.id)
            ctx.log.print(f"{ctx.log.RED}User {user.id} ditolak masuk ke grup {chat.id}")
    except Exception as e:
        ctx.log.print(f"{ctx.log.YELLOW}User {user.id} gagal memproses auto-approve join request: {e}")
