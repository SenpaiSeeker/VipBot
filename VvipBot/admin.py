import shutil
import tempfile

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

        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(downloaded_zip_path, "r") as zf:
                if not zf.namelist():
                    raise ValueError(lang.get("admin.restore.empty_zip"))
                zf.extractall(path=temp_dir)

            project_root = os.getcwd()
            restored_files = []

            current_db_path = getattr(ctx.db, "data_file", getattr(ctx.db, "db_file", None))

            for root, _, files in os.walk(temp_dir):
                for filename in files:
                    source_path = os.path.join(root, filename)

                    is_db_file = current_db_path and (filename.endswith(".db") or filename.endswith(".json"))
                    is_env_file = filename.endswith(".env")

                    destination_path = None
                    if is_db_file:
                        destination_path = current_db_path
                    elif is_env_file:
                        destination_path = os.path.join(project_root, filename)

                    if destination_path:
                        shutil.move(source_path, destination_path)
                        restored_files.append(os.path.basename(destination_path))

            if not restored_files:
                raise ValueError("Tidak ada file database atau .env yang valid ditemukan dalam arsip.")

            success_message = lang.get("admin.restore.success", db_path=", ".join(restored_files))
            await status_msg.edit_text(success_message)
            ctx.log.print(f"{ctx.log.GREEN}File-file berikut dipulihkan: {', '.join(restored_files)} oleh admin.")

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
        return await message.reply_text(lang.get("admin.access.usage_error"), parse_mode=ParseMode.MARKDOWN)

    try:
        target_user = await client.get_users(user_id_target)
        await ctx.db.getListVars(client.me.id, "create_bot_access") or []

        has_access = False
        user_expiry_str = await ctx.db.getVars(target_user.id, "user_expiry_date")
        if user_expiry_str:
            expiry_date = datetime.fromisoformat(user_expiry_str)
            if expiry_date > datetime.now(timezone.utc):
                has_access = True

        status_text = lang.get("admin.access.has_access") if has_access else lang.get("admin.access.no_access")

        text = lang.get(
            "admin.access.panel",
            mention=client.ns.telegram.arg.getMention(target_user),
            id=target_user.id,
            status=status_text,
        )

        layout = [
            [
                {"text": lang.get("admin.access.give_button"), "callback_data": f"give_access_{target_user.id}"},
                {"text": lang.get("admin.access.revoke_button"), "callback_data": f"revoke_access_{target_user.id}"},
            ]
        ]

        btn = client.ns.telegram.button.build_button_grid(layout)
        await message.reply_text(text, reply_markup=btn)

    except Exception as e:
        await message.reply_text(lang.get("admin.access.process_fail", e=e))


@command(lambda ctx: filters.regex(r"^give_access_(\d+)"), handler_type="callback")
@seller_only
async def give_access_callback(client, callback_query):
    lang = callback_query.lang
    target_id = int(callback_query.data.split("_")[-1])

    text = lang.get("admin.access.give_duration_panel")

    layout = []
    row = []
    for months in [1, 3, 6, 12]:
        row.append({"text": f"{months} Bulan", "callback_data": f"do_give_{target_id}_{months}"})
    layout.append(row)
    layout.append([{"text": lang.get("general.back"), "callback_data": "close_panel"}])

    btn = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^do_give_(\d+)_(\d+)"), handler_type="callback")
@seller_only
async def do_give_access_callback(client, callback_query):
    lang = callback_query.lang
    _, _, target_id_str, months_str = callback_query.data.split("_")
    target_id = int(target_id_str)
    months_to_add = int(months_str)

    try:
        target_user = await client.get_users(target_id)

        current_expiry_str = await ctx.db.getVars(target_id, "user_expiry_date")
        start_date = datetime.now(timezone.utc)

        if current_expiry_str:
            current_expiry = datetime.fromisoformat(current_expiry_str)
            if current_expiry > start_date:
                start_date = current_expiry

        new_expiry_date = start_date + timedelta(days=30 * months_to_add)
        await ctx.db.setVars(target_id, "user_expiry_date", new_expiry_date.isoformat())

        expiry_in_jakarta = new_expiry_date.astimezone(ZoneInfo("Asia/Jakarta"))

        success_text = lang.get(
            "admin.access.give_success_panel_manual",
            mention=client.ns.telegram.arg.getMention(target_user),
            months=months_to_add,
            new_date=expiry_in_jakarta.strftime("%d %B %Y, %H:%M %Z"),
        )
        await callback_query.edit_message_text(success_text)
        await callback_query.answer(lang.get("admin.access.give_success_alert", target_id=target_id))

    except Exception as e:
        await callback_query.answer(lang.get("admin.access.process_fail", e=e), show_alert=True)


@command(lambda ctx: filters.regex(r"^revoke_access_(\d+)"), handler_type="callback")
@seller_only
async def revoke_access_callback(client, callback_query):
    lang = callback_query.lang
    target_id = int(callback_query.data.split("_")[-1])

    try:
        target_user = await client.get_users(target_id)
        mention = client.ns.telegram.arg.getMention(target_user)

        await ctx.db.removeVars(target_id, "user_expiry_date")

        alert_text = lang.get("admin.access.revoke_success_alert", target_id=target_id)
        text = lang.get("admin.access.revoke_success_panel", mention=mention)

        await callback_query.answer(alert_text)
        await callback_query.edit_message_text(text)

    except Exception as e:
        await callback_query.answer(lang.get("admin.access.process_fail", e=e), show_alert=True)


@command(lambda ctx: filters.command("addseller") & filters.user(ctx.owner_id))
async def add_seller_handler(client, message):
    lang = message.lang
    args = message.command
    if len(args) < 2:
        return await message.reply_text(lang.get("admin.seller.add_usage"))

    try:
        target_id = int(args[1])
        seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
        
        if target_id in seller_list:
            return await message.reply_text(lang.get("admin.seller.already_exists", user_id=target_id))
        
        await ctx.db.setListVars(ctx.owner_id, "seller_id_list", target_id)
        await message.reply_text(lang.get("admin.seller.add_success", user_id=target_id))
    except ValueError:
        await message.reply_text(lang.get("admin.seller.add_usage"))


@command(lambda ctx: filters.command("listseller") & filters.user(ctx.owner_id))
async def list_seller_handler(client, message):
    lang = message.lang
    seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []

    if not seller_list:
        return await message.reply_text(lang.get("admin.seller.empty"))

    text = lang.get("admin.seller.list_title")
    keyboard = []

    for index, user_id in enumerate(seller_list, 1):
        text += f"{index}. ID: `{user_id}`\n"
        keyboard.append([
            {"text": f"{lang.get('admin.seller.delete_button')} ({user_id})", "callback_data": f"del_sell_{user_id}"}
        ])

    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await message.reply_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^del_sell_(\d+)"), handler_type="callback")
async def delete_seller_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return

    lang = callback_query.lang
    target_id = int(callback_query.matches[0].group(1))
    
    seller_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
    if target_id in seller_list:
        await ctx.db.removeListVars(ctx.owner_id, "seller_id_list", target_id)
        await callback_query.answer(lang.get("admin.seller.deleted", user_id=target_id), show_alert=True)
        
        new_list = await ctx.db.getListVars(ctx.owner_id, "seller_id_list") or []
        if not new_list:
            return await callback_query.edit_message_text(lang.get("admin.seller.empty"))
        
        text = lang.get("admin.seller.list_title")
        keyboard = []
        for index, user_id in enumerate(new_list, 1):
            text += f"{index}. ID: `{user_id}`\n"
            keyboard.append([
                {"text": f"{lang.get('admin.seller.delete_button')} ({user_id})", "callback_data": f"del_sell_{user_id}"}
            ])
        btn = client.ns.telegram.button.build_button_grid(keyboard)
        await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.command("listakses") & filters.user(ctx.owner_id))
async def list_akses_handler(client, message):
    lang = message.lang
    user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
    
    access_users = []
    for uid in user_ids:
        expiry = await ctx.db.getVars(uid, "user_expiry_date")
        if expiry:
            from datetime import datetime, timezone
            if datetime.fromisoformat(expiry) > datetime.now(timezone.utc):
                access_users.append(uid)

    if not access_users:
        return await message.reply_text(lang.get("admin.access_list.empty"))

    text = lang.get("admin.access_list.list_title")
    keyboard = []
    for index, uid in enumerate(access_users, 1):
        text += f"{index}. ID: `{uid}`\n"
        keyboard.append([
            {"text": f"{lang.get('admin.access_list.delete_button')} ({uid})", "callback_data": f"del_acc_{uid}"}
        ])

    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await message.reply_text(text, reply_markup=btn)


@command(lambda ctx: filters.regex(r"^del_acc_(\d+)"), handler_type="callback")
async def delete_access_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return

    lang = callback_query.lang
    target_id = int(callback_query.matches[0].group(1))

    await ctx.db.removeVars(target_id, "user_expiry_date")
    await callback_query.answer(lang.get("admin.access_list.deleted", user_id=target_id), show_alert=True)
    
    user_ids = await ctx.db.getListVars(client.me.id, "user_ids") or []
    access_users = []
    for uid in user_ids:
        expiry = await ctx.db.getVars(uid, "user_expiry_date")
        if expiry:
            from datetime import datetime, timezone
            if datetime.fromisoformat(expiry) > datetime.now(timezone.utc):
                access_users.append(uid)

    if not access_users:
        return await callback_query.edit_message_text(lang.get("admin.access_list.empty"))

    text = lang.get("admin.access_list.list_title")
    keyboard = []
    for index, uid in enumerate(access_users, 1):
        text += f"{index}. ID: `{uid}`\n"
        keyboard.append([
            {"text": f"{lang.get('admin.access_list.delete_button')} ({uid})", "callback_data": f"del_acc_{uid}"}
        ])
    btn = client.ns.telegram.button.build_button_grid(keyboard)
    await callback_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.command("extend") & filters.user(ctx.owner_id))
async def extend_command_handler(client, message):
    lang = message.lang
    try:
        _, bot_id_str, days_str = message.text.split()
        bot_id = int(bot_id_str)
        days_to_add = int(days_str)

        exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
        current_exp_date = datetime.fromisoformat(exp_date_str) if exp_date_str else datetime.now(timezone.utc)
        new_exp_date = current_exp_date + timedelta(days=days_to_add)
        await ctx.db.setVars(bot_id, "bot_expiration_date", new_exp_date.isoformat())

        await message.reply_text(
            lang.get("admin.extend.success", bot_id=bot_id, new_date=new_exp_date.strftime("%d %b %Y"))
        )

        owner_bot_id = await ctx.db.getVars(bot_id, "owner_id")
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
    all_bots = await ctx.db.getBots(is_token=True)
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

    owner_id = await ctx.db.getVars(bot_id, "owner_id")
    owner_text = lang.get("admin.allbots.unknown")
    if owner_id:
        try:
            owner_user = await client.get_users(owner_id)
            owner_text = client.ns.telegram.arg.getMention(owner_user)
        except Exception:
            owner_text = f"ID `{owner_id}`"

    exp_date_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
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

    layout = []
    pagination_row = []
    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages
        pagination_row.extend(
            [
                {"text": lang.get("admin.allbots.prev_button"), "callback_data": f"allbots_{prev_page}"},
                {"text": lang.get("admin.allbots.next_button"), "callback_data": f"allbots_{next_page}"},
            ]
        )
    if pagination_row:
        layout.append(pagination_row)

    layout.extend(
        [
            [{"text": lang.get("admin.allbots.delete_button"), "callback_data": f"confirm_delete_bot_{bot_id}"}],
            [
                {
                    "text": lang.get("admin.allbots.manage_duration_button"),
                    "callback_data": f"manage_duration_bot_{bot_id}_{page}",
                }
            ],
            [{"text": lang.get("general.close_panel"), "callback_data": "close_panel"}],
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)

    if isinstance(message_or_query, pyrogram.types.Message):
        await message_or_query.reply_text(text, reply_markup=btn)
    else:
        await message_or_query.edit_message_text(text, reply_markup=btn)


@command(lambda ctx: filters.command("allbots") & filters.user(ctx.owner_id))
async def allbots_command_handler(client, message):
    await _send_allbots_list(client, message, 0)


@command(lambda ctx: filters.regex(r"^allbots_(\-?\d+)"), handler_type="callback")
async def allbots_callback_handler(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    page = int(callback_query.data.split("_")[1])
    await _send_allbots_list(client, callback_query, page)


@command(lambda ctx: filters.regex(r"^confirm_delete_bot_(\d+)"), handler_type="callback")
async def confirm_delete_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    lang = callback_query.lang
    bot_id = int(callback_query.matches[0].group(1))
    text = lang.get("admin.allbots.delete_confirm", bot_id=bot_id)

    layout = [
        [
            {"text": lang.get("admin.allbots.delete_confirm_yes"), "callback_data": f"do_delete_bot_{bot_id}"},
            {"text": lang.get("admin.allbots.delete_confirm_no"), "callback_data": "allbots_0"},
        ]
    ]
    markup = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_text(text, reply_markup=markup)


@command(lambda ctx: filters.regex(r"^do_delete_bot_(\d+)"), handler_type="callback")
async def do_delete_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    lang = callback_query.lang
    bot_id = int(callback_query.matches[0].group(1))
    await callback_query.edit_message_text(lang.get("admin.allbots.deleting"))
    try:
        await ctx.manager.stop_bot(bot_id)
        await asyncio.sleep(1)
        await ctx.db.removeBot(bot_id)
        await ctx.db.removeAllVars(bot_id)
        await _send_allbots_list(client, callback_query, 0)
        await callback_query.answer(lang.get("admin.allbots.delete_success"), show_alert=True)
    except Exception as e:
        await callback_query.answer(lang.get("admin.allbots.delete_fail", e=e), show_alert=True)
        await _send_allbots_list(client, callback_query, 0)


@command(lambda ctx: filters.regex(r"^manage_duration_bot_(\d+)_(\d+)"), handler_type="callback")
async def manage_duration_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    lang = callback_query.lang
    bot_id, page = map(int, callback_query.data.split("_")[3:])
    text = lang.get("admin.allbots.manage_duration_panel", bot_id=bot_id)

    layout = [
        [{"text": lang.get("admin.allbots.add_duration_button"), "callback_data": f"extend_bot_{bot_id}_{page}"}],
        [{"text": lang.get("admin.allbots.reduce_duration_button"), "callback_data": f"reduce_bot_{bot_id}_{page}"}],
        [{"text": lang.get("general.back"), "callback_data": f"allbots_{page}"}],
    ]
    markup = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_text(text, reply_markup=markup)


@command(lambda ctx: filters.regex(r"^extend_bot_(\d+)_(\d+)"), handler_type="callback")
async def extend_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    lang = callback_query.lang
    bot_id, page = map(int, callback_query.data.split("_")[2:])
    text = lang.get("admin.allbots.add_duration_select", bot_id=bot_id)
    buttons = [
        {"text": f"+{days} {lang.get('admin.allbots.days')}", "callback_data": f"do_extend_{bot_id}_{days}_{page}"}
        for days in [7, 30, 90]
    ]
    layout = [buttons, [{"text": lang.get("general.back"), "callback_data": f"manage_duration_bot_{bot_id}_{page}"}]]
    markup = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_text(text, reply_markup=markup)


@command(lambda ctx: filters.regex(r"^do_extend_(\d+)_(\d+)_(\d+)"), handler_type="callback")
async def do_extend_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    lang = callback_query.lang
    bot_id, days, page = map(int, callback_query.data.split("_")[2:])
    current_expiry_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    start_date = datetime.now(timezone.utc)
    if current_expiry_str:
        current_expiry = datetime.fromisoformat(current_expiry_str)
        if current_expiry > start_date:
            start_date = current_expiry
    new_expiry_date = start_date + timedelta(days=days)
    await ctx.db.setVars(bot_id, "bot_expiration_date", new_expiry_date.isoformat())
    await callback_query.answer(
        lang.get("admin.allbots.add_duration_success", days=days, bot_id=bot_id), show_alert=True
    )
    await _send_allbots_list(client, callback_query, page)


@command(lambda ctx: filters.regex(r"^reduce_bot_(\d+)_(\d+)"), handler_type="callback")
async def reduce_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    lang = callback_query.lang
    bot_id, page = map(int, callback_query.data.split("_")[2:])
    text = lang.get("admin.allbots.reduce_duration_select", bot_id=bot_id)
    buttons = [
        {"text": f"-{days} {lang.get('admin.allbots.days')}", "callback_data": f"do_reduce_{bot_id}_{days}_{page}"}
        for days in [7, 30, 90]
    ]
    layout = [buttons, [{"text": lang.get("general.back"), "callback_data": f"manage_duration_bot_{bot_id}_{page}"}]]
    markup = client.ns.telegram.button.build_button_grid(layout)
    await callback_query.edit_message_text(text, reply_markup=markup)


@command(lambda ctx: filters.regex(r"^do_reduce_(\d+)_(\d+)_(\d+)"), handler_type="callback")
async def do_reduce_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    lang = callback_query.lang
    bot_id, days, page = map(int, callback_query.data.split("_")[2:])
    current_expiry_str = await ctx.db.getVars(bot_id, "bot_expiration_date")
    if not current_expiry_str:
        return await callback_query.answer(lang.get("admin.allbots.reduce_duration_no_expiry"), show_alert=True)
    current_expiry = datetime.fromisoformat(current_expiry_str)
    new_expiry_date = current_expiry - timedelta(days=days)
    await ctx.db.setVars(bot_id, "bot_expiration_date", new_expiry_date.isoformat())
    await callback_query.answer(
        lang.get("admin.allbots.reduce_duration_success", days=days, bot_id=bot_id), show_alert=True
    )
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
        refund_data = await ctx.db.getVars(client.me.id, db_key)

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
            await ctx.db.removeVars(client.me.id, db_key)


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
            layout = [[{"text": lang.get("general.back_to_settings"), "callback_data": "settings"}]]
            btn = client.ns.telegram.button.build_button_grid(layout)
            if callback_query.message.photo:
                return await callback_query.edit_message_caption(text, reply_markup=btn)
            return await callback_query.edit_message_text(text, reply_markup=btn)

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

        layout = []
        pagination_row = []
        if total_pages > 1:
            prev_page = page - 1 if page > 0 else total_pages - 1
            next_page = page + 1 if page < total_pages - 1 else 0
            pagination_row.extend(
                [
                    {"text": lang.get("stats.prev_button"), "callback_data": f"stats_{prev_page}"},
                    {"text": lang.get("stats.next_button"), "callback_data": f"stats_{next_page}"},
                ]
            )
        if pagination_row:
            layout.append(pagination_row)

        layout.append([{"text": lang.get("general.back_to_settings"), "callback_data": "settings"}])
        btn = client.ns.telegram.button.build_button_grid(layout)

        if callback_query.message.photo:
            await callback_query.edit_message_caption(text, reply_markup=btn)
        else:
            await callback_query.edit_message_text(text, reply_markup=btn)

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
        user_ids = await ctx.db.getListVars(bot_id, "user_ids") or []
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

    layout = []
    back_row = [{"text": lang.get("general.back_to_settings"), "callback_data": "settings"}]
    refresh_row = [{"text": lang.get("admin.list_users.refresh_button"), "callback_data": f"list_all_users_0_refresh"}]

    if not users_data:
        text = lang.get("admin.list_users.no_users")
        layout = [refresh_row, back_row]
        btn = client.ns.telegram.button.build_button_grid(layout)
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

    pagination_row = []
    if total_pages > 1:
        if page > 0:
            pagination_row.append({"text": "«", "callback_data": f"list_all_users_{page-1}"})
        pagination_row.append(
            {"text": lang.get("admin.list_users.page_info", page=page + 1, total=total_pages), "callback_data": "noop"}
        )
        if page < total_pages - 1:
            pagination_row.append({"text": "»", "callback_data": f"list_all_users_{page+1}"})
    if pagination_row:
        layout.append(pagination_row)

    action_buttons = []
    for user in page_user_data:
        btn_text = lang.get(
            "admin.list_users.send_message_button", name=user.first_name[:10] if user.first_name else user.id
        )
        action_buttons.append({"text": btn_text, "callback_data": f"message_user_{user.id}_{page}"})

    i = 0
    while i < len(action_buttons):
        layout.append(action_buttons[i : i + 2])
        i += 2

    layout.append(refresh_row)
    layout.append(back_row)

    markup = client.ns.telegram.button.build_button_grid(layout)

    try:
        if callback_query.message.photo:
            await callback_query.edit_message_caption(text, reply_markup=markup)
        else:
            await callback_query.edit_message_text(text, reply_markup=markup)
    except pyrogram.errors.MessageNotModified:
        await callback_query.answer(lang.get("admin.list_users.data_updated_answer"), show_alert=False)
    except Exception as e:
        ctx.log.print(f"{ctx.log.RED}Gagal mengedit daftar pengguna: {e}")
        await callback_query.answer(lang.get("admin.list_users.update_error_answer"), show_alert=True)


@command(lambda ctx: filters.regex(r"^message_user_(\d+)_(\d+)"), handler_type="callback")
async def message_user_callback(client, callback_query):
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

    all_bots_data = await ctx.db.getBots(is_token=True)
    total_bots = len(all_bots_data)

    unique_users = set()
    bot_user_counts = {}
    for bot_data in all_bots_data:
        bot_id = int(bot_data["name"])
        user_ids = await ctx.db.getListVars(bot_id, "user_ids") or []
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
        stats = client.ns.server.monitor.get_detailed_stats()
        server_stats_text = lang.get(
            "admin.dashboard.server_stats",
            cpu=f"[{stats.cpu['bar']}] {stats.cpu['percent']}%",
            ram=f"[{stats.ram['bar']}] {stats.ram['percent']}%", 
            disk=f"[{stats.disk['bar']}] {stats.disk['percent']}%"
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

    all_bots_data = await ctx.db.getBots(is_token=True)
    owner_ids = set()
    for bot in all_bots_data:
        owner_id = await ctx.db.getVars(int(bot["name"]), "owner_id")
        if owner_id:
            owner_ids.add(owner_id)

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
