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
    cmd = client.ns.telegram.arg.getMessage(message, is_arg=True)
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

    final_output = lang.get("admin.eval.output", output=evaluation.strip(), time=end_time - start_time)

    if len(final_output) > 4096:
        with BytesIO(str.encode(evaluation)) as out_file:
            out_file.name = "eval_result.txt"
            await message.reply_document(document=out_file, caption=lang.get("admin.eval.too_long_caption"))
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
        if db_path and os.path.exists(db_filename_in_zip) and db_filename_in_zip != db_path:
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rename(db_filename_in_zip, db_path)

        await status_msg.edit_text(lang.get("admin.restore.success", db_path=db_path))
        ctx.log.print(f"{ctx.log.GREEN}Database '{db_path}' restored by admin.")
    except Exception as e:
        await status_msg.edit_text(lang.get("admin.restore.fail", e=str(e)))
        ctx.log.print(f"{ctx.log.RED}Restore failed: {e}")
    finally:
        if downloaded_zip_path and os.path.exists(downloaded_zip_path):
            os.remove(downloaded_zip_path)


@command(lambda ctx: filters.command("akses"))
@seller_only
async def access_command_handler(client, message):
    lang = message.lang
    user_id_target, _ = await client.ns.telegram.arg.getReasonAndId(message)
    if not user_id_target:
        return await message.reply_text(lang.get("admin.access.usage_error"))

    try:
        target_user = await client.get_users(user_id_target)
        access_list = ctx.db.getListVars(client.me.id, "create_bot_access") or []

        status_text = (
            lang.get("admin.access.has_access") if target_user.id in access_list else lang.get("admin.access.no_access")
        )

        text = lang.get(
            "admin.access.panel",
            mention=client.ns.telegram.arg.getMention(target_user),
            id=target_user.id,
            status=status_text,
        )

        btn_text = (
            f"| {lang.get('admin.access.give_button')} - give_access {target_user.id} |\n"
            f"| {lang.get('admin.access.revoke_button')} - revoke_access {target_user.id};same |"
        )

        btn, _ = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")
        await message.reply_text(text, reply_markup=btn)
    except Exception as e:
        await message.reply_text(lang.get("admin.access.process_fail", e=e))


@command(lambda ctx: filters.regex(r"^(give|revoke)_access\s(\d+)"), handler_type="callback")
async def manage_access_callback(client, callback_query):
    lang = callback_query.lang
    action, target_id_str = callback_query.data.split(" ", 1)
    target_id = int(target_id_str.strip())

    try:
        target_user = await client.get_users(target_id)
        mention = client.ns.telegram.arg.getMention(target_user)
        access_list = ctx.db.getListVars(client.me.id, "create_bot_access") or []

        text = ""
        alert_text = ""

        if action == "give_access":
            if target_id not in access_list:
                ctx.db.setListVars(client.me.id, "create_bot_access", target_id)
            alert_text = lang.get("admin.access.give_success_alert", target_id=target_id)
            text = lang.get("admin.access.give_success_panel", mention=mention)

        elif action == "revoke_access":
            if target_id in access_list:
                ctx.db.removeListVars(client.me.id, "create_bot_access", target_id)
            alert_text = lang.get("admin.access.revoke_success_alert", target_id=target_id)
            text = lang.get("admin.access.revoke_success_panel", mention=mention)

        await callback_query.answer(alert_text)

        btn_text = f"| {lang.get('general.close_panel')} - close_panel |"
        btn, _ = client.ns.telegram.button.create_inline_keyboard(btn_text)

        await callback_query.edit_message_text(text, reply_markup=btn)

    except Exception as e:
        await callback_query.answer(lang.get("admin.access.process_fail", e=e), show_alert=True)


@command(lambda ctx: filters.command("extend") & filters.user(ctx.owner_id))
async def extend_command_handler(client, message):
    lang = message.lang
    try:
        _, bot_id_str, days_str = message.text.split()
        bot_id = int(bot_id_str)
        days_to_add = int(days_str)

        exp_date_str = ctx.db.getVars(bot_id, "bot_expiration_date")
        current_exp_date = datetime.fromisoformat(exp_date_str) if exp_date_str else datetime.now(timezone.utc)
        new_exp_date = current_exp_date + timedelta(days=days_to_add)
        ctx.db.setVars(bot_id, "bot_expiration_date", new_exp_date.isoformat())

        await message.reply_text(
            lang.get("admin.extend.success", bot_id=bot_id, new_date=new_exp_date.strftime("%d %b %Y"))
        )

        owner_bot_id = ctx.db.getVars(bot_id, "owner_id")
        if owner_bot_id:
            try:
                bot_instance = ctx.manager.running_bots.get(bot_id)
                bot_name = bot_instance.me.first_name if bot_instance else f"ID {bot_id}"
                await client.send_message(owner_bot_id, lang.get("admin.extend.notification", bot_name=bot_name))
            except Exception:
                pass
    except ValueError:
        await message.reply_text(lang.get("admin.extend.usage_error"))
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

    bot_name = f"ID {bot_id} {lang.get('admin.allbots.offline')}"
    bot_username = "N/A"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username
    except Exception:
        bot_name = f"ID {bot_id} {lang.get('admin.allbots.error')}"

    owner_id = ctx.db.getVars(bot_id, "owner_id")
    owner_text = lang.get("admin.allbots.unknown")
    if owner_id:
        try:
            owner_user = await client.get_users(owner_id)
            owner_text = client.ns.telegram.arg.getMention(owner_user)
        except Exception:
            owner_text = f"ID `{owner_id}`"

    exp_date_str = ctx.db.getVars(bot_id, "bot_expiration_date")
    days_left = (datetime.fromisoformat(exp_date_str) - datetime.now(timezone.utc)).days if exp_date_str else "N/A"

    text = lang.get(
        "admin.allbots.panel",
        page=page + 1,
        total=total_pages,
        bot_name=bot_name,
        bot_id=bot_id,
        username=bot_username,
        owner=owner_text,
        days_left=days_left,
    )

    btn_text = ""
    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages
        btn_text += f"| {lang.get('admin.allbots.prev_button')} - allbots_{prev_page} | | {lang.get('admin.allbots.next_button')} - allbots_{next_page};same |\n"

    btn_text += f"| {lang.get('general.close_panel')} - close_panel |"
    btn, _ = client.ns.telegram.button.create_inline_keyboard(btn_text)

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
        return await callback_query.answer(lang.get("admin.refund.no_permission"), show_alert=True)

    db_key = ""
    try:
        refund_key = callback_query.data.split("_")[2]
        db_key = f"refund_{refund_key}"
        refund_data = ctx.db.getVars(client.me.id, db_key)

        if not refund_data:
            return await callback_query.edit_message_text(
                callback_query.message.text + lang.get("admin.refund.fail_not_found")
            )

        user_id_to_refund = refund_data["user_id"]
        charge_id = refund_data["charge_id"]

        await client.refund_star_payment(user_id=user_id_to_refund, telegram_payment_charge_id=charge_id)

        await callback_query.edit_message_text(
            text=callback_query.message.text + lang.get("admin.refund.success_text"),
            entities=callback_query.message.entities,
        )

        await client.send_message(user_id_to_refund, lang.get("admin.refund.success_notif"))

    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal merefund donasi: {e}")
        await callback_query.edit_message_text(callback_query.message.text + lang.get("admin.refund.fail_text", e=e))
    finally:
        if db_key:
            ctx.db.removeVars(client.me.id, db_key)


@command(lambda ctx: filters.regex(r"^stats_(\d+)"), handler_type="callback")
async def show_stars_stats(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    lang = callback_query.lang
    page = int(callback_query.data.split("_")[1])
    items_per_page = 5

    try:
        await callback_query.answer(lang.get("general.processing"))

        peer = await client.resolve_peer(client.me.id)

        raw_result = await client.invoke(
            pyrogram.raw.functions.payments.GetStarsTransactions(peer=peer, offset="", limit=200)
        )

        transactions_history = raw_result.history if hasattr(raw_result, "history") else []

        if not transactions_history:
            text = lang.get("stats.no_transactions")
            btn_text = f"| {lang.get('general.back_to_settings')} - settings |"
            btn, txt = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")
            if callback_query.message.photo:
                return await callback_query.edit_message_caption(txt, reply_markup=btn)
            return await callback_query.edit_message_text(txt, reply_markup=btn)

        total_balance = raw_result.balance.amount
        total_income = sum(t.amount.amount for t in transactions_history if t.amount.amount > 0)
        total_refunds = sum(abs(t.amount.amount) for t in transactions_history if t.amount.amount < 0)
        total_transactions_count = len(transactions_history)

        peer_map = {p.id: p for p in raw_result.users + raw_result.chats}
        total_pages = math.ceil(total_transactions_count / items_per_page)
        start_index = page * items_per_page
        end_index = start_index + items_per_page
        paginated_transactions = transactions_history[start_index:end_index]

        transactions_text_list = []
        jakarta_timezone = ZoneInfo("Asia/Jakarta")

        for t in paginated_transactions:
            peer_id = t.peer.peer.user_id if hasattr(t.peer.peer, "user_id") else t.peer.peer.channel_id
            peer_obj = peer_map.get(peer_id)

            peer_mention = lang.get("stats.transaction_entry_unknown")
            if peer_obj:
                peer_mention = f"{peer_obj.first_name}" if hasattr(peer_obj, "first_name") else f"{peer_obj.title}"

            amount = t.amount.amount
            amount_str = f"+{amount}" if amount > 0 else str(amount)
            transaction_date = datetime.fromtimestamp(t.date, tz=timezone.utc).astimezone(jakarta_timezone)

            transactions_text_list.append(
                lang.get(
                    "stats.transaction_entry",
                    date=transaction_date.strftime("%d %b, %H:%M %Z"),
                    amount_str=amount_str,
                    peer=peer_mention,
                )
            )

        transactions_text = "\n".join(transactions_text_list)

        text = lang.get(
            "stats.panel",
            balance=total_balance,
            income=total_income,
            refunds=total_refunds,
            count=total_transactions_count,
            page=page + 1,
            total_pages=total_pages,
            transactions=transactions_text,
        )

        btn_text = ""
        if total_pages > 1:
            prev_page = page - 1 if page > 0 else total_pages - 1
            next_page = page + 1 if page < total_pages - 1 else 0
            btn_text += f"| {lang.get('stats.prev_button')} - stats_{prev_page} | | {lang.get('stats.next_button')} - stats_{next_page};same |\n"

        btn_text += f"| {lang.get('general.back_to_settings')} - settings |"

        btn, txt = client.ns.telegram.button.create_inline_keyboard(f"{text} {btn_text}")
        if callback_query.message.photo:
            await callback_query.edit_message_caption(txt, reply_markup=btn)
        else:
            await callback_query.edit_message_text(txt, reply_markup=btn)

    except Exception as e:
        ctx.log.print(f"{ctx.log.RED} Error fetching stars stats: {e}\n{traceback.format_exc()}")
        await callback_query.answer(f"Error: {e}", show_alert=True)


@command(lambda ctx: filters.regex(r"^list_all_users_(\d+)(_refresh)?"), handler_type="callback")
async def list_all_users_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(callback_query.lang.get("general.no_access"), show_alert=True)

    lang = callback_query.lang
    match = callback_query.matches[0]
    page = int(match.group(1))
    is_refresh = bool(match.group(2))
    bot_id = client.me.id

    if not hasattr(ctx, "all_users_cache"):
        ctx.all_users_cache = {}

    if is_refresh or bot_id not in ctx.all_users_cache:
        await callback_query.answer(lang.get("admin.list_users.refreshing_data"), show_alert=False)
        user_ids = ctx.db.getListVars(bot_id, "user_ids") or []
        user_data_cache = []
        if user_ids:
            for i in range(0, len(user_ids), 200):
                chunk_ids = user_ids[i : i + 200]
                try:
                    users = await client.get_users(chunk_ids)
                    user_data_cache.extend(users)
                    await asyncio.sleep(1)
                except pyrogram.errors.FloodWait as e:
                    await asyncio.sleep(e.value + 2)
                    users = await client.get_users(chunk_ids)
                    user_data_cache.extend(users)
                except Exception as e:
                    ctx.log.warning(f"Gagal mengambil chunk pengguna: {e}")
        ctx.all_users_cache[bot_id] = user_data_cache

    users_data = ctx.all_users_cache.get(bot_id, [])

    back_btn_text = f"| {lang.get('general.back_to_settings')} - settings |"

    if not users_data:
        text = lang.get("admin.list_users.no_users")
        refresh_btn = f"| {lang.get('admin.list_users.refresh_button')} - list_all_users_0_refresh |"
        btn, _ = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{refresh_btn}\n{back_btn_text}")
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)

    items_per_page = 5
    total_pages = math.ceil(len(users_data) / items_per_page)
    page = max(0, min(page, total_pages - 1))
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    page_user_data = users_data[start_index:end_index]

    text = lang.get("admin.list_users.panel_title", page=page + 1, total_pages=total_pages)
    for user in page_user_data:
        text += f"• {client.ns.telegram.arg.getMention(user)} (`{user.id}`)\n  - @{user.username or 'N/A'}\n"

    btn_text_list = []
    pagination_row_parts = []
    if total_pages > 1:
        if page > 0:
            pagination_row_parts.append(f"| « - list_all_users_{page-1} |")
        pagination_row_parts.append(
            f"| {lang.get('admin.list_users.page_info', page=page+1, total=total_pages)} - noop;same |"
        )
        if page < total_pages - 1:
            pagination_row_parts.append(f"| » - list_all_users_{page+1};same |")

    if pagination_row_parts:
        btn_text_list.append(" ".join(pagination_row_parts))

    i = 0
    while i < len(page_user_data):
        user1 = page_user_data[i]
        btn1_text = lang.get(
            "admin.list_users.send_message_button", name=user1.first_name[:10] if user1.first_name else user1.id
        )
        btn1_str = f"| {btn1_text} - message_user_{user1.id}_{page} |"

        if i + 1 < len(page_user_data):
            user2 = page_user_data[i + 1]
            btn2_text = lang.get(
                "admin.list_users.send_message_button", name=user2.first_name[:10] if user2.first_name else user2.id
            )
            btn2_str = f"| {btn2_text} - message_user_{user2.id}_{page};same |"
            btn_text_list.append(f"{btn1_str}{btn2_str}")
            i += 2
        else:
            btn_text_list.append(btn1_str)
            i += 1

    btn_text_list.append(f"| {lang.get('admin.list_users.refresh_button')} - list_all_users_{page}_refresh |")
    btn_text_list.append(back_btn_text)

    btn, _ = client.ns.telegram.button.create_inline_keyboard("\n".join(btn_text_list))

    try:
        if callback_query.message.photo:
            await callback_query.edit_message_caption(text, reply_markup=btn)
        else:
            await callback_query.edit_message_text(text, reply_markup=btn)
    except pyrogram.errors.MessageNotModified:
        await callback_query.answer(lang.get("admin.list_users.data_updated_answer"), show_alert=False)
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal mengedit daftar pengguna: {e}")
        await callback_query.answer(lang.get("admin.list_users.update_error_answer"), show_alert=True)


@command(lambda ctx: filters.regex(r"^message_user_(\d+)_(\d+)"), handler_type="callback")
async def message_user_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(callback_query.lang.get("general.no_access"), show_alert=True)

    lang = callback_query.lang
    target_user_id, page = map(int, callback_query.data.split("_")[2:])

    try:
        prompt = f"{lang.get('admin.message_user.prompt')}{lang.get('prompts.cancel_footer')}"
        ask_msg = await client.ask(callback_query.from_user.id, prompt, timeout=300)

        if ask_msg.text and ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        await ask_msg.forward(target_user_id)
        await ask_msg.reply_text(lang.get("admin.message_user.success"))
    except listen.UserCancelled:
        await client.send_message(callback_query.from_user.id, lang.get("admin.message_user.cancelled"))
    except asyncio.TimeoutError:
        await client.send_message(callback_query.from_user.id, lang.get("admin.message_user.timeout"))
    except Exception as e:
        await client.send_message(callback_query.from_user.id, lang.get("admin.message_user.fail", e=e))


@command(lambda ctx: filters.command("dashboard") & filters.user(ctx.owner_id))
async def dashboard_command_handler(client, message):
    lang = message.lang
    msg = await message.reply_text(lang.get("general.processing"))

    all_bots_data = ctx.db.getBots(is_token=True)
    total_bots = len(all_bots_data)

    unique_users = set()
    bot_user_counts = {}
    for bot_data in all_bots_data:
        bot_id = int(bot_data["name"])
        user_ids = ctx.db.getListVars(bot_id, "user_ids") or []
        bot_user_counts[bot_id] = len(user_ids)
        for user_id in user_ids:
            unique_users.add(user_id)

    total_users = len(unique_users)

    top_bot_id = max(bot_user_counts, key=bot_user_counts.get) if bot_user_counts else None
    top_bot_info = "N/A"
    if top_bot_id:
        top_bot_instance = ctx.manager.running_bots.get(top_bot_id)
        top_bot_name = top_bot_instance.me.first_name if top_bot_instance else f"ID {top_bot_id}"
        top_bot_info = f"{top_bot_name} ({bot_user_counts[top_bot_id]} pengguna)"

    try:
        stats = client.ns.server.monitor.get_stats()
        server_stats_text = lang.get(
            "admin.dashboard.server_stats", cpu=stats.cpu_percent, ram=stats.ram_percent, disk=stats.disk_percent
        )
    except Exception as e:
        server_stats_text = lang.get("admin.dashboard.server_stats_fail", e=e)

    dashboard_text = lang.get(
        "admin.dashboard.panel",
        total_bots=total_bots,
        total_users=total_users,
        top_bot=top_bot_info,
        server_stats=server_stats_text,
    )

    await msg.edit_text(dashboard_text)


@command(lambda ctx: filters.command("broadcast_owners") & filters.user(ctx.owner_id))
async def broadcast_owners_handler(client, message):
    lang = message.lang

    broadcast_msg = client.ns.telegram.arg.getMessage(message)
    if not broadcast_msg:
        return await message.reply_text(lang.get("admin.broadcast_owners.usage"))

    all_bots_data = ctx.db.getBots(is_token=True)
    owner_ids = {ctx.db.getVars(int(bot["name"]), "owner_id") for bot in all_bots_data}
    owner_ids.discard(None)

    if not owner_ids:
        return await message.reply_text(lang.get("admin.broadcast_owners.no_owners"))

    progress_msg = await message.reply_text(lang.get("settings.broadcast_start", count=len(owner_ids)))

    success_count = 0
    fail_count = 0

    for owner_id in owner_ids:
        try:
            await broadcast_msg.copy(owner_id)
            success_count += 1
        except Exception as e:
            ctx.log.print(f"{ctx.log.RED}Gagal broadcast ke owner {owner_id}: {e}")
            fail_count += 1
        await asyncio.sleep(0.2)

    await progress_msg.edit(lang.get("settings.broadcast_done", success=success_count, fail=fail_count))
