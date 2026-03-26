import shutil
import tempfile

from . import *


@command(
    lambda ctx: filters.command("eval")
    & filters.user(ctx.owner_id)
)
async def eval_bot_handler(client, message):

    async def aexec(code, client, message):
        exec(
            "async def __aexec(client, message):\n    p = print\n    c = client\n    m = message\n    r = message.reply_to_message\n    "
            + "\n    ".join(code.split("\n"))
        )
        return await locals()["__aexec"](client, message)

    msg = await message.reply_text(
        "<emoji id=5264727218734524899>🔄</emoji> `Memproses kode...`"
    )
    cmd = client.ns.telegram.arg.getMessage(
        message, is_arg=True
    )
    if not cmd:
        return await msg.edit(
            "<emoji id=6298671811345254603>❌</emoji> **Perintah Gagal:** Harap berikan kode untuk dievaluasi."
        )
    reply_to_ = message.reply_to_message or message
    (old_stdout, old_stderr) = (sys.stdout, sys.stderr)
    (redirected_output, redirected_error) = (
        StringIO(),
        StringIO(),
    )
    (sys.stdout, sys.stderr) = (
        redirected_output,
        redirected_error,
    )
    exc = None
    start_time = time()
    try:
        await aexec(cmd, client, message)
    except Exception:
        exc = traceback.format_exc()
    end_time = time()
    (sys.stdout, sys.stderr) = (old_stdout, old_stderr)
    (stdout, stderr) = (
        redirected_output.getvalue(),
        redirected_error.getvalue(),
    )
    evaluation = (
        exc
        or stderr
        or stdout
        or "<emoji id=6296367896398399651>✅</emoji> **Eksekusi Berhasil**"
    )
    final_output = "**<emoji id=6219796119933683821>🖥️</emoji> OUTPUT:**\n<pre>{output}</pre>\n\n**<emoji id=5451732530048802485>⏳</emoji> Waktu Eksekusi:** `{time:.4f}` detik".format(
        output=evaluation.strip(),
        time=end_time - start_time,
    )
    if len(final_output) > 4096:
        with BytesIO(str.encode(evaluation)) as out_file:
            out_file.name = "eval_result.txt"
            await message.reply_document(
                document=out_file,
                caption="<emoji id=6219796119933683821>📄</emoji> Hasil evaluasi terlalu panjang. Dikirim sebagai file.",
            )
    else:
        await reply_to_.reply_text(final_output)
    await msg.delete()


@command(
    lambda ctx: filters.command("restore")
    & filters.user(ctx.owner_id)
)
async def restore_database_handler(client, message):
    if (
        not message.reply_to_message
        or not message.reply_to_message.document
    ):
        return await message.reply_text(
            "<emoji id=6271786398404055377>⚠️</emoji> **Cara Penggunaan Salah:**\nBalas (reply) ke file backup `.zip` yang dikirim oleh bot dengan perintah ini."
        )
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".zip"):
        return await message.reply_text(
            "<emoji id=6298671811345254603>❌</emoji> **Format File Salah:**\nHanya file backup dengan format `.zip` yang bisa dipulihkan."
        )
    status_msg = await message.reply_text(
        "<emoji id=5451732530048802485>⏳</emoji> `Mendownload & mengekstrak file backup...`"
    )
    downloaded_zip_path = None
    try:
        downloaded_zip_path = await client.download_media(
            message.reply_to_message
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(
                downloaded_zip_path, "r"
            ) as zf:
                if not zf.namelist():
                    raise ValueError(
                        "File .zip ini kosong atau rusak."
                    )
                zf.extractall(path=temp_dir)
            project_root = os.getcwd()
            restored_files = []
            current_db_path = getattr(
                ctx.db,
                "data_file",
                getattr(ctx.db, "db_file", None),
            )
            for root, _, files in os.walk(temp_dir):
                for filename in files:
                    source_path = os.path.join(
                        root, filename
                    )
                    is_db_file = current_db_path and (
                        filename.endswith(".db")
                        or filename.endswith(".json")
                    )
                    is_env_file = filename.endswith(".env")
                    destination_path = None
                    if is_db_file:
                        destination_path = current_db_path
                    elif is_env_file:
                        destination_path = os.path.join(
                            project_root, filename
                        )
                    if destination_path:
                        shutil.move(
                            source_path, destination_path
                        )
                        restored_files.append(
                            os.path.basename(
                                destination_path
                            )
                        )
            if not restored_files:
                raise ValueError(
                    "Tidak ada file database atau .env yang valid ditemukan dalam arsip."
                )
            success_message = "<emoji id=6296367896398399651>✅</emoji> **Pemulihan Berhasil!**\nDatabase `{db_path}` telah dipulihkan.\n\n<emoji id=6271786398404055377>⚠️</emoji> **PENTING:** Mohon **restart** bot agar dapat menggunakan database baru.".format(
                db_path=", ".join(restored_files)
            )
            await status_msg.edit_text(success_message)
            ctx.log.print(
                f"{ctx.log.GREEN}File-file berikut dipulihkan: {', '.join(restored_files)} oleh admin."
            )
    except Exception as e:
        await status_msg.edit_text(
            "<emoji id=6298671811345254603>❌</emoji> **Pemulihan Gagal!**\n\n**Error:** `{e}`".format(
                e=str(e)
            )
        )
        ctx.log.print(f"{ctx.log.RED}Restore failed: {e}")
    finally:
        if downloaded_zip_path and os.path.exists(
            downloaded_zip_path
        ):
            os.remove(downloaded_zip_path)


@command(lambda ctx: filters.command("akses"))
@seller_only
async def access_command_handler(client, message):
    (user_id_target, _) = (
        await client.ns.telegram.arg.getReasonAndId(message)
    )
    if not user_id_target:
        return await message.reply_text(
            "**Format Salah.**\nGunakan: `/akses <user_id atau @username>`",
            parse_mode=ParseMode.MARKDOWN,
        )
    try:
        target_user = await client.get_users(user_id_target)
        await ctx.db.getListVars(
            client.me.id, "create_bot_access"
        ) or []
        has_access = False
        user_expiry_str = await ctx.db.getVars(
            target_user.id, "user_expiry_date"
        )
        if user_expiry_str:
            expiry_date = datetime.fromisoformat(
                user_expiry_str
            )
            if expiry_date > datetime.now(timezone.utc):
                has_access = True
        status_text = (
            "<emoji id=6296367896398399651>✅</emoji> Memiliki Akses"
            if has_access
            else "<emoji id=6298671811345254603>❌</emoji> Tidak Memiliki Akses"
        )
        text = "**<emoji id=6176966310920983412>🔑</emoji> Kelola Akses Pembuatan Bot**\n\n**Pengguna:** {mention}\n**ID:** `{id}`\n**Status:** `{status}`\n\nPilih tindakan untuk pengguna ini:".format(
            mention=client.ns.telegram.arg.getMention(
                target_user
            ),
            id=target_user.id,
            status=status_text,
        )
        layout = [
            [
                {
                    "text": "✅ Beri Akses",
                    "callback_data": f"give_access_{target_user.id}",
                },
                {
                    "text": "❌ Cabut Akses",
                    "callback_data": f"revoke_access_{target_user.id}",
                },
            ]
        ]
        btn = client.ns.telegram.button.build_button_grid(
            layout
        )
        await message.reply_text(text, reply_markup=btn)
    except Exception as e:
        await message.reply_text(
            "Gagal memproses. Error: `{e}`".format(e=e)
        )


@command(
    lambda ctx: filters.regex("^give_access_(\\d+)"),
    handler_type="callback",
)
@seller_only
async def give_access_callback(client, callback_query):
    target_id = int(callback_query.data.split("_")[-1])
    text = "Pilih durasi akses yang ingin diberikan:"
    layout = []
    row = []
    for months in [1, 3, 6, 12]:
        row.append(
            {
                "text": f"{months} Bulan",
                "callback_data": f"do_give_{target_id}_{months}",
            }
        )
    layout.append(row)
    layout.append(
        [
            {
                "text": "• Kembali •",
                "callback_data": "close_panel",
            }
        ]
    )
    btn = client.ns.telegram.button.build_button_grid(
        layout
    )
    await callback_query.edit_message_text(
        text, reply_markup=btn
    )


@command(
    lambda ctx: filters.regex("^do_give_(\\d+)_(\\d+)"),
    handler_type="callback",
)
@seller_only
async def do_give_access_callback(client, callback_query):
    (_, _, target_id_str, months_str) = (
        callback_query.data.split("_")
    )
    target_id = int(target_id_str)
    months_to_add = int(months_str)
    try:
        target_user = await client.get_users(target_id)
        current_expiry_str = await ctx.db.getVars(
            target_id, "user_expiry_date"
        )
        start_date = datetime.now(timezone.utc)
        if current_expiry_str:
            current_expiry = datetime.fromisoformat(
                current_expiry_str
            )
            if current_expiry > start_date:
                start_date = current_expiry
        new_expiry_date = start_date + timedelta(
            days=30 * months_to_add
        )
        await ctx.db.setVars(
            target_id,
            "user_expiry_date",
            new_expiry_date.isoformat(),
        )
        expiry_in_jakarta = new_expiry_date.astimezone(
            ZoneInfo("Asia/Jakarta")
        )
        success_text = "<emoji id=6296367896398399651>✅</emoji> **Akses Diberikan!**\n\nPengguna {mention} sekarang memiliki akses untuk membuat bot selama **{months} bulan**.\n\nMasa aktif akses hingga: `{new_date}`".format(
            mention=client.ns.telegram.arg.getMention(
                target_user
            ),
            months=months_to_add,
            new_date=expiry_in_jakarta.strftime(
                "%d %B %Y, %H:%M %Z"
            ),
        )
        await callback_query.edit_message_text(success_text)
        await callback_query.answer(
            "<emoji id=6296367896398399651>✅</emoji> Akses berhasil diberikan kepada {target_id}".format(
                target_id=target_id
            )
        )
    except Exception as e:
        await callback_query.answer(
            "Gagal memproses. Error: `{e}`".format(e=e),
            show_alert=True,
        )


@command(
    lambda ctx: filters.regex("^revoke_access_(\\d+)"),
    handler_type="callback",
)
@seller_only
async def revoke_access_callback(client, callback_query):
    target_id = int(callback_query.data.split("_")[-1])
    try:
        target_user = await client.get_users(target_id)
        mention = client.ns.telegram.arg.getMention(
            target_user
        )
        await ctx.db.removeVars(
            target_id, "user_expiry_date"
        )
        alert_text = "<emoji id=6298671811345254603>❌</emoji> Akses berhasil dicabut dari {target_id}".format(
            target_id=target_id
        )
        text = "<emoji id=6298671811345254603>❌</emoji> **Akses Dicabut!**\n\nPengguna {mention} tidak lagi memiliki hak untuk membuat bot.".format(
            mention=mention
        )
        await callback_query.answer(alert_text)
        await callback_query.edit_message_text(text)
    except Exception as e:
        await callback_query.answer(
            "Gagal memproses. Error: `{e}`".format(e=e),
            show_alert=True,
        )


@command(
    lambda ctx: filters.command("addseller")
    & filters.user(ctx.owner_id)
)
async def add_seller_handler(client, message):
    (user_id_target, _) = (
        await client.ns.telegram.arg.getReasonAndId(message)
    )
    if not user_id_target:
        return await message.reply_text(
            "<emoji id=6298671811345254603>❌</emoji> Pengguna tidak ditemukan. Pastikan ID/Username benar atau balas pesan pengguna."
        )
    try:
        target_user = await client.get_users(user_id_target)
        seller_list = (
            await ctx.db.getListVars(
                ctx.owner_id, "seller_id_list"
            )
            or []
        )
        if target_user.id in seller_list:
            return await message.reply_text(
                "<emoji id=6298671811345254603>❌</emoji> User `{user_id}` sudah terdaftar sebagai seller.".format(
                    user_id=target_user.id
                )
            )
        await ctx.db.setListVars(
            ctx.owner_id, "seller_id_list", target_user.id
        )
        mention = client.ns.telegram.arg.getMention(
            target_user
        )
        await message.reply_text(
            "<emoji id=6296367896398399651>✅</emoji> Berhasil menambahkan `{user_mention}` sebagai seller.".format(
                user_mention=mention
            )
        )
    except Exception as e:
        await message.reply_text(
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            )
        )


@command(
    lambda ctx: filters.command("listseller")
    & filters.user(ctx.owner_id)
)
async def list_seller_handler(client, message):
    seller_list = (
        await ctx.db.getListVars(
            ctx.owner_id, "seller_id_list"
        )
        or []
    )
    if not seller_list:
        return await message.reply_text(
            "Belum ada seller yang terdaftar."
        )
    text = "**<emoji id=6176966310920983412>👤</emoji> Daftar Seller Aktif**\n\n"
    keyboard = []
    for index, user_id in enumerate(seller_list, 1):
        try:
            user_obj = await client.get_users(user_id)
            mention = client.ns.telegram.arg.getMention(
                user_obj
            )
        except Exception:
            mention = f"ID: `{user_id}`"
        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"{'Hapus Seller 🗑️'} ({user_id})",
                    "callback_data": f"del_sell_{user_id}",
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(
        keyboard
    )
    await message.reply_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^del_sell_(\\d+)"),
    handler_type="callback",
)
async def delete_seller_callback(client, callback_query):
    if callback_query.fromuser.id != ctx.owner_id:
        return
    target_id = int(callback_query.matches[0].group(1))
    await ctx.db.removeListVars(
        ctx.owner_id, "seller_id_list", target_id
    )
    await callback_query.answer(
        "Seller `{user_id}` berhasil dihapus.".format(
            user_id=target_id
        ),
        show_alert=True,
    )
    seller_list = (
        await ctx.db.getListVars(
            ctx.owner_id, "seller_id_list"
        )
        or []
    )
    if not seller_list:
        return await callback_query.edit_message_text(
            "Belum ada seller yang terdaftar."
        )
    text = "**<emoji id=6176966310920983412>👤</emoji> Daftar Seller Aktif**\n\n"
    keyboard = []
    for index, user_id in enumerate(seller_list, 1):
        try:
            user_obj = await client.get_users(user_id)
            mention = client.ns.telegram.arg.getMention(
                user_obj
            )
        except Exception:
            mention = f"ID: `{user_id}`"
        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"{'Hapus Seller 🗑️'} ({user_id})",
                    "callback_data": f"del_sell_{user_id}",
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(
        keyboard
    )
    await callback_query.edit_message_text(
        text, reply_markup=btn
    )


@command(
    lambda ctx: filters.command("listakses")
    & filters.user(ctx.owner_id)
)
async def list_akses_handler(client, message):
    user_ids = (
        await ctx.db.getListVars(client.me.id, "user_ids")
        or []
    )
    access_users = []
    for uid in user_ids:
        expiry = await ctx.db.getVars(
            uid, "user_expiry_date"
        )
        if expiry:
            access_users.append(uid)
    if not access_users:
        return await message.reply_text(
            "Tidak ada pengguna yang memiliki akses aktif saat ini."
        )
    text = "**<emoji id=6176966310920983412>🔑</emoji> Daftar Pengguna Berakses**\n\n"
    keyboard = []
    for index, uid in enumerate(access_users, 1):
        try:
            user_obj = await client.get_users(uid)
            mention = client.ns.telegram.arg.getMention(
                user_obj
            )
        except Exception:
            mention = f"ID: `{uid}`"
        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"{'Cabut Akses 🚫'} ({uid})",
                    "callback_data": f"del_acc_{uid}",
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(
        keyboard
    )
    await message.reply_text(text, reply_markup=btn)


@command(
    lambda ctx: filters.regex("^del_acc_(\\d+)"),
    handler_type="callback",
)
async def delete_access_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    target_id = int(callback_query.matches[0].group(1))
    await ctx.db.removeVars(target_id, "user_expiry_date")
    await callback_query.answer(
        "Akses untuk `{user_id}` telah dicabut.".format(
            user_id=target_id
        ),
        show_alert=True,
    )
    user_ids = (
        await ctx.db.getListVars(client.me.id, "user_ids")
        or []
    )
    access_users = []
    for uid in user_ids:
        expiry = await ctx.db.getVars(
            uid, "user_expiry_date"
        )
        if expiry:
            access_users.append(uid)
    if not access_users:
        return await callback_query.edit_message_text(
            "Tidak ada pengguna yang memiliki akses aktif saat ini."
        )
    text = "**<emoji id=6176966310920983412>🔑</emoji> Daftar Pengguna Berakses**\n\n"
    keyboard = []
    for index, uid in enumerate(access_users, 1):
        try:
            user_obj = await client.get_users(uid)
            mention = client.ns.telegram.arg.getMention(
                user_obj
            )
        except Exception:
            mention = f"ID: `{uid}`"
        text += f"{index}. {mention}\n"
        keyboard.append(
            [
                {
                    "text": f"{'Cabut Akses 🚫'} ({uid})",
                    "callback_data": f"del_acc_{uid}",
                }
            ]
        )
    btn = client.ns.telegram.button.build_button_grid(
        keyboard
    )
    await callback_query.edit_message_text(
        text, reply_markup=btn
    )


@command(
    lambda ctx: filters.command("extend")
    & filters.user(ctx.owner_id)
)
async def extend_command_handler(client, message):
    try:
        (_, bot_id_str, days_str) = message.text.split()
        bot_id = int(bot_id_str)
        days_to_add = int(days_str)
        exp_date_str = await ctx.db.getVars(
            bot_id, "bot_expiration_date"
        )
        current_exp_date = (
            datetime.fromisoformat(exp_date_str)
            if exp_date_str
            else datetime.now(timezone.utc)
        )
        new_exp_date = current_exp_date + timedelta(
            days=days_to_add
        )
        await ctx.db.setVars(
            bot_id,
            "bot_expiration_date",
            new_exp_date.isoformat(),
        )
        await message.reply_text(
            "<emoji id=6296367896398399651>✅</emoji> **Sukses!** Durasi bot `{bot_id}` berhasil diubah. Masa aktif baru: `{new_date}`.".format(
                bot_id=bot_id,
                new_date=new_exp_date.strftime("%d %b %Y"),
            )
        )
        owner_bot_id = await ctx.db.getVars(
            bot_id, "owner_id"
        )
        if owner_bot_id:
            try:
                bot_instance = ctx.manager.running_bots.get(
                    bot_id
                )
                bot_name = (
                    bot_instance.me.first_name
                    if bot_instance
                    else f"ID {bot_id}"
                )
                await client.send_message(
                    owner_bot_id,
                    "🎉 **Kabar Baik!**\n\nMasa aktif bot Anda **{bot_name}** telah diperpanjang oleh Owner Utama.".format(
                        bot_name=bot_name
                    ),
                )
            except Exception:
                pass
    except ValueError:
        await message.reply_text(
            "**Format salah.**\nGunakan: `/extend <bot_id> <jumlah_hari>`\nContoh: `/extend 12345678 30`"
        )
    except Exception as e:
        await message.reply_text(
            "<emoji id=6298671811345254603>❌</emoji> Terjadi kesalahan: `{e}`".format(
                e=e
            )
        )


async def _send_allbots_list(
    client, message_or_query, page
):
    all_bots = await ctx.db.getBots(is_token=True)
    if not all_bots:
        text = "Belum ada bot yang dibuat oleh pengguna manapun."
        if isinstance(
            message_or_query, pyrogram.types.Message
        ):
            return await message_or_query.reply_text(text)
        else:
            return await message_or_query.answer(
                text, show_alert=True
            )
    total_pages = len(all_bots)
    page = (page + total_pages) % total_pages
    bot_data = all_bots[page]
    bot_id = int(bot_data["name"])
    bot_name = f"ID {bot_id} {'(Offline)'}"
    bot_username = "N/A"
    try:
        bot_instance = ctx.manager.running_bots.get(bot_id)
        if bot_instance and bot_instance.is_connected:
            bot_name = bot_instance.me.first_name
            bot_username = bot_instance.me.username
    except Exception:
        bot_name = f"ID {bot_id} {'(Error)'}"
    owner_id = await ctx.db.getVars(bot_id, "owner_id")
    owner_text = "Tidak diketahui"
    if owner_id:
        try:
            owner_user = await client.get_users(owner_id)
            owner_text = client.ns.telegram.arg.getMention(
                owner_user
            )
        except Exception:
            owner_text = f"ID `{owner_id}`"
    exp_date_str = await ctx.db.getVars(
        bot_id, "bot_expiration_date"
    )
    days_left = (
        (
            datetime.fromisoformat(exp_date_str)
            - datetime.now(timezone.utc)
        ).days
        if exp_date_str
        else "N/A"
    )
    text = "**<emoji id=6283073379184415506>📦</emoji> Daftar Semua Bot ({page}/{total})**\n\n• **Nama Bot:** {bot_name}\n• **ID Bot:** `{bot_id}`\n• **Username Bot:** @{username}\n• **Pemilik:** {owner}\n• **Sisa Aktif:** `{days_left}` hari".format(
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
                {
                    "text": "« Sebelumnya",
                    "callback_data": f"allbots_{prev_page}",
                },
                {
                    "text": "Selanjutnya »",
                    "callback_data": f"allbots_{next_page}",
                },
            ]
        )
    if pagination_row:
        layout.append(pagination_row)
    layout.extend(
        [
            [
                {
                    "text": "🗑️ Hapus Bot",
                    "callback_data": f"confirm_delete_bot_{bot_id}",
                }
            ],
            [
                {
                    "text": "🗓️ Kelola Masa Aktif",
                    "callback_data": f"manage_duration_bot_{bot_id}_{page}",
                }
            ],
            [
                {
                    "text": "Tutup Panel",
                    "callback_data": "close_panel",
                }
            ],
        ]
    )
    btn = client.ns.telegram.button.build_button_grid(
        layout
    )
    if isinstance(message_or_query, pyrogram.types.Message):
        await message_or_query.reply_text(
            text, reply_markup=btn
        )
    else:
        await message_or_query.edit_message_text(
            text, reply_markup=btn
        )


@command(
    lambda ctx: filters.command("allbots")
    & filters.user(ctx.owner_id)
)
async def allbots_command_handler(client, message):
    await _send_allbots_list(client, message, 0)


@command(
    lambda ctx: filters.regex("^allbots_(\\-?\\d+)"),
    handler_type="callback",
)
async def allbots_callback_handler(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    page = int(callback_query.data.split("_")[1])
    await _send_allbots_list(client, callback_query, page)


@command(
    lambda ctx: filters.regex("^confirm_delete_bot_(\\d+)"),
    handler_type="callback",
)
async def confirm_delete_bot_callback(
    client, callback_query
):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    text = "**<emoji id=6271786398404055377>⚠️</emoji> Konfirmasi Penghapusan**\n\nAnda yakin ingin menghapus bot dengan ID `{bot_id}` secara permanen?".format(
        bot_id=bot_id
    )
    layout = [
        [
            {
                "text": "✅ Ya, Hapus",
                "callback_data": f"do_delete_bot_{bot_id}",
            },
            {
                "text": "❌ Tidak",
                "callback_data": "allbots_0",
            },
        ]
    ]
    markup = client.ns.telegram.button.build_button_grid(
        layout
    )
    await callback_query.edit_message_text(
        text, reply_markup=markup
    )


@command(
    lambda ctx: filters.regex("^do_delete_bot_(\\d+)"),
    handler_type="callback",
)
async def do_delete_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    bot_id = int(callback_query.matches[0].group(1))
    await callback_query.edit_message_text(
        "<emoji id=5451732530048802485>⏳</emoji> Menghapus bot..."
    )
    try:
        await ctx.manager.stop_bot(bot_id)
        await asyncio.sleep(1)
        await ctx.db.removeBot(bot_id)
        await ctx.db.removeAllVars(bot_id)
        await _send_allbots_list(client, callback_query, 0)
        await callback_query.answer(
            "<emoji id=6296367896398399651>✅</emoji> Bot berhasil dihapus.",
            show_alert=True,
        )
    except Exception as e:
        await callback_query.answer(
            "<emoji id=6298671811345254603>❌</emoji> Gagal menghapus bot: {e}".format(
                e=e
            ),
            show_alert=True,
        )
        await _send_allbots_list(client, callback_query, 0)


@command(
    lambda ctx: filters.regex(
        "^manage_duration_bot_(\\d+)_(\\d+)"
    ),
    handler_type="callback",
)
async def manage_duration_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    (bot_id, page) = map(
        int, callback_query.data.split("_")[3:]
    )
    text = "**<emoji id=4972341539033318152>🗓️</emoji> Kelola Masa Aktif untuk Bot `{bot_id}`**".format(
        bot_id=bot_id
    )
    layout = [
        [
            {
                "text": "➕ Tambah Masa Aktif",
                "callback_data": f"extend_bot_{bot_id}_{page}",
            }
        ],
        [
            {
                "text": "➖ Kurangi Masa Aktif",
                "callback_data": f"reduce_bot_{bot_id}_{page}",
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": f"allbots_{page}",
            }
        ],
    ]
    markup = client.ns.telegram.button.build_button_grid(
        layout
    )
    await callback_query.edit_message_text(
        text, reply_markup=markup
    )


@command(
    lambda ctx: filters.regex("^extend_bot_(\\d+)_(\\d+)"),
    handler_type="callback",
)
async def extend_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    (bot_id, page) = map(
        int, callback_query.data.split("_")[2:]
    )
    text = "Pilih durasi untuk ditambahkan ke Bot `{bot_id}`:".format(
        bot_id=bot_id
    )
    buttons = [
        {
            "text": f"+{days} {'hari'}",
            "callback_data": f"do_extend_{bot_id}_{days}_{page}",
        }
        for days in [7, 30, 90]
    ]
    layout = [
        buttons,
        [
            {
                "text": "• Kembali •",
                "callback_data": f"manage_duration_bot_{bot_id}_{page}",
            }
        ],
    ]
    markup = client.ns.telegram.button.build_button_grid(
        layout
    )
    await callback_query.edit_message_text(
        text, reply_markup=markup
    )


@command(
    lambda ctx: filters.regex(
        "^do_extend_(\\d+)_(\\d+)_(\\d+)"
    ),
    handler_type="callback",
)
async def do_extend_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    (bot_id, days, page) = map(
        int, callback_query.data.split("_")[2:]
    )
    current_expiry_str = await ctx.db.getVars(
        bot_id, "bot_expiration_date"
    )
    start_date = datetime.now(timezone.utc)
    if current_expiry_str:
        current_expiry = datetime.fromisoformat(
            current_expiry_str
        )
        if current_expiry > start_date:
            start_date = current_expiry
    new_expiry_date = start_date + timedelta(days=days)
    await ctx.db.setVars(
        bot_id,
        "bot_expiration_date",
        new_expiry_date.isoformat(),
    )
    await callback_query.answer(
        "{days} hari berhasil ditambahkan ke bot {bot_id}.".format(
            days=days, bot_id=bot_id
        ),
        show_alert=True,
    )
    await _send_allbots_list(client, callback_query, page)


@command(
    lambda ctx: filters.regex("^reduce_bot_(\\d+)_(\\d+)"),
    handler_type="callback",
)
async def reduce_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    (bot_id, page) = map(
        int, callback_query.data.split("_")[2:]
    )
    text = "Pilih durasi untuk dikurangi dari Bot `{bot_id}`:".format(
        bot_id=bot_id
    )
    buttons = [
        {
            "text": f"-{days} {'hari'}",
            "callback_data": f"do_reduce_{bot_id}_{days}_{page}",
        }
        for days in [7, 30, 90]
    ]
    layout = [
        buttons,
        [
            {
                "text": "• Kembali •",
                "callback_data": f"manage_duration_bot_{bot_id}_{page}",
            }
        ],
    ]
    markup = client.ns.telegram.button.build_button_grid(
        layout
    )
    await callback_query.edit_message_text(
        text, reply_markup=markup
    )


@command(
    lambda ctx: filters.regex(
        "^do_reduce_(\\d+)_(\\d+)_(\\d+)"
    ),
    handler_type="callback",
)
async def do_reduce_bot_callback(client, callback_query):
    if callback_query.from_user.id != ctx.owner_id:
        return
    (bot_id, days, page) = map(
        int, callback_query.data.split("_")[2:]
    )
    current_expiry_str = await ctx.db.getVars(
        bot_id, "bot_expiration_date"
    )
    if not current_expiry_str:
        return await callback_query.answer(
            "Bot ini tidak memiliki tanggal kedaluwarsa untuk dikurangi.",
            show_alert=True,
        )
    current_expiry = datetime.fromisoformat(
        current_expiry_str
    )
    new_expiry_date = current_expiry - timedelta(days=days)
    await ctx.db.setVars(
        bot_id,
        "bot_expiration_date",
        new_expiry_date.isoformat(),
    )
    await callback_query.answer(
        "Masa aktif bot {bot_id} berhasil dikurangi {days} hari.".format(
            days=days, bot_id=bot_id
        ),
        show_alert=True,
    )
    await _send_allbots_list(client, callback_query, page)


@command(
    lambda ctx: filters.regex("^refund_stars_"),
    handler_type="callback",
)
async def refund_stars_callback(client, callback_query):
    if not await is_bot_owner(
        client, callback_query.from_user.id
    ):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki izin untuk melakukan ini.",
            show_alert=True,
        )
    db_key = ""
    try:
        refund_key = callback_query.data.split("_")[2]
        db_key = f"refund_{refund_key}"
        refund_data = await ctx.db.getVars(
            client.me.id, db_key
        )
        if not refund_data:
            return await callback_query.edit_message_text(
                callback_query.message.text
                + "\n\n<emoji id=6271786398404055377>⚠️</emoji> **Gagal: Transaksi tidak ditemukan atau sudah di-refund.**"
            )
        user_id_to_refund = refund_data["user_id"]
        charge_id = refund_data["charge_id"]
        await client.refund_star_payment(
            user_id=user_id_to_refund,
            telegram_payment_charge_id=charge_id,
        )
        await callback_query.edit_message_text(
            text=callback_query.message.text
            + "\n\n<emoji id=6296367896398399651>✅</emoji> Donasi berhasil dikembalikan.",
            entities=callback_query.message.entities,
        )
        await client.send_message(
            user_id_to_refund,
            "ℹ️ **Informasi Donasi**\n\nDonasi Stars Anda telah dikembalikan oleh admin. Terima kasih atas pengertiannya.",
        )
    except Exception as e:
        ctx.log.print(
            f"{ctx.log.RED}Gagal merefund donasi: {e}"
        )
        await callback_query.edit_message_text(
            callback_query.message.text
            + "\n\n<emoji id=6298671811345254603>❌</emoji> **Gagal mengembalikan donasi:**\n`{e}`".format(
                e=e
            )
        )
    finally:
        if db_key:
            await ctx.db.removeVars(client.me.id, db_key)


@command(
    lambda ctx: filters.regex("^stats_(\\d+)"),
    handler_type="callback",
)
async def show_stars_stats(client, callback_query):
    if not await is_bot_owner(
        client, callback_query.from_user.id
    ):
        return
    page = int(callback_query.data.split("_")[1])
    items_per_page = 5
    try:
        await callback_query.answer(
            "<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar."
        )
        peer = await client.resolve_peer(client.me.id)
        raw_result = await client.invoke(
            pyrogram.raw.functions.payments.GetStarsTransactions(
                peer=peer, offset="", limit=200
            )
        )
        transactions_history = (
            raw_result.history
            if hasattr(raw_result, "history")
            else []
        )
        if not transactions_history:
            text = (
                "Belum ada transaksi Stars yang tercatat."
            )
            layout = [
                [
                    {
                        "text": "• Kembali ke Pengaturan •",
                        "callback_data": "settings",
                    }
                ]
            ]
            btn = (
                client.ns.telegram.button.build_button_grid(
                    layout
                )
            )
            if callback_query.message.photo:
                return await callback_query.edit_message_caption(
                    text, reply_markup=btn
                )
            return await callback_query.edit_message_text(
                text, reply_markup=btn
            )
        total_balance = raw_result.balance.amount
        total_income = sum(
            (
                t.amount.amount
                for t in transactions_history
                if t.amount.amount > 0
            )
        )
        total_refunds = sum(
            (
                abs(t.amount.amount)
                for t in transactions_history
                if t.amount.amount < 0
            )
        )
        total_transactions_count = len(transactions_history)
        peer_map = {
            p.id: p
            for p in raw_result.users + raw_result.chats
        }
        total_pages = math.ceil(
            total_transactions_count / items_per_page
        )
        start_index = page * items_per_page
        end_index = start_index + items_per_page
        paginated_transactions = transactions_history[
            start_index:end_index
        ]
        transactions_text_list = []
        jakarta_timezone = ZoneInfo("Asia/Jakarta")
        for t in paginated_transactions:
            peer_id = (
                t.peer.peer.user_id
                if hasattr(t.peer.peer, "user_id")
                else t.peer.peer.channel_id
            )
            peer_obj = peer_map.get(peer_id)
            peer_mention = "sumber tidak dikenal"
            if peer_obj:
                peer_mention = (
                    f"{peer_obj.first_name}"
                    if hasattr(peer_obj, "first_name")
                    else f"{peer_obj.title}"
                )
            amount = t.amount.amount
            amount_str = (
                f"+{amount}" if amount > 0 else str(amount)
            )
            transaction_date = datetime.fromtimestamp(
                t.date, tz=timezone.utc
            ).astimezone(jakarta_timezone)
            transactions_text_list.append(
                "• `{date}`: **{amount_str}<emoji id=6298332994260175589>⭐</emoji>** dari {peer}".format(
                    date=transaction_date.strftime(
                        "%d %b, %H:%M %Z"
                    ),
                    amount_str=amount_str,
                    peer=peer_mention,
                )
            )
        transactions_text = "\n".join(
            transactions_text_list
        )
        text = "**<emoji id=5431577498364158238>📊</emoji> Statistik Pendapatan Stars**\n\n<emoji id=5375296873982604963>💰</emoji> **Saldo Saat Ini:** `{balance}` <emoji id=6298332994260175589>⭐</emoji>\n<emoji id=5373001317042101552>📈</emoji> **Total Pemasukan:** `{income}` <emoji id=6298332994260175589>⭐</emoji>\n<emoji id=5361748661640372834>📉</emoji> **Total Pengembalian:** `{refunds}` <emoji id=6298332994260175589>⭐</emoji>\n<emoji id=5264727218734524899>🔄</emoji> **Total Transaksi (Tampil):** `{count}`\n\n**<emoji id=5282843764451195532>📜</emoji> Transaksi Terakhir ({page}/{total_pages})**\n{transactions}".format(
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
            prev_page = (
                page - 1 if page > 0 else total_pages - 1
            )
            next_page = (
                page + 1 if page < total_pages - 1 else 0
            )
            pagination_row.extend(
                [
                    {
                        "text": "« Sebelumnya",
                        "callback_data": f"stats_{prev_page}",
                    },
                    {
                        "text": "Selanjutnya »",
                        "callback_data": f"stats_{next_page}",
                    },
                ]
            )
        if pagination_row:
            layout.append(pagination_row)
        layout.append(
            [
                {
                    "text": "• Kembali ke Pengaturan •",
                    "callback_data": "settings",
                }
            ]
        )
        btn = client.ns.telegram.button.build_button_grid(
            layout
        )
        if callback_query.message.photo:
            await callback_query.edit_message_caption(
                text, reply_markup=btn
            )
        else:
            await callback_query.edit_message_text(
                text, reply_markup=btn
            )
    except Exception as e:
        ctx.log.print(
            f"{ctx.log.RED} Error fetching stars stats: {e}\n{traceback.format_exc()}"
        )
        await callback_query.answer(
            f"Error: {e}", show_alert=True
        )


@command(
    lambda ctx: filters.regex("^total_users_count$"),
    handler_type="callback",
)
async def total_users_count_callback(
    client, callback_query
):
    if not await is_bot_owner(
        client, callback_query.from_user.id
    ):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )
    bot_id = client.me.id
    user_ids = (
        await ctx.db.getListVars(bot_id, "user_ids") or []
    )
    total_users = len(user_ids)
    text = "**<emoji id=5372926953978341366>👥</emoji> Total Pengguna Bot**\n\nJumlah keseluruhan pengguna yang pernah memulai bot ini adalah: **{total} pengguna**.".format(
        total=total_users
    )
    layout = [
        [
            {
                "text": "• Kembali ke Pengaturan •",
                "callback_data": "settings",
            }
        ]
    ]
    markup = client.ns.telegram.button.build_button_grid(
        layout
    )
    try:
        if callback_query.message.photo:
            await callback_query.edit_message_caption(
                text, reply_markup=markup
            )
        else:
            await callback_query.edit_message_text(
                text, reply_markup=markup
            )
    except pyrogram.errors.MessageNotModified:
        await callback_query.answer()
    except Exception as e:
        ctx.log.print(
            f"{ctx.log.RED}Gagal memuat total pengguna: {e}"
        )
        await callback_query.answer(
            "<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>".format(
                e=e
            ),
            show_alert=True,
        )


@command(
    lambda ctx: filters.command("dashboard")
    & filters.user(ctx.owner_id)
)
async def dashboard_command_handler(client, message):
    msg = await message.reply_text(
        "<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar."
    )
    all_bots_data = await ctx.db.getBots(is_token=True)
    total_bots = len(all_bots_data)
    unique_users = set()
    bot_user_counts = {}
    for bot_data in all_bots_data:
        bot_id = int(bot_data["name"])
        user_ids = (
            await ctx.db.getListVars(bot_id, "user_ids")
            or []
        )
        bot_user_counts[bot_id] = len(user_ids)
        for user_id in user_ids:
            unique_users.add(user_id)
    total_users = len(unique_users)
    top_bot_id = (
        max(bot_user_counts, key=bot_user_counts.get)
        if bot_user_counts
        else None
    )
    top_bot_info = "N/A"
    if top_bot_id:
        top_bot_instance = ctx.manager.running_bots.get(
            top_bot_id
        )
        top_bot_name = (
            top_bot_instance.me.first_name
            if top_bot_instance
            else f"ID {top_bot_id}"
        )
        top_bot_info = f"{top_bot_name} ({bot_user_counts[top_bot_id]} pengguna)"
    try:
        stats = (
            client.ns.server.monitor.get_detailed_stats()
        )
        stats_data = {
            "cpu": stats.cpu["percent"],
            "ram": stats.ram["percent"],
            "disk": stats.disk["percent"],
        }
        server_stats_text = "- CPU: `{cpu}%`\n- RAM: `{ram}%`\n- Disk: `{disk}%`".format(
            cpu=f"[{stats.cpu['bar']}] {stats.cpu['percent']}%",
            ram=f"[{stats.ram['bar']}] {stats.ram['percent']}%",
            disk=f"[{stats.disk['bar']}] {stats.disk['percent']}%",
        )
    except Exception as e:
        stats_data = {"cpu": 0, "ram": 0, "disk": 0}
        server_stats_text = "Gagal mengambil statistik server: `{e}`".format(
            e=e
        )
    dashboard_text = "**<emoji id=5431577498364158238>📊</emoji> Dashboard Platform**\n\n**Statistik Platform:**\n- Total Bot Aktif: `{total_bots}`\n- Total Pengguna Unik: `{total_users}`\n- Bot Terpopuler: `{top_bot}`\n\n**Kesehatan Server:**\n{server_stats}".format(
        total_bots=total_bots,
        total_users=total_users,
        top_bot=top_bot_info,
        server_stats=server_stats_text,
    )
    try:
        photo_stream = (
            client.ns.utils.dashboard.generate_dashboard(
                stats_data
            )
        )
        await message.reply_photo(
            photo=photo_stream, caption=dashboard_text
        )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(
            dashboard_text + f"\n\nError Visualisasi: {e}"
        )


@command(
    lambda ctx: filters.command("broadcast_owners")
    & filters.user(ctx.owner_id)
)
async def broadcast_owners_handler(client, message):
    broadcast_msg = client.ns.telegram.arg.getMessage(
        message
    )
    if not broadcast_msg:
        return await message.reply_text(
            "Gunakan: `/broadcast_owners <pesan>` atau balas ke sebuah pesan."
        )
    all_bots_data = await ctx.db.getBots(is_token=True)
    owner_ids = set()
    for bot in all_bots_data:
        owner_id = await ctx.db.getVars(
            int(bot["name"]), "owner_id"
        )
        if owner_id:
            owner_ids.add(owner_id)
    if not owner_ids:
        return await message.reply_text(
            "Tidak ada pemilik bot yang bisa di-broadcast."
        )
    progress_msg = await message.reply_text(
        "<emoji id=6296367896398399651>✅</emoji> Memulai siaran ke `{count}` pengguna...".format(
            count=len(owner_ids)
        )
    )
    success_count = 0
    fail_count = 0
    for owner_id in owner_ids:
        try:
            await broadcast_msg.copy(owner_id)
            success_count += 1
        except Exception as e:
            ctx.log.print(
                f"{ctx.log.RED}Gagal broadcast ke owner {owner_id}: {e}"
            )
            fail_count += 1
        await asyncio.sleep(0.2)
    await progress_msg.edit(
        "**<emoji id=5368776520921784743>📢</emoji> Siaran Selesai!**\n<emoji id=6296367896398399651>✅</emoji> **Terkirim:** `{success}`\n<emoji id=6298671811345254603>❌</emoji> **Gagal:** `{fail}` (pengguna gagal telah dihapus dari database)".format(
            success=success_count, fail=fail_count
        )
    )
