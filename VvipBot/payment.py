from . import *

async def verify_user_join(client, user, chat_id, link_msg):
    verification_timeout = 3600
    start_time = time()
    is_joined = False
    while time() - start_time < verification_timeout:
        try:
            member = await client.get_chat_member(chat_id, user.id)
            if member.status not in [pyrogram.enums.ChatMemberStatus.LEFT, pyrogram.enums.ChatMemberStatus.BANNED]:
                is_joined = True
                ctx.log.print(f'{ctx.log.GREEN}User {user.id} berhasil diverifikasi bergabung ke {chat_id} dari bot {client.me.username}.')
                break
        except pyrogram.errors.UserNotParticipant:
            await asyncio.sleep(15)
        except Exception as e:
            ctx.log.print(f'{ctx.log.RED}Error saat verifikasi join {user.id} ke {chat_id}: {e}')
            break
    try:
        await link_msg.delete()
    except Exception:
        pass
    if not is_joined:
        ctx.log.print(f'{ctx.log.YELLOW}User {user.id} tidak bergabung ke {chat_id} dalam waktu yang ditentukan.')
        await client.send_message(user.id, '<emoji id=6271786398404055377>⚠️</emoji> Link undangan Anda telah kedaluwarsa karena Anda tidak bergabung dalam 60 menit. Silakan hubungi admin jika terjadi masalah.')

async def verify_user_join_multiple(client, user, invite_payloads, link_msg):
    verification_timeout = 3600
    start_time = time()
    while time() - start_time < verification_timeout:
        pending_payloads = []
        for payload in invite_payloads:
            chat_id = payload.get('chat_id')
            try:
                member = await client.get_chat_member(chat_id, user.id)
                if member.status in [pyrogram.enums.ChatMemberStatus.LEFT, pyrogram.enums.ChatMemberStatus.BANNED]:
                    pending_payloads.append(payload)
            except pyrogram.errors.UserNotParticipant:
                pending_payloads.append(payload)
            except Exception as e:
                ctx.log.print(f'{ctx.log.RED}Error saat verifikasi multi join {user.id} ke {chat_id}: {e}')
                pending_payloads.append(payload)
        if not pending_payloads:
            try:
                await link_msg.delete()
            except Exception:
                pass
            ctx.log.print(f'{ctx.log.GREEN}User {user.id} berhasil bergabung ke semua paket VVIP dari bot {client.me.username}.')
            return
        await asyncio.sleep(15)
    pending_lines = []
    for item in pending_payloads:
        pending_lines.append(f"• {item.get('name')}: {item.get('link')}")
    try:
        await client.send_message(user.id, '<emoji id=6271786398404055377>⚠️</emoji> Anda belum join ke semua grup VIP dalam waktu 60 menit.\n\nSilakan join grup berikut:\n{pending_links}\n'.format(pending_links='\n'.join(pending_lines)), protect_content=True)
    except Exception as e:
        ctx.log.print(f'{ctx.log.RED}Gagal mengirim notifikasi pending join multi {user.id}: {e}')

def _get_all_vvip_items(vvip_list):
    selected_items = []
    for (index, item) in enumerate(vvip_list):
        price = int(item.get('price', 0) or 0)
        chat_id_normal = item.get('chat_id_normal')
        if price > 0 and chat_id_normal:
            selected_items.append({'index': index, 'name': item.get('name', f'Paket {index + 1}'), 'price': price, 'chat_id': chat_id_normal, 'duration': item.get('duration', 0)})
    return selected_items

async def _create_payment_invoice(client, user, item_index, tipe, amount, coupon_code=None):
    vvip_list = await ctx.db.getListVars(client.me.id, 'list_vvip') or []
    try:
        item = vvip_list[item_index]
        names = item.get('name')
    except IndexError:
        return await client.send_message(user.id, '<emoji id=6298671811345254603>❌</emoji> Paket VVIP tidak ditemukan.')
    saweria_user_id = await ctx.db.getVars(client.me.id, 'SAWERIA_USER_ID')
    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = '<emoji id=6271786398404055377>⚠️</emoji> **Layanan Pembayaran Tidak Aktif**\n\nSilakan atur API Key untuk payment gateway terlebih dahulu.'
            layout = [[{'text': '⚙️ Atur Kunci API', 'callback_data': 'api_settings'}]]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(user.id, text, reply_markup=btn)
        else:
            await client.send_message(user.id, 'Maaf, layanan pembayaran saat ini tidak tersedia.')
        return
    msg = await client.send_message(user.id, '<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar.')
    try:
        fakeinfo = client.ns.utils.faker.generate()
        random_message = generate_safe_saweria_message(fakeinfo.name)
        (qr_string, transaction_id, qr_image_stream, amount_raw) = await client.services.saweria.create_payment(user_id=saweria_user_id, amount=int(amount), name=fakeinfo.name, email=fakeinfo.email, message=random_message, creator_name=client.me.username)
        order_data = f'{item_index}|{tipe}|{amount_raw}'
        if coupon_code:
            order_data += f'|{coupon_code}'
        await ctx.db.setVars(client.me.id, transaction_id, order_data)
        caption = '**<emoji id=6296367896398399651>✅</emoji> Pembayaran Siap Dilakukan!**\n\nSilakan scan QRIS di atas untuk membayar. Setelah itu, tekan tombol **Konfirmasi Pembayaran**.\n\n╭─ **Detail Tagihan**\n│\n├─ <emoji id=5373052667671093676>🛍️</emoji> **Produk:** {name} ({type})\n├─ <emoji id=6129870117619634982>💳</emoji> **Jumlah:** `Rp {amount}`\n├─ <emoji id=6269253325477123346>🆔</emoji> **Order ID:** {id}\n│\n╰─ <emoji id=5470177992950946662>👇</emoji> **Jika sudah membayar, silakan klik tombol di bawah ini.**\n'.format(name=names, type=tipe.title(), amount=f'{int(amount_raw):,}', id=f'[{transaction_id}](https://saweria.co/qris/{transaction_id})')
        layout = [[{'text': '✅ Konfirmasi Pembayaran', 'callback_data': f'confirm_payment {transaction_id}'}]]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_photo(user.id, photo=qr_image_stream, caption=caption, reply_markup=btn)
        await msg.delete()
        ctx.log.print(f'{ctx.log.CYAN}User {user.id} membuat pembayaran untuk {names} dari bot {client.me.username}.')
    except Exception as e:
        await msg.edit('<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>'.format(e=e))

async def _create_all_vvip_payment_invoice(client, user, selected_items, total_amount):
    saweria_user_id = await ctx.db.getVars(client.me.id, 'SAWERIA_USER_ID')
    if not saweria_user_id:
        if await is_bot_owner(client, user.id):
            text = '<emoji id=6271786398404055377>⚠️</emoji> **Layanan Pembayaran Tidak Aktif**\n\nSilakan atur API Key untuk payment gateway terlebih dahulu.'
            layout = [[{'text': '⚙️ Atur Kunci API', 'callback_data': 'api_settings'}]]
            btn = client.ns.telegram.button.build_button_grid(layout)
            await client.send_message(user.id, text, reply_markup=btn)
        else:
            await client.send_message(user.id, 'Maaf, layanan pembayaran saat ini tidak tersedia.')
        return
    msg = await client.send_message(user.id, '<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar.')
    try:
        fakeinfo = client.ns.utils.faker.generate()
        random_message = generate_safe_saweria_message(fakeinfo.name)
        (qr_string, transaction_id, qr_image_stream, amount_raw) = await client.services.saweria.create_payment(user_id=saweria_user_id, amount=int(total_amount), name=fakeinfo.name, email=fakeinfo.email, message=random_message, creator_name=client.me.username)
        package_indexes = ','.join((str(item.get('index')) for item in selected_items))
        order_data = f'ALL|normal|{int(amount_raw)}|{package_indexes}'
        await ctx.db.setVars(client.me.id, transaction_id, order_data)
        package_names = ', '.join((item.get('name') for item in selected_items))
        caption = '**<emoji id=6296367896398399651>✅</emoji> Pembayaran Siap Dilakukan!**\n\nSilakan scan QRIS di atas untuk membayar. Setelah itu, tekan tombol **Konfirmasi Pembayaran**.\n\n╭─ **Detail Tagihan**\n│\n├─ <emoji id=5373052667671093676>🛍️</emoji> **Produk:** {name} ({type})\n├─ <emoji id=6129870117619634982>💳</emoji> **Jumlah:** `Rp {amount}`\n├─ <emoji id=6269253325477123346>🆔</emoji> **Order ID:** {id}\n│\n╰─ <emoji id=5470177992950946662>👇</emoji> **Jika sudah membayar, silakan klik tombol di bawah ini.**\n'.format(name='Semua VIP ({total} paket)'.format(total=len(selected_items), names=package_names), type='Bundle', amount=f'{int(amount_raw):,}', id=f'[{transaction_id}](https://saweria.co/qris/{transaction_id})')
        layout = [[{'text': '✅ Konfirmasi Pembayaran', 'callback_data': f'confirm_payment {transaction_id}'}]]
        btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_photo(user.id, photo=qr_image_stream, caption=caption, reply_markup=btn)
        await msg.delete()
        ctx.log.print(f'{ctx.log.CYAN}User {user.id} membuat pembayaran bundling semua VVIP ({len(selected_items)} paket) dari bot {client.me.username}.')
    except Exception as e:
        await msg.edit('<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>'.format(e=e))

@command(lambda ctx: filters.regex('^confirm_payment\\s(.+)'), handler_type='callback')
async def manual_check_payment_callback(client, callback_query):
    transaction_id = callback_query.data.split(' ', 1)[1]
    user = callback_query.from_user
    ref_data_str = await ctx.db.getVars(client.me.id, transaction_id)
    if not ref_data_str:
        return await callback_query.edit_message_caption('<emoji id=6271786398404055377>⚠️</emoji> Invoice ini sudah tidak valid atau telah selesai.')
    ref_parts = ref_data_str.split('|')
    is_bundle_order = ref_parts[0] == 'ALL'
    tipe = ref_parts[1]
    amount_raw = int(ref_parts[2])
    coupon_code = None
    bundle_indexes = []
    if is_bundle_order:
        bundle_indexes = [int(i) for i in ref_parts[3].split(',') if i.strip().isdigit()] if len(ref_parts) > 3 else []
    else:
        item_index = int(ref_parts[0])
        coupon_code = ref_parts[3] if len(ref_parts) > 3 else None
    try:
        is_owner_confirm = await is_bot_owner(client, user.id)
        is_paid = is_owner_confirm or await client.services.saweria.check_paid_status(transaction_id)
        if is_paid:
            await callback_query.edit_message_reply_markup(None)
            await ctx.db.removeVars(client.me.id, transaction_id)
            vvip_list = await ctx.db.getListVars(client.me.id, 'list_vvip') or []
            if is_bundle_order:
                invite_payloads = []
                purchased_names = []
                for idx in bundle_indexes:
                    try:
                        item_found = vvip_list[idx]
                    except IndexError:
                        continue
                    name = item_found.get('name')
                    target_chat_id = item_found.get('chat_id_normal')
                    if not target_chat_id:
                        continue
                    try:
                        expire_date_link = datetime.now() + timedelta(minutes=60)
                        invite_link_obj = await client.create_chat_invite_link(chat_id=target_chat_id, member_limit=1, expire_date=expire_date_link)
                        link = invite_link_obj.invite_link
                    except Exception as e:
                        ctx.log.print(f'{ctx.log.RED}Gagal membuat invite link bundle untuk {target_chat_id}: {e}')
                        continue
                    member_data = {'user_id': user.id, 'vvip_name': name, 'join_date': datetime.now(timezone.utc).isoformat(), 'payment_type': 'normal', 'chat_id_kick': target_chat_id}
                    duration = item_found.get('duration', 0)
                    if duration > 0:
                        expiry_date = datetime.now(timezone.utc) + timedelta(days=duration)
                        member_data['expiry_date'] = expiry_date.isoformat()
                    await ctx.db.setListVars(client.me.id, 'vvip_members', member_data)
                    purchased_names.append(name)
                    invite_payloads.append({'name': name, 'chat_id': target_chat_id, 'link': link})
                if not invite_payloads:
                    raise ValueError('<emoji id=6298671811345254603>❌</emoji> Tidak ada paket VIP valid untuk pembelian semua VIP.')
                revenue_data = {'user_id': user.id, 'username': user.username or user.first_name, 'amount': amount_raw, 'date': datetime.now(timezone.utc).isoformat(), 'item_name': ' + '.join(purchased_names), 'type': 'bundle'}
                await ctx.db.setListVars(client.me.id, 'vip_revenue_history', revenue_data)
                link_text = '\n'.join([f"• {item.get('name')}: {item.get('link')}" for item in invite_payloads])
                link_msg = await client.send_message(user.id, '<emoji id=5436040291507247633>🎉</emoji> **Pembayaran Paket Semua VIP Berhasil!**\n\nBerikut semua link akses VIP Anda:\n\n{links}\n\n<emoji id=6271786398404055377>⚠️</emoji> Setiap link hanya berlaku 1 kali klik dan kedaluwarsa dalam 60 menit.\n'.format(links=link_text), protect_content=True)
                await callback_query.message.delete()
                asyncio.create_task(verify_user_join_multiple(client, user, invite_payloads, link_msg))
                owner_bot_id = await ctx.db.getVars(client.me.id, 'owner_id') or ctx.owner_id
                await client.send_message(owner_bot_id, '<emoji id=5375296873982604963>💰</emoji> **Pemasukan Baru!**\n\n**Pengguna:** {mention}\n**Bot:** {bot_mention}\n**Kategori:** `{name}` ({type})'.format(mention=client.ns.telegram.arg.getMention(user), bot_mention=client.me.mention, name='Semua VIP', type='Bundle'))
                ctx.log.print(f'{ctx.log.CYAN}User {user.id} telah mengkonfirmasi pembayaran bundle semua VVIP dari bot {client.me.username}.')
                return
            try:
                item_found = vvip_list[item_index]
                name = item_found.get('name')
            except IndexError:
                raise ValueError("Kategori VVIP '{name}' tidak lagi ditemukan di database. Pembayaran berhasil, namun link grup gagal diberikan. Mohon hubungi admin.".format(name=f'index {item_index}'))
            is_promo = tipe == 'promo'
            target_chat_id = item_found.get('chat_id_promo') if is_promo else item_found.get('chat_id_normal')
            if not target_chat_id:
                raise ValueError('Chat ID untuk paket VVIP ini belum diatur oleh admin.')
            try:
                expire_date_link = datetime.now() + timedelta(minutes=60)
                invite_link_obj = await client.create_chat_invite_link(chat_id=target_chat_id, member_limit=1, expire_date=expire_date_link)
                link = invite_link_obj.invite_link
            except Exception as e:
                ctx.log.print(f'{ctx.log.RED}Gagal membuat invite link untuk {target_chat_id}: {e}')
                raise Exception("Gagal membuat link undangan. Pastikan bot adalah admin di grup tujuan dengan hak 'Invite Users'.")
            member_data = {'user_id': user.id, 'vvip_name': name, 'join_date': datetime.now(timezone.utc).isoformat(), 'payment_type': tipe, 'chat_id_kick': target_chat_id}
            duration = item_found.get('duration', 0)
            if duration > 0:
                expiry_date = datetime.now(timezone.utc) + timedelta(days=duration)
                member_data['expiry_date'] = expiry_date.isoformat()
            if coupon_code:
                coupons = await ctx.db.getListVars(client.me.id, 'coupons') or []
                for c in coupons:
                    if c.get('code') == coupon_code:
                        c['uses_left'] = c.get('uses_left', 1) - 1
                        break
                await ctx.db.removeVars(client.me.id, 'coupons')
                for c in coupons:
                    await ctx.db.setListVars(client.me.id, 'coupons', c)
            await ctx.db.setListVars(client.me.id, 'vvip_members', member_data)
            revenue_data = {'user_id': user.id, 'username': user.username or user.first_name, 'amount': amount_raw, 'date': datetime.now(timezone.utc).isoformat(), 'item_name': name, 'type': tipe}
            await ctx.db.setListVars(client.me.id, 'vip_revenue_history', revenue_data)
            link_msg = await client.send_message(user.id, '<emoji id=5436040291507247633>🎉</emoji> **Pembayaran Dikonfirmasi!**\n\nTerima kasih, berikut adalah link akses Anda untuk paket **{name}**:\n\n{link}\n\n<emoji id=6271786398404055377>⚠️</emoji> Link ini hanya berlaku untuk 1 kali klik dan akan kedaluwarsa dalam 60 menit jika tidak digunakan.\n'.format(name=name, link=link), protect_content=True)
            await callback_query.message.delete()
            asyncio.create_task(verify_user_join(client, user, target_chat_id, link_msg))
            owner_bot_id = await ctx.db.getVars(client.me.id, 'owner_id') or ctx.owner_id
            await client.send_message(owner_bot_id, '<emoji id=5375296873982604963>💰</emoji> **Pemasukan Baru!**\n\n**Pengguna:** {mention}\n**Bot:** {bot_mention}\n**Kategori:** `{name}` ({type})'.format(mention=client.ns.telegram.arg.getMention(user), bot_mention=client.me.mention, name=name, type=tipe.title()))
            ctx.log.print(f'{ctx.log.CYAN}User {user.id} telah mengkonfirmasi pembayaran {name} dari bot {client.me.username}.')
        else:
            await callback_query.answer('❌ Pembayaran belum terdeteksi. Silakan coba lagi setelah beberapa saat.', show_alert=True)
    except Exception as e:
        ctx.log.print(f'{ctx.log.RED}Error manual-check {user.id} ({client.me.username}) {transaction_id}: {e}')
        await callback_query.answer('<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>'.format(e=e), show_alert=True)

@command(lambda ctx: filters.regex('^pay_all_vvip$'), handler_type='callback')
async def pay_all_vvip_callback(client, callback_query):
    vvip_list = await ctx.db.getListVars(client.me.id, 'list_vvip') or []
    selected_items = _get_all_vvip_items(vvip_list)
    if not selected_items:
        return await callback_query.answer('<emoji id=6298671811345254603>❌</emoji> Tidak ada paket VIP valid untuk pembelian semua VIP.', show_alert=True)
    total_amount = sum((item.get('price', 0) for item in selected_items))
    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text('<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar.')
    await _create_all_vvip_payment_invoice(client, callback_query.from_user, selected_items, total_amount)

@command(lambda ctx: filters.regex('^notes_(.+)'), handler_type='callback')
async def notes_data(client, callback_query):
    item_id = callback_query.matches[0].group(1)
    if item_id.isdigit():
        item_index = int(item_id)
    else:
        if not hasattr(ctx, 'vip_list') or item_id not in ctx.vip_list:
            return await callback_query.answer('Sesi kedaluwarsa, silakan muat ulang menu.', show_alert=True)
        item_index = ctx.vip_list[item_id]
    vvip_list = await ctx.db.getListVars(client.me.id, 'list_vvip') or []
    layout = [[{'text': '• Kembali ke Daftar VVIP •', 'callback_data': 'list_vvip'}]]
    try:
        item = vvip_list[item_index]
    except IndexError:
        item = None
    if item:
        name = item.get('name')
        price_val = item.get('price', 0)
        normal_text = item.get('normal_text', '')
        desc = normal_text.format(name=name, price=f'{price_val:,}') if normal_text else "╭─ **<emoji id=5472164874886846699>✨</emoji> Detail Paket VVIP**\n│\n├─ <emoji id=5431721976769027887>📂</emoji> **Nama Paket:** `{name}`\n├─ <emoji id=5334882760735598374>📝</emoji> **Deskripsi:** Dapatkan akses instan ke konten premium dan eksklusif setelah pembayaran berhasil.\n│\n├─ <emoji id=6129870117619634982>💳</emoji> **Harga Normal:** `Rp {price}`\n│\n╰─ Silakan klik tombol 'Bayar' di bawah untuk melanjutkan!\n".format(name=name, price=f'{price_val:,}')
        layout = [[{'text': '💸 Bayar Harga Normal', 'callback_data': f'paynow_{item_index}_normal_{price_val}'}], [{'text': '🎟️ Gunakan Kupon', 'callback_data': f'apply_coupon_{item_index}_normal_{price_val}'}, {'text': '• Kembali ke Daftar VVIP •', 'callback_data': 'list_vvip'}]]
        btn = client.ns.telegram.button.build_button_grid(layout)
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(desc, reply_markup=btn)
        return await callback_query.edit_message_text(desc, reply_markup=btn)
    text = '<emoji id=6298671811345254603>❌</emoji> Paket VVIP tidak ditemukan.'
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)

@command(lambda ctx: filters.regex('^promo_detail_(.+)'), handler_type='callback')
async def promo_detail(client, callback_query):
    item_id = callback_query.matches[0].group(1)
    if item_id.isdigit():
        item_index = int(item_id)
    else:
        if not hasattr(ctx, 'vip_list') or item_id not in ctx.vip_list:
            return await callback_query.answer('Sesi kedaluwarsa, silakan muat ulang menu.', show_alert=True)
        item_index = ctx.vip_list[item_id]
    vvip_list = await ctx.db.getListVars(client.me.id, 'list_vvip') or []
    layout = [[{'text': '• Kembali ke Daftar VVIP •', 'callback_data': 'list_vvip'}]]
    try:
        item = vvip_list[item_index]
    except IndexError:
        item = None
    if item and item.get('promo_price', 0) > 0:
        name = item.get('name')
        promo_price_val = item.get('promo_price', 0)
        promo_text = item.get('promo_text', '')
        desc = promo_text.format(name=name, promo_price=f'{promo_price_val:,}') if promo_text else '╭─ **<emoji id=5436040291507247633>🎉</emoji> Penawaran Spesial Terbatas!**\n│\n├─ <emoji id=5431721976769027887>📂</emoji> **Nama Paket:** `{name}`\n├─ <emoji id=5334882760735598374>📝</emoji> **Deskripsi:** Jangan lewatkan kesempatan emas ini untuk bergabung dengan harga yang jauh lebih terjangkau!\n│\n├─ <emoji id=5375296873982604963>💰</emoji> **Harga Promo:** `Rp {promo_price}`\n│\n╰─ Segera amankan slot Anda sebelum promo berakhir!\n'.format(name=name, promo_price=f'{promo_price_val:,}')
        layout = [[{'text': '✅ Bayar Harga Promo', 'callback_data': f'paynow_{item_index}_promo_{promo_price_val}'}], [{'text': '🎟️ Gunakan Kupon', 'callback_data': f'apply_coupon_{item_index}_promo_{promo_price_val}'}, {'text': '• Kembali ke Daftar VVIP •', 'callback_data': 'list_vvip'}]]
        btn = client.ns.telegram.button.build_button_grid(layout)
        if callback_query.message.photo:
            return await callback_query.edit_message_caption(desc, reply_markup=btn)
        return await callback_query.edit_message_text(desc, reply_markup=btn)
    text = '<emoji id=6298671811345254603>❌</emoji> Paket promo tidak ditemukan atau tidak aktif.'
    btn = client.ns.telegram.button.build_button_grid(layout)
    if callback_query.message.photo:
        await callback_query.edit_message_caption(text, reply_markup=btn)
    else:
        await callback_query.edit_message_text(text, reply_markup=btn)

@command(lambda ctx: filters.regex('^apply_coupon_(\\d+)_(normal|promo)_(\\d+)'), handler_type='callback')
async def apply_coupon_callback(client, callback_query):
    chat_id = callback_query.from_user.id
    match = callback_query.matches[0]
    item_index = int(match.group(1))
    tipe = match.group(2)
    original_amount = int(match.group(3))
    await callback_query.message.delete()
    try:
        ask_msg = await client.ask(chat_id, 'Silakan masukkan kode kupon Anda.', timeout=300)
        if ask_msg.text.lower() == '/batal':
            raise listen.UserCancelled
        coupon_code = ask_msg.text.upper()
        coupons = await ctx.db.getListVars(client.me.id, 'coupons') or []
        coupon = next((c for c in coupons if c.get('code') == coupon_code), None)
        if not coupon:
            raise ValueError('<emoji id=6298671811345254603>❌</emoji> Kode kupon tidak valid.')
        if coupon.get('uses_left', 1) <= 0:
            raise ValueError('<emoji id=6298671811345254603>❌</emoji> Kupon ini sudah habis digunakan.')
        expiry_str = coupon.get('expiry_date')
        if expiry_str and datetime.fromisoformat(expiry_str) < datetime.now(timezone.utc):
            raise ValueError('<emoji id=6298671811345254603>❌</emoji> Kupon ini sudah kedaluwarsa.')
        discount_type = coupon['discount_type']
        discount_value = coupon['discount_value']
        if discount_type == 'percentage':
            final_amount = original_amount - original_amount * (discount_value / 100)
        else:
            final_amount = original_amount - discount_value
        final_amount = max(1000, int(final_amount))
        await client.send_message(chat_id, '<emoji id=6296367896398399651>✅</emoji> Kupon `{code}` berhasil digunakan! Harga awal `Rp {original}` menjadi `Rp {final}`.'.format(code=coupon_code, original=f'{original_amount:,}', final=f'{final_amount:,}'))
        await _create_payment_invoice(client, callback_query.from_user, item_index, tipe, final_amount, coupon_code)
    except listen.UserCancelled:
        await client.send_message(chat_id, '<emoji id=6298671811345254603>🚫</emoji> **Proses Dibatalkan**')
    except asyncio.TimeoutError:
        await client.send_message(chat_id, '<emoji id=5413704112220949842>⏰</emoji> **Waktu Habis**\nProses telah dibatalkan otomatis.')
    except ValueError as e:
        await client.send_message(chat_id, str(e))
    except Exception as e:
        await client.send_message(chat_id, '<emoji id=6298671811345254603>❌</emoji> **Terjadi Kesalahan**\n<pre>{e}</pre>'.format(e=e))

@command(lambda ctx: filters.regex('^paynow_(\\d+)_(normal|promo)_(\\d+)'), handler_type='callback')
async def paynow(client, callback_query):
    match = callback_query.matches[0]
    item_index = int(match.group(1))
    tipe = match.group(2)
    amount = int(match.group(3))
    if callback_query.message.photo:
        await callback_query.message.delete()
    else:
        await callback_query.edit_message_text('<emoji id=5451732530048802485>⏳</emoji> **Sedang Memproses...**\nMohon tunggu sebentar.')
    await _create_payment_invoice(client, callback_query.from_user, item_index, tipe, amount)

@command(lambda ctx: filters.PreCheckoutQuery, handler_type='pre_checkout')
async def pre_checkout_handler(client, pre_checkout_query):
    await pre_checkout_query.answer(ok=True)

@command(lambda ctx: filters.successful_payment)
async def successful_donation_handler(client, message):
    if not message.successful_payment.invoice_payload.startswith('donation_'):
        return
    user = message.from_user
    stars_donated = message.successful_payment.total_amount
    charge_id = message.successful_payment.telegram_payment_charge_id
    current_bot_id = client.me.id
    super_admin_id = ctx.owner_id
    await client.send_message(chat_id=user.id, text='<emoji id=5436040291507247633>🎉</emoji> **Terima Kasih Banyak, {name}!**\n\nKami telah menerima donasi Anda sebesar **{stars} Stars (<emoji id=6298332994260175589>⭐</emoji>)**.\nDukungan Anda adalah bahan bakar semangat bagi kami. Semoga hari Anda menyenangkan!'.format(name=user.first_name, stars=stars_donated))
    owner_of_this_bot = await ctx.db.getVars(current_bot_id, 'owner_id') or super_admin_id
    main_bot_client = ctx.manager.main_bot_client
    try:
        notification_text = '<emoji id=5472164874886846699>✨</emoji> **Donasi Baru Diterima!**\n\n**Jumlah:** `{stars}` Stars (<emoji id=6298332994260175589>⭐</emoji>)\n**Dari:** {mention} (`{id}`)\n**Melalui Bot:** {bot_mention}'.format(stars=stars_donated, mention=client.ns.telegram.arg.getMention(user), id=user.id, bot_mention=client.me.mention)
        refund_key = uuid.uuid4().hex[:16]
        refund_data = {'user_id': user.id, 'charge_id': charge_id}
        await ctx.db.setVars(current_bot_id, f'refund_{refund_key}', refund_data)
        refund_callback_data = f'refund_stars_{refund_key}'
        layout = [[{'text': '🔙 Kembalikan Donasi', 'callback_data': refund_callback_data}]]
        refund_btn = client.ns.telegram.button.build_button_grid(layout)
        await client.send_message(chat_id=owner_of_this_bot, text=notification_text, reply_markup=refund_btn)
    except pyrogram.errors.UserIsBlocked:
        ctx.log.warning(f'Gagal kirim notif donasi, Owner {owner_of_this_bot} memblokir bot {current_bot_id}')
        if main_bot_client and owner_of_this_bot != super_admin_id:
            await main_bot_client.send_message(super_admin_id, '<emoji id=6271786398404055377>⚠️</emoji> **Notifikasi Gagal Terkirim**\n\nNotifikasi donasi sebesar `{stars}` Stars dari {mention} gagal dikirim ke owner bot `{bot_name}` karena bot diblokir olehnya.'.format(stars=stars_donated, mention=client.ns.telegram.arg.getMention(user), bot_name=client.me.first_name))
    except Exception as e:
        ctx.log.print(f'{ctx.log.RED}Gagal mengirim notifikasi donasi: {e}')
    ctx.log.print(f'{ctx.log.GREEN}Donasi {stars_donated} XTR diterima dari {user.id} ({user.first_name}) melalui bot {current_bot_id}')

@command(lambda ctx: filters.regex('^renew_sub_(\\d+)'), handler_type='callback')
async def renew_subscription_callback(client, callback_query):
    item_index = int(callback_query.matches[0].group(1))
    vvip_list = await ctx.db.getListVars(client.me.id, 'list_vvip') or []
    try:
        item = vvip_list[item_index]
    except IndexError:
        return await callback_query.answer('<emoji id=6298671811345254603>❌</emoji> Paket VVIP tidak ditemukan.', show_alert=True)
    if item.get('promo_price', 0) > 0:
        callback_query.data = f'promo_detail_{item_index}'
        callback_query.matches = [re.match('promo_detail_(\\d+)', callback_query.data)]
        await promo_detail(client, callback_query)
    else:
        callback_query.data = f'notes_{item_index}'
        callback_query.matches = [re.match('notes_(\\d+)', callback_query.data)]
        await notes_data(client, callback_query)
