from . import *

@command(lambda ctx: filters.command("eval") & filters.user(ctx.owner_id))
async def eval_bot_handler(client, message):
    lang = message.lang

    async def aexec(code, client, message):
        exec(
            "async def __aexec(client, message):\n"
            "    p = print\n"
            "    c = client\n"
            "    m = message\n"
            "    r = message.reply_to_message\n"
            "    " + "\n    ".join(code.split("\n"))
        )
        return await locals()["__aexec"](client, message)

    msg = await message.reply_text(lang.get("admin.eval.processing"))
    cmd = client.ns.arg.getMessage(message, is_arg=True)
    if not cmd:
        return await msg.edit(lang.get("admin.eval.no_code"))

    reply_to_ = message.reply_to_message or message
    old_stdout, old_stderr = sys.stdout, sys.stderr
    redirected_output, redirected_error = StringIO(), StringIO()
    sys.stdout, sys.stderr = redirected_output, redirected_error
    exc = None
    start_time = time()
    try:
        await aexec(cmd, client, message)
    except Exception:
        exc = traceback.format_exc()
    end_time = time()
    sys.stdout, sys.stderr = old_stdout, old_stderr
    stdout, stderr = redirected_output.getvalue(), redirected_error.getvalue()
    evaluation = exc or stderr or stdout or lang.get("admin.eval.success")
    execution_time = (
        f"\n\n**{lang.get('admin.eval.exec_time')}** `{end_time - start_time:.4f}` detik"
    )
    final_output = f"**{lang.get('admin.eval.output')}**\n<pre>{evaluation.strip()}</pre>{execution_time}"
    if len(final_output) > 4096:
        with BytesIO(str.encode(evaluation + execution_time)) as out_file:
            out_file.name = "eval_result.txt"
            await message.reply_document(
                document=out_file, caption=lang.get("admin.eval.too_long")
            )
    else:
        await reply_to_.reply_text(final_output)
    await msg.delete()


@command(lambda ctx: filters.command("restore") & filters.user(ctx.owner_id))
async def restore_database_handler(client, message):
    lang = message.lang
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text(lang.get("admin.restore.usage"))

    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".zip"):
        return await message.reply_text(lang.get("admin.restore.wrong_format"))

    status_msg = await message.reply_text(lang.get("admin.restore.processing"))
    downloaded_zip_path = None
    try:
        downloaded_zip_path = await client.download_media(message.reply_to_message)
        with zipfile.ZipFile(downloaded_zip_path, "r") as zf:
            if not zf.namelist():
                raise ValueError(lang.get("admin.restore.empty_zip"))
            db_filename_in_zip = zf.namelist()[0]
            zf.extractall(path=".")

        db_path = getattr(ctx.db, "data_file", getattr(ctx.db, "db_file", ""))
        if (
            db_path
            and os.path.exists(db_filename_in_zip)
            and db_filename_in_zip != db_path
        ):
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rename(db_filename_in_zip, db_path)

        success_text = f"{lang.get('admin.restore.success', db_path=db_path)}\n\n{lang.get('admin.restore.important')}"
        await status_msg.edit_text(success_text)
        ctx.log.print(f"{ctx.log.GREEN}Database '{db_path}' restored by admin.")
    except Exception as e:
        await status_msg.edit_text(lang.get("admin.restore.fail", e=str(e)))
        ctx.log.print(f"{ctx.log.RED}Restore failed: {e}")
    finally:
        if downloaded_zip_path and os.path.exists(downloaded_zip_path):
            os.remove(downloaded_zip_path)


@command(lambda ctx: filters.command("akses") & filters.user(ctx.owner_id))
async def access_command_handler(client, message):
    lang = message.lang
    user_id_target, _ = await client.ns.arg.getReasonAndId(message)
    if not user_id_target:
        return await message.reply_text(
            f"**{lang.get('general.invalid_format')}**\n{lang.get('admin.access.format_error')}"
        )

    try:
        target_user = await client.get_users(user_id_target)
        access_list = ctx.db.getListVars(ctx.owner_id, "create_bot_access") or []

        status_text = (
            lang.get("admin.access.has_access")
            if target_user.id in access_list
            else lang.get("admin.access.no_access")
        )

        text = (
            f"**{lang.get('admin.access.title')}**\n\n"
            f"**👤 {lang.get('general.user')}:** {client.ns.arg.getMention(target_user)}\n"
            f"**🆔 {lang.get('general.id')}:** `{target_user.id}`\n"
            f"**📊 {lang.get('general.status')}:** `{status_text}`\n\n"
            f"{lang.get('admin.access.prompt')}"
        )

        btn_text = (
            f"| {lang.get('admin.access.give_button')} - give_access {target_user.id} |\n"
            f"| {lang.get('admin.access.revoke_button')} - revoke_access {target_user.id};same |"
        )

        btn, _ = client.ns.button.create_keyboard(f"{text}\n{btn_text}")
        await message.reply_text(text, reply_markup=btn)
    except Exception as e:
        await message.reply_text(lang.get("admin.access.process_fail", e=e))


@command(
    lambda ctx: filters.regex(r"^(give|revoke)_access\s(\d+)"), handler_type="callback"
)
async def manage_access_callback(client, callback_query):
    lang = callback_query.lang
    action, target_id_str = callback_query.data.split(" ", 1)
    target_id = int(target_id_str.strip())
    access_list = ctx.db.getListVars(ctx.owner_id, "create_bot_access") or []

    if action == "give_access":
        if target_id not in access_list:
            ctx.db.setListVars(ctx.owner_id, "create_bot_access", target_id)
        await callback_query.answer(
            lang.get("admin.access.give_success_alert", target_id=target_id),
            show_alert=True,
        )
    elif action == "revoke_access":
        if target_id in access_list:
            ctx.db.removeListVars(ctx.owner_id, "create_bot_access", target_id)
        await callback_query.answer(
            lang.get("admin.access.revoke_success_alert", target_id=target_id),
            show_alert=True,
        )

    await callback_query.message.delete()


@command(lambda ctx: filters.command("extend") & filters.user(ctx.owner_id))
async def extend_command_handler(client, message):
    lang = message.lang
    try:
        _, bot_id_str, days_str = message.text.split()
        bot_id = int(bot_id_str)
        days_to_add = int(days_str)

        exp_date_str = ctx.db.getVars(bot_id, "bot_expiration_date")
        current_exp_date = (
            datetime.fromisoformat(exp_date_str)
            if exp_date_str
            else datetime.now(timezone.utc)
        )
        new_exp_date = current_exp_date + timedelta(days=days_to_add)
        ctx.db.setVars(bot_id, "bot_expiration_date", new_exp_date.isoformat())

        await message.reply_text(
            lang.get(
                "admin.extend.success",
                bot_id=bot_id,
                new_date=new_exp_date.strftime("%d %b %Y"),
            )
        )

        owner_bot_id = ctx.db.getVars(bot_id, "owner_id")
        if owner_bot_id:
            try:
                bot_instance = ctx.manager.running_bots.get(bot_id)
                bot_name = (
                    bot_instance.me.first_name if bot_instance else f"ID {bot_id}"
                )
                await client.send_message(
                    owner_bot_id,
                    lang.get("admin.extend.notification", bot_name=bot_name),
                )
            except Exception:
                pass
    except ValueError:
        await message.reply_text(
            f"{lang.get('general.invalid_format')}\n{lang.get('admin.extend.usage')}"
        )
    except Exception as e:
        await message.reply_text(lang.get("admin.extend.fail", e=e))


async def _send_allbots_list(client, message_or_query, page):
    all_bots = ctx.db.getBots(is_token=True)
    lang = message_or_query.lang

    if not all_bots:
        text = lang.get("admin.allbots.empty")
        if isinstance(message_or_query, pyrogram.types.Message):
            return await message_or_query.reply_text(text)
        else:
            return await message_or_query.answer(text, show_alert=True)

    total_pages = len(all_bots)
    page = (page + total_pages) % total_pages
    bot_data = all_bots[page]
    bot_id = int(bot_data["name"])

    bot_name = f"ID {bot_id} ({lang.get('admin.allbots.offline')})"
    bot_username = None
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username
    except Exception:
        bot_name = f"ID {bot_id} ({lang.get('admin.allbots.error')})"

    owner_id = ctx.db.getVars(bot_id, "owner_id")
    owner_text = lang.get("admin.allbots.unknown")
    if owner_id:
        try:
            owner_user = await client.get_users(owner_id)
            owner_text = client.ns.arg.getMention(owner_user)
        except Exception:
            owner_text = f"ID `{owner_id}`"

    exp_date_str = ctx.db.getVars(bot_id, "bot_expiration_date")
    days_left = (
        (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days
        if exp_date_str
        else "N/A"
    )

    text = (
        f"**{lang.get('admin.allbots.title', page=page + 1, total=total_pages)}**\n\n"
    )
    text += (
        f"• **{lang.get('admin.allbots.bot_name')}:** {bot_name}\n"
        f"• **{lang.get('admin.allbots.bot_id')}:** `{bot_id}`\n"
        f"• **{lang.get('admin.allbots.bot_username')}:** @{bot_username}\n"
        f"• **{lang.get('admin.allbots.owner')}:** {owner_text}\n"
        f"• **{lang.get('admin.allbots.expires_in')}:** `{days_left}` {lang.get('admin.allbots.days')}"
    )

    btn_text = ""
    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages
        btn_text += f"| {lang.get('admin.allbots.prev_button')} - allbots_{prev_page} | | {lang.get('admin.allbots.next_button')} - allbots_{next_page};same |\n"

    btn_text += f"| {lang.get('general.close_panel')} - close_panel |"
    btn, _ = client.ns.button.create_keyboard(btn_text)

    if isinstance(message_or_query, pyrogram.types.Message):
        await message_or_query.reply_text(text, reply_markup=btn)
    else:
        await message_or_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.command("allbots") & filters.user(ctx.owner_id))
async def allbots_command_handler(client, message):
    await _send_allbots_list(client, message, 0)


@command(lambda ctx: filters.regex(r"^allbots_(\-?\d+)"), handler_type="callback")
async def allbots_callback_handler(client, callback_query):
    page = int(callback_query.data.split("_")[1])
    await _send_allbots_list(client, callback_query, page)


@command(lambda ctx: filters.regex(r"^refund_stars_"), handler_type="callback")
async def refund_stars_callback(client, callback_query):
    lang = callback_query.lang
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            lang.get("admin.refund.no_permission"), show_alert=True
        )

    db_key = ""
    try:
        refund_key = callback_query.data.split("_")[2]
        db_key = f"refund_{refund_key}"
        refund_data = ctx.db.getVars(client.me.id, db_key)
        
        if not refund_data:
            return await callback_query.edit_message_text(
                callback_query.message.text
                + f"\n\n{lang.get('admin.refund.fail_not_found')}"
            )

        user_id_to_refund = refund_data["user_id"]
        charge_id = refund_data["charge_id"]
        
        await client.refund_star_payment(
            user_id=user_id_to_refund, telegram_payment_charge_id=charge_id
        )
        
        await callback_query.edit_message_text(
            text=callback_query.message.text + lang.get("admin.refund.success_text"),
            entities=callback_query.message.entities,
        )
        
        await client.send_message(
            user_id_to_refund, lang.get("admin.refund.success_notif")
        )

    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal merefund donasi: {e}")
        await callback_query.edit_message_text(
            callback_query.message.text + lang.get("admin.refund.fail_text", e=e)
        )
    finally:
        if db_key:
            ctx.db.removeVars(client.me.id, db_key)

@command(lambda ctx: filters.regex(r"^stats_(\d+)"), handler_type="callback")
async def show_stars_stats(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    
    lang = callback_query.lang
    page = int(callback_query.data.split("_")[1])
    
    try:
        await callback_query.answer(lang.get("general.processing"))
        
        peer = await client.resolve_peer(client.me.id)
        raw_result = await client.invoke(
            pyrogram.raw.functions.payments.GetStarsTransactions(
                peer=peer,
                offset="",
                limit=0
            )
        )
        
        transactions = [pyrogram.types.StarTransaction._parse(client, t, raw_result.users, raw_result.chats) for t in raw_result.transactions]
        
        if not transactions:
            btn, txt = client.ns.button.create_keyboard(f"{lang.get('stats.no_transactions')}\n\n| {lang.get('general.back')} - settings |")
            if callback_query.message.photo:
                return await callback_query.edit_message_caption(txt, reply_markup=btn)
            return await callback_query.edit_message_text(txt, reply_markup=btn)
        
        total_balance = sum(t.amount for t in transactions)
        total_income = sum(t.amount for t in transactions if t.amount > 0)
        total_refunds = sum(abs(t.amount) for t in transactions if t.amount < 0)
        
        items_per_page = 5
        total_pages = math.ceil(len(transactions) / items_per_page)
        start_index = page * items_per_page
        end_index = start_index + items_per_page
        paginated_transactions = transactions[start_index:end_index]
        
        text = (
            f"**{lang.get('stats.title')}**\n\n"
            f"💰 **{lang.get('stats.total_balance')}:** `{total_balance}` ⭐\n"
            f"📈 **{lang.get('stats.total_income')}:** `{total_income}` ⭐\n"
            f"📉 **{lang.get('stats.total_refunds')}:** `{total_refunds}` ⭐\n"
            f"🔄 **{lang.get('stats.total_transactions')}:** `{raw_result.count}`\n\n"
            f"**{lang.get('stats.recent_transactions_title', page=page + 1, total_pages=total_pages)}**\n"
        )
        
        for t in paginated_transactions:
            peer_mention = lang.get('stats.transaction_entry_unknown')
            if t.source:
                if isinstance(t.source, pyrogram.types.User):
                    peer_mention = client.ns.arg.getMention(t.source)
                elif isinstance(t.source, pyrogram.types.Chat):
                    peer_mention = t.source.title
            
            amount_str = f"+{t.amount}" if t.amount > 0 else str(t.amount)
            text += lang.get('stats.transaction_entry',
                             date=t.date.strftime('%d %b, %H:%M'),
                             amount_str=amount_str,
                             peer=peer_mention) + "\n"
        
        btn_text = ""
        if total_pages > 1:
            prev_page = page - 1 if page > 0 else total_pages - 1
            next_page = page + 1 if page < total_pages - 1 else 0
            btn_text += f"| {lang.get('stats.prev_button')} - stats_{prev_page} | {lang.get('stats.next_button')} - stats_{next_page};same |\n"
            
        btn_text += f"| {lang.get('general.back_to_settings')} - settings |"
        
        btn, _ = client.ns.button.create_keyboard(btn_text)
        if callback_query.message.photo:
            await callback_query.edit_message_caption(text, reply_markup=btn)
        else:
            await callback_query.edit_message_text(text, reply_markup=btn)

    except Exception as e:
        await callback_query.answer(f"Error: {e}", show_alert=True)
