import pyrogram

from helpers import parse_dt
from helpers.modules import Modules

from .. import *


async def extend_command_handler(client, message):
    bot_id = client.me.id
    text, btn = await build_extend_panel(client, bot_id)
    return await message.reply_rich(
        pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def build_extend_panel(client, bot_id):
    try:
        bot_id = int(bot_id)
    except (TypeError, ValueError):
        pass
    bot_instance = client.manager.running_bots.get(bot_id)
    if bot_id == client.me.id:
        bot_name = client.me.first_name
    elif bot_instance and bot_instance.me:
        bot_name = bot_instance.me.first_name
    else:
        bot_name = f"ID {bot_id}"

    exp_date_str = await client.db.getVars(bot_id, "bot_expiration_date")
    current_exp_date = parse_dt(exp_date_str) if exp_date_str else None
    expiry_text = (
        f"`{current_exp_date.strftime('%d %b %Y')}`"
        if current_exp_date
        else "Belum diatur"
    )

    rows = [
        ["Bot", f"**{bot_name}** (`{bot_id}`)"],
        ["Masa Aktif", expiry_text],
        ["Pilih", "Tambah atau kurangi masa aktif"],
    ]
    text = (
        f"{client.ns.emoji.md('calendar')} **Atur Masa Aktif**\n\n"
        f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
    )

    layout = [
        [
            {
                "text": "➕ Tambah Expired",
                "callback_data": f"extend_mode_{bot_id}_add",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            },
            {
                "text": "➖ Kurangi Expired",
                "callback_data": f"extend_mode_{bot_id}_sub",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
        ]
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    return text, btn


async def build_extend_month_grid(client, bot_id, mode):
    try:
        bot_id = int(bot_id)
    except (TypeError, ValueError):
        pass
    is_add = mode == "add"
    title = (
        f"{client.ns.emoji.md('calendar')} **Tambah Masa Aktif**"
        if is_add
        else f"{client.ns.emoji.md('calendar')} **Kurangi Masa Aktif**"
    )
    rows = [
        ["Bot", f"`{bot_id}`"],
        ["Satuan", "1 bulan = 30 hari"],
        ["Pilih", "Jumlah bulan di bawah ini"],
    ]
    text = f"{title}\n\n" f"{client.ns.table.md(['Info', 'Nilai'], rows)}"

    layout = []
    row = []
    for m in range(1, 13):
        row.append(
            {
                "text": f"{m} Bulan",
                "callback_data": f"extend_month_{bot_id}_{mode}_{m}",
                "style": "blue",
                "emoji": client.ns.emoji.id("calendar"),
            }
        )
        if len(row) == 3:
            layout.append(row)
            row = []
    if row:
        layout.append(row)
    layout.append(
        [
            {
                "text": "• Kembali •",
                "callback_data": f"extend_panel_{bot_id}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ]
    )

    btn = client.ns.telegram.button.build_button_grid(layout)
    return text, btn


async def apply_extend_duration(client, bot_id, days_to_add):
    exp_date_str = await client.db.getVars(bot_id, "bot_expiration_date")
    current_exp_date = (
        parse_dt(exp_date_str) if exp_date_str else datetime.now(timezone.utc)
    )
    new_exp_date = current_exp_date + timedelta(days=days_to_add)
    await client.db.setVars(bot_id, "bot_expiration_date", new_exp_date.isoformat())
    return new_exp_date.strftime("%d %b %Y")


async def notify_extend_owner(client, bot_id, action="diperpanjang"):
    owner_bot_id = await client.db.getVars(bot_id, "owner_id")
    if not owner_bot_id:
        return
    try:
        bot_instance = client.manager.running_bots.get(bot_id)
        bot_name = bot_instance.me.first_name if bot_instance else f"ID {bot_id}"
        rows = [
            ["Bot", f"**{bot_name}**"],
            [
                "Status",
                f"Masa aktif bot Anda telah {action} oleh Owner Utama",
            ],
        ]
        await client.send_rich_message(
            owner_bot_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('party_popper')} **Kabar Baik!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )
    except Exception:
        pass


async def extend_panel_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )
    bot_id = int(callback_query.matches[0].group(1))
    text, btn = await build_extend_panel(client, bot_id)
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def extend_mode_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )
    bot_id = int(callback_query.matches[0].group(1))
    mode = callback_query.matches[0].group(2)
    text, btn = await build_extend_month_grid(client, bot_id, mode)
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


async def extend_month_callback(client, callback_query):
    if callback_query.from_user.id != client.owner_id:
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )
    bot_id = int(callback_query.matches[0].group(1))
    mode = callback_query.matches[0].group(2)
    months = int(callback_query.matches[0].group(3))
    days_to_add = months * 30 if mode == "add" else -(months * 30)

    formatted_new_date = await apply_extend_duration(client, bot_id, days_to_add)
    if mode == "add":
        title = f"{client.ns.emoji.md('white_check_mark')} **Sukses!**"
        aksi = f"`{months}` bulan (`{days_to_add}` hari)"
        action = "diperpanjang"
    else:
        title = f"{client.ns.emoji.md('white_check_mark')} **Sukses!**"
        aksi = f"`{months}` bulan (`{abs(days_to_add)}` hari)"
        action = "dikurangi"
    rows = [
        ["Bot", f"`{bot_id}`"],
        ["Aksi", f"{action.title()} masa aktif"],
        ["Jumlah", f"{aksi}"],
        ["Masa Aktif Baru", f"`{formatted_new_date}`"],
    ]
    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=(f"{title}\n\n" f"{client.ns.table.md(['Info', 'Nilai'], rows)}")
        )
    )
    await notify_extend_owner(client, bot_id, action)


async def broadcast_owners_handler(client, message):
    broadcast_msg = client.ns.telegram.arg.getMessage(message)
    if not broadcast_msg:
        rows = [
            [
                "Gunakan",
                "`/broadcast_owners <pesan>` atau balas ke sebuah pesan",
            ],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Format Salah**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            )
        )
    all_bots_data = await client.db.getBots(is_token=True)
    owner_ids = set()
    for bot in all_bots_data:
        owner_id = await client.db.getVars(int(bot["name"]), "owner_id")
        if owner_id:
            owner_ids.add(owner_id)
    if not owner_ids:
        empty_rows = [
            ["Jumlah Pemilik Bot", "`0`"],
            ["Status", "Tidak ada pemilik bot terdaftar"],
        ]
        return await message.reply_rich(
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Broadcast ke Pemilik "
                    "Bot**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], empty_rows)}"
                )
            )
        )

    total_owners = len(owner_ids)
    rows = [
        ["Status", "Siaran dimulai"],
        ["Jumlah", f"`{total_owners}` pengguna"],
    ]
    progress_msg = await message.reply_rich(
        pyrogram.types.InputRichMessage(
            markdown=(
                f"{client.ns.emoji.md('white_check_mark')} **Memulai Siaran**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
    )
    success_count = 0
    fail_count = 0
    for owner_id in owner_ids:
        try:
            await broadcast_msg.copy(owner_id)
            success_count += 1
        except Exception as e:
            client.log.print(
                f"{client.log.RED}Gagal broadcast ke owner {owner_id}: {e}"
            )
            fail_count += 1
        await asyncio.sleep(0.2)

    rows = [
        ["Status", "Selesai"],
        ["Terkirim", f"`{success_count}`"],
        ["Gagal", f"`{fail_count}`"],
    ]
    await progress_msg.edit(
        rich_message=pyrogram.types.InputRichMessage(
            markdown=f"**{client.ns.emoji.md('loudspeaker')} Siaran Selesai!**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
        )
    )


class AdminBotControl(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_message(
            filters.command("extend") & filters.user(self.client.owner_id)
        )(self.handle(extend_command_handler))
        self.client.on_callback_query(filters.regex("^extend_panel_(\\d+)$"))(
            self.handle(extend_panel_callback)
        )
        self.client.on_callback_query(filters.regex("^extend_mode_(\\d+)_(add|sub)$"))(
            self.handle(extend_mode_callback)
        )
        self.client.on_callback_query(
            filters.regex("^extend_month_(\\d+)_(add|sub)_(\\d+)$")
        )(self.handle(extend_month_callback))
        self.client.on_message(
            filters.command("broadcast_owners") & filters.user(self.client.owner_id)
        )(self.handle(broadcast_owners_handler))
