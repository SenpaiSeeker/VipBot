from . import *

@command(lambda ctx: filters.regex('^list_members_(\\-?\\d+)$'), handler_type='callback')
async def list_members_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    members_list = await ctx.db.getListVars(client.me.id, 'vvip_members') or []
    back_row = [{'text': '• Kembali ke Pengaturan •', 'callback_data': 'settings'}]
    if not members_list:
        text = '<emoji id=6296367896398399651>✅</emoji> Tidak ada member VVIP yang tercatat di database.'
        btn = client.ns.telegram.button.build_button_grid([back_row])
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)
    total_pages = len(members_list)
    try:
        page = int(callback_query.data.split('_')[-1])
        page = (page + total_pages) % total_pages
    except (ValueError, IndexError):
        page = 0
    member_data = members_list[page]
    try:
        (user_id, vvip_name) = (member_data['user_id'], member_data['vvip_name'])
        (join_date_iso, pay_type) = (member_data['join_date'], member_data['payment_type'])
        user = await client.get_users(user_id)
    except (KeyError, pyrogram.errors.UserNotParticipant) as e:
        text_error = 'Data member ini tampaknya rusak atau pengguna tidak dapat diakses lagi.\n`Error: {e}`\n\nEntri ini telah dihapus dari daftar untuk menjaga kebersihan data.'.format(e=e)
        btn_back = client.ns.telegram.button.build_button_grid([back_row])
        await callback_query.edit_message_caption(text_error, reply_markup=btn_back)
        await ctx.db.removeListVars(client.me.id, 'vvip_members', member_data)
        return
    join_dt_utc = datetime.fromisoformat(join_date_iso)
    expiry_date_str = 'Permanen'
    expiry_date_obj_str = member_data.get('expiry_date')
    if expiry_date_obj_str:
        expiry_date_obj = datetime.fromisoformat(expiry_date_obj_str)
        expiry_date_str = expiry_date_obj.strftime('%d %b %Y, %H:%M %Z')
    text = '**<emoji id=5372926953978341366>👥</emoji> Daftar Member VVIP ({page}/{total})**\n\n**Nama:** {mention}\n**ID:** `{id}`\n**Kategori:** `{category}` ({type})\n**Bergabung:** `{date}`\n**Kedaluwarsa:** `{expiry}`'.format(page=page + 1, total=total_pages, mention=client.ns.telegram.arg.getMention(user), id=user.id, category=vvip_name, type=pay_type.title(), date=join_dt_utc.strftime('%d %b %Y, %H:%M %Z'), expiry=expiry_date_str)
    button_name = (user.first_name or str(user.id))[:15]
    layout = []
    pagination_row = []
    if total_pages > 1:
        (prev_page, next_page) = ((page - 1 + total_pages) % total_pages, (page + 1) % total_pages)
        pagination_row.extend([{'text': '« Sebelumnya', 'callback_data': f'list_members_{prev_page}'}, {'text': 'Selanjutnya »', 'callback_data': f'list_members_{next_page}'}])
    if pagination_row:
        layout.append(pagination_row)
    layout.append([{'text': '🚨 Tendang {name}'.format(name=button_name), 'callback_data': f'kick_{user.id}_{vvip_name}'}])
    layout.append(back_row)
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)

@command(lambda ctx: filters.regex('^kick_(\\d+)_(.+)'), handler_type='callback')
async def confirm_kick_member_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    match = callback_query.matches[0]
    user_id_str = match.group(1)
    vvip_name = match.group(2)
    user = await client.get_users(int(user_id_str))
    text = '**<emoji id=6271786398404055377>⚠️</emoji> Konfirmasi Penendangan**\n\nAnda yakin ingin menendang **{mention}** dari grup VVIP **{name}**?\n\nPengguna akan dikeluarkan dari grup dan data keanggotaannya akan dihapus.'.format(mention=client.ns.telegram.arg.getMention(user), name=vvip_name)
    layout = [[{'text': '✅ Ya, Tendang', 'callback_data': f'do_kick_{user_id_str}_{vvip_name}'}, {'text': '❌ Tidak', 'callback_data': 'list_members_0'}]]
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)

@command(lambda ctx: filters.regex('^do_kick_(\\d+)_(.+)'), handler_type='callback')
async def do_kick_member_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    match = callback_query.matches[0]
    user_id = int(match.group(1))
    vvip_name = match.group(2)
    members_list = await ctx.db.getListVars(client.me.id, 'vvip_members') or []
    record_to_remove = next((r for r in members_list if r.get('user_id') == user_id and r.get('vvip_name') == vvip_name), None)
    if not record_to_remove:
        return await callback_query.edit_message_caption('<emoji id=6298671811345254603>❌</emoji> **Gagal:** Record keanggotaan tidak ditemukan di database.')
    chat_id_kick = record_to_remove.get('chat_id_kick')
    if not chat_id_kick:
        return await callback_query.edit_message_caption('<emoji id=6298671811345254603>❌</emoji> **Gagal:** Chat ID untuk menendang member tidak valid atau belum diatur di paket VVIP.')
    await callback_query.edit_message_caption('<emoji id=5451732530048802485>⏳</emoji> `Memproses penendangan member dari grup...`')
    try:
        await client.ban_chat_member(chat_id_kick, user_id)
        await asyncio.sleep(1)
        await client.unban_chat_member(chat_id_kick, user_id)
        await ctx.db.removeListVars(client.me.id, 'vvip_members', record_to_remove)
        user_to_kick = await client.get_users(user_id)
        layout = [[{'text': '• Kembali •', 'callback_data': 'list_members_0'}]]
        btn_back = client.ns.telegram.button.build_button_grid(layout)
        await callback_query.edit_message_caption('<emoji id=6296367896398399651>✅</emoji> **Sukses!**\nPengguna {mention} telah ditendang dari **{name}** dan dihapus dari daftar.'.format(mention=client.ns.telegram.arg.getMention(user_to_kick), name=vvip_name), reply_markup=btn_back)
    except Exception as e:
        await callback_query.edit_message_caption('<emoji id=6298671811345254603>❌</emoji> **Gagal Menendang:** `{e}`'.format(e=e))

@command(lambda ctx: filters.regex('^check_active_menu'), handler_type='callback')
async def check_active_menu_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    if 'init' in callback_query.data:
        ctx.ACTIVE_MEMBERS_CACHE = {}
    vvip_list = await ctx.db.getListVars(client.me.id, 'list_vvip') or []
    layout = []
    button_row = []
    for item in vvip_list:
        (name, chat_id_norm, chat_id_promo) = (item.get('name'), item.get('chat_id_normal'), item.get('chat_id_promo'))
        if name and chat_id_norm:
            button_row.append({'text': "👥 Cek '{name}' Normal".format(name=name), 'callback_data': f'list_active_{chat_id_norm}_0'})
        if name and chat_id_promo:
            button_row.append({'text': "👥 Cek '{name}' Promo".format(name=name), 'callback_data': f'list_active_{chat_id_promo}_0'})
        if len(button_row) == 2:
            layout.append(button_row)
            button_row = []
    if button_row:
        layout.append(button_row)
    back_row = [{'text': '• Kembali ke Pengaturan •', 'callback_data': 'settings'}]
    if not layout:
        text = 'Tidak ada VVIP dengan Chat ID valid yang terkonfigurasi. Silakan atur terlebih dahulu.'
        btn = client.ns.telegram.button.build_button_grid([back_row])
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(text, reply_markup=btn)
        return await callback_query.edit_message_text(text, reply_markup=btn)
    layout.append(back_row)
    text = '**<emoji id=6271786398404055377>🕵️</emoji> Cek Member Aktif Real-time**\n\nPilih grup yang ingin Anda periksa untuk melihat daftar anggotanya saat ini.'
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)

@command(lambda ctx: filters.regex('^list_active_(\\-?\\d+)_(\\-?\\d+)'), handler_type='callback')
async def list_active_members_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    try:
        (_, _, chat_id_str, page_str) = callback_query.data.split('_', 3)
        (chat_id, page) = (int(chat_id_str), int(page_str))
    except Exception:
        return await callback_query.answer('Data callback tidak valid.')
    if chat_id not in ctx.ACTIVE_MEMBERS_CACHE:
        try:
            await callback_query.answer('<emoji id=5451732530048802485>⏳</emoji> Mengambil data member dari server Telegram, mohon tunggu...', show_alert=False)
            members = [m async for m in client.get_chat_members(chat_id) if not m.user.is_bot]
            random.shuffle(members)
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = members
        except Exception as e:
            return await callback_query.edit_message_caption('<emoji id=6298671811345254603>❌</emoji> **Gagal Mengambil Daftar Member:**\n`{e}`'.format(e=e))
    all_members = ctx.ACTIVE_MEMBERS_CACHE.get(chat_id, [])
    if not all_members:
        return await callback_query.edit_message_caption('Tidak ada anggota (non-bot) yang ditemukan di dalam grup ini.')
    total_members = len(all_members)
    page = (page + total_members) % total_members
    (member, user) = (all_members[page], all_members[page].user)
    text = '**<emoji id=6271786398404055377>🕵️</emoji> Member Aktif ({page}/{total})**\n\n**Nama:** {mention}\n**ID:** `{id}`\n**Status:** `{status}`'.format(page=page + 1, total=total_members, mention=client.ns.telegram.arg.getMention(user), id=user.id, status=member.status.name.title())
    button_name = (user.first_name or str(user.id))[:15]
    layout = []
    pagination_row = []
    if total_members > 1:
        (prev_p, next_p) = ((page - 1 + total_members) % total_members, (page + 1) % total_members)
        pagination_row.extend([{'text': '«', 'callback_data': f'list_active_{chat_id}_{prev_p}'}, {'text': '»', 'callback_data': f'list_active_{chat_id}_{next_p}'}])
    if pagination_row:
        layout.append(pagination_row)
    layout.extend([[{'text': '🚨 Tendang {name}'.format(name=button_name), 'callback_data': f'kick_active_{chat_id}_{user.id}_{page}'}], [{'text': '• Kembali ke Pemilihan Grup •', 'callback_data': 'check_active_menu_init'}]])
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)

@command(lambda ctx: filters.regex('^kick_active_(\\-?\\d+)_(\\d+)_(\\-?\\d+)'), handler_type='callback')
async def confirm_kick_active_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    (_, _, chat_id_str, user_id_str, page_str) = callback_query.data.split('_', 4)
    user = await client.get_users(int(user_id_str))
    text = '**<emoji id=6271786398404055377>⚠️</emoji> Konfirmasi**\n\nAnda yakin ingin menendang **{mention}** dari grup?'.format(mention=client.ns.telegram.arg.getMention(user))
    layout = [[{'text': '✅ Ya, Tendang', 'callback_data': f'do_kick_active_{chat_id_str}_{user_id_str}'}, {'text': '❌ Tidak, Batalkan', 'callback_data': f'list_active_{chat_id_str}_{page_str}'}]]
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)

@command(lambda ctx: filters.regex('^do_kick_active_(\\-?\\d+)_(\\d+)'), handler_type='callback')
async def do_kick_active_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return
    (_, _, _, chat_id_str, user_id_str) = callback_query.data.split('_', 4)
    (chat_id, user_id) = (int(chat_id_str), int(user_id_str))
    try:
        await callback_query.edit_message_caption('<emoji id=5451732530048802485>⏳</emoji> `Memproses penendangan pengguna...`')
        await client.ban_chat_member(chat_id, user_id)
        await client.unban_chat_member(chat_id, user_id)
        members_list = await ctx.db.getListVars(client.me.id, 'vvip_members') or []
        record_to_remove = next((r for r in members_list if r.get('user_id') == user_id and r.get('chat_id_kick') == chat_id), None)
        if record_to_remove:
            await ctx.db.removeListVars(client.me.id, 'vvip_members', record_to_remove)
        if chat_id in ctx.ACTIVE_MEMBERS_CACHE:
            ctx.ACTIVE_MEMBERS_CACHE[chat_id] = [m for m in ctx.ACTIVE_MEMBERS_CACHE[chat_id] if m.user.id != user_id]
        user = await client.get_users(user_id)
        text = '<emoji id=6296367896398399651>✅</emoji> **Sukses!**\nPengguna **{mention}** telah ditendang dari grup.'.format(mention=client.ns.telegram.arg.getMention(user))
        layout = [[{'text': '• Kembali ke Pemilihan Grup •', 'callback_data': 'check_active_menu_init'}]]
        btn = client.ns.telegram.button.build_button_grid(layout)
        if callback_query.message.photo:
            await callback_query.edit_message_caption(text, reply_markup=btn)
        else:
            await callback_query.edit_message_text(text, reply_markup=btn)
    except Exception as e:
        await callback_query.edit_message_caption('<emoji id=6298671811345254603>❌</emoji> **Gagal Menendang:** `{e}`'.format(e=e))
