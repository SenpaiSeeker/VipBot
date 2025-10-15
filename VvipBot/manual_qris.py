from . import *
from datetime import datetime, timedelta, timezone
import uuid
from .payment import verify_user_join

@command(lambda ctx: filters.regex(r"^pay_manual\s(.+)"), handler_type="callback")
async def pay_manual(client, callback_query):
    parts = callback_query.data.split()
    name_parts = []
    tipe = None
    amount = None
    i = 1
    while i < len(parts):
        if parts[i] in ["normal", "promo"]:
            tipe = parts[i]
            amount = int(parts[i+1])
            break
        name_parts.append(parts[i])
        i += 1
    name = " ".join(name_parts)
    lang = callback_query.lang
    chat_id = callback_query.from_user.id
    qris_photo_id = ctx.db.getVars(client.me.id, "qris_photo_id")
    qris_text = ctx.db.getVars(client.me.id, "qris_text") or lang.get("payment.manual.default_instructions")
    txt = lang.get("payment.manual.instructions_header", name=name, amount=amount) + "\n\n" + qris_text
    if qris_photo_id:
        try:
            btn_text = f"| {lang.get('payment.manual.upload_proof_button')} - upload_proof {name} {tipe} {amount} |"
            btn, _ = client.ns.telegram.button.create_inline_keyboard(btn_text)
            await client.send_photo(chat_id, qris_photo_id, caption=txt, reply_markup=btn)
        except Exception:
            await client.send_message(chat_id, txt)
    else:
        await client.send_message(chat_id, txt)
    try:
        ask_prompt = lang.get("payment.manual.ask_upload")
        ask_msg = await client.ask(chat_id, f"{ask_prompt}{lang.get('prompts.cancel_footer')}", timeout=1800)
        if ask_msg.text and ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled
        if not ask_msg.photo:
            await client.send_message(chat_id, lang.get("payment.manual.must_send_photo"))
            return
        file_id = ask_msg.photo.sizes[-1].file_id
        proof_id = str(uuid.uuid4())
        proof_data = {
            "id": proof_id,
            "user_id": chat_id,
            "photo_file_id": file_id,
            "name": name,
            "type": tipe,
            "amount": amount,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        ctx.db.setListVars(client.me.id, "payment_proofs", proof_data)
        owner_bot_id = ctx.db.getVars(client.me.id, "owner_id") or ctx.owner_id
        owner_lang = Language(ctx.db, owner_bot_id)
        user_obj = await client.get_users(chat_id)
        user_mention = client.ns.telegram.arg.getMention(user_obj)
        txt_owner = owner_lang.get(
            "payment.manual.owner_notif",
            mention=user_mention,
            name=name,
            type=tipe.title(),
            amount=amount,
            id=proof_id
        )
        btn_text = f"| {owner_lang.get('payment.manual.approve')} - approve_proof {proof_id} | | {owner_lang.get('payment.manual.reject')} - reject_proof {proof_id} |"
        btn_owner, _ = client.ns.telegram.button.create_inline_keyboard(f"{txt_owner}\n\n{btn_text}")
        await client.send_message(owner_bot_id, txt_owner, reply_markup=btn_owner)
        await client.send_message(chat_id, lang.get("payment.manual.uploaded_thanks"))
    except listen.UserCancelled:
        await client.send_message(chat_id, callback_query.lang.get("general.cancelled"))
    except asyncio.TimeoutError:
        await client.send_message(chat_id, callback_query.lang.get("general.timeout"))

@command(lambda ctx: filters.regex(r"^upload_proof\s(.+)\s(normal|promo)\s(\d+)"), handler_type="callback")
async def upload_proof_button(client, callback_query):
    await pay_manual(client, callback_query)

@command(lambda ctx: filters.regex(r"^approve_proof\s(.+)"), handler_type="callback")
async def approve_proof_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(callback_query.lang.get("general.no_access"), show_alert=True)
    proof_id = callback_query.data.split()[1]
    proofs = ctx.db.getListVars(client.me.id, "payment_proofs") or []
    target = None
    for p in proofs:
        if p.get("id") == proof_id:
            target = p
            p["status"] = "approved"
            p["approved_by"] = callback_query.from_user.id
            p["approved_at"] = datetime.now(timezone.utc).isoformat()
            break
    ctx.db.removeVars(client.me.id, "payment_proofs")
    for p in proofs:
        ctx.db.setListVars(client.me.id, "payment_proofs", p)
    if not target:
        return await callback_query.answer(callback_query.lang.get("payment.manual.proof_not_found"), show_alert=True)
    name = target.get("name")
    tipe = target.get("type")
    user_id = target.get("user_id")
    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
    item_found = next((item for item in vvip_list if item.get("name") == name), None)
    if not item_found:
        await callback_query.answer(callback_query.lang.get("payment.manual.vvip_missing"), show_alert=True)
        return
    is_promo = tipe == "promo"
    target_chat_id = item_found.get("chat_id_promo") if is_promo else item_found.get("chat_id_normal")
    if not target_chat_id:
        await callback_query.answer(callback_query.lang.get("payment.manual.chat_missing"), show_alert=True)
        return
    try:
        expire_date_link = datetime.now(timezone.utc) + timedelta(hours=2)
        invite_link_obj = await client.create_chat_invite_link(chat_id=target_chat_id, member_limit=1, expire_date=expire_date_link)
        link = invite_link_obj.invite_link
    except Exception as e:
        return await callback_query.answer(callback_query.lang.get("payment.manual.invite_fail", e=e), show_alert=True)
    duration = item_found.get("duration", 0)
    member_data = {
        "user_id": user_id,
        "vvip_name": name,
        "join_date": datetime.now(timezone.utc).isoformat(),
        "payment_type": tipe,
        "chat_id_kick": target_chat_id
    }
    if duration and duration > 0:
        expiry_date = datetime.now(timezone.utc) + timedelta(days=duration)
        member_data["expiry_date"] = expiry_date.isoformat()
    ctx.db.setListVars(client.me.id, "vvip_members", member_data)
    try:
        link_msg = await client.send_message(user_id, callback_query.lang.get("payment.manual.success_customer", name=name, link=link), protect_content=True)
        asyncio.create_task(verify_user_join(client, await client.get_users(user_id), target_chat_id, link_msg))
    except Exception:
        pass
    await callback_query.edit_message_text(callback_query.lang.get("payment.manual.approved_owner", id=proof_id))

@command(lambda ctx: filters.regex(r"^reject_proof\s(.+)"), handler_type="callback")
async def reject_proof_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(callback_query.lang.get("general.no_access"), show_alert=True)
    proof_id = callback_query.data.split()[1]
    proofs = ctx.db.getListVars(client.me.id, "payment_proofs") or []
    target = None
    for p in proofs:
        if p.get("id") == proof_id:
            p["status"] = "rejected"
            p["rejected_by"] = callback_query.from_user.id
            p["rejected_at"] = datetime.now(timezone.utc).isoformat()
            target = p
            break
    ctx.db.removeVars(client.me.id, "payment_proofs")
    for p in proofs:
        ctx.db.setListVars(client.me.id, "payment_proofs", p)
    if target:
        try:
            await client.send_message(target.get("user_id"), callback_query.lang.get("payment.manual.rejected_customer", name=target.get("name")))
        except Exception:
            pass
    await callback_query.edit_message_text(callback_query.lang.get("payment.manual.rejected_owner", id=proof_id))

@command(lambda ctx: filters.regex(r"^join_vvip\s(.+)"), handler_type="callback")
async def join_vvip_callback(client, callback_query):
    parts = callback_query.data.split()
    name = " ".join(parts[1:])
    user = callback_query.from_user
    vvip_members = ctx.db.getListVars(client.me.id, "vvip_members") or []
    now = datetime.now(timezone.utc)
    member = next((m for m in vvip_members if m.get("user_id") == user.id and m.get("vvip_name") == name), None)
    lang = callback_query.lang
    if not member:
        await callback_query.answer(lang.get("payment.join.not_member"), show_alert=True)
        return
    expiry = member.get("expiry_date")
    if expiry:
        expiry_dt = datetime.fromisoformat(expiry)
        if expiry_dt < now:
            await callback_query.answer(lang.get("payment.join.expired"), show_alert=True)
            return
    vvip_list = ctx.db.getListVars(client.me.id, "list_vvip") or []
    item_found = next((item for item in vvip_list if item.get("name") == name), None)
    if not item_found:
        await callback_query.answer(lang.get("payment.join.vvip_missing"), show_alert=True)
        return
    target_chat_id = item_found.get("chat_id_normal") or item_found.get("chat_id_promo")
    if not target_chat_id:
        await callback_query.answer(lang.get("payment.join.chat_missing"), show_alert=True)
        return
    try:
        expire_date_link = datetime.now(timezone.utc) + timedelta(hours=2)
        invite_link_obj = await client.create_chat_invite_link(chat_id=target_chat_id, member_limit=1, expire_date=expire_date_link)
        link = invite_link_obj.invite_link
        await client.send_message(user.id, lang.get("payment.join.link_sent", name=name, link=link), protect_content=True)
    except Exception as e:
        await callback_query.answer(lang.get("payment.join.invite_fail", e=e), show_alert=True)
