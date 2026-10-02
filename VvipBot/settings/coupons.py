import asyncio
from datetime import datetime, timedelta, timezone

import pyrogram
from pyrogram import filters

from helpers import parse_dt

from .. import command, ctx, is_bot_owner, listen


@command(
    lambda ctx: filters.regex("^manage_coupons"),
    handler_type="callback",
)
async def manage_coupons_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    menu_rows = [
        ["Buat Kupon Baru", "Tambah kode diskon"],
        ["Lihat Kupon", "Daftar kupon aktif"],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('ticket_admit')} **Manajemen Kupon**\n\n"
        f"{table.md(['Menu', 'Fungsi'], menu_rows)}"
    )
    layout = [
        [
            {
                "text": "➕ Buat Kupon Baru",
                "callback_data": "add_coupon",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            }
        ],
        [
            {
                "text": "📋 Lihat Kupon",
                "callback_data": "list_coupons_0",
                "style": "blue",
                "emoji": client.ns.emoji.id("open_book"),
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": "settings",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]
    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


@command(
    lambda ctx: filters.regex("^add_coupon"),
    handler_type="callback",
)
async def add_coupon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    try:

        def ask(text):
            return client.ask(
                chat_id,
                f"{text}\n\nKetik `/batal` untuk membatalkan.",
                timeout=600,
            )

        code = (
            await ask("**1/4:** Masukkan kode kupon unik (misal: `DISKONBARU`).")
        ).text.upper()

        type_msg = await ask(
            "**2/4:** Pilih tipe diskon:\n1. Persentase (%)\n2. Potongan Harga Tetap"
        )
        discount_type = "percentage" if "1" in type_msg.text else "fixed"

        value_prompt = (
            "**3/4:** Masukkan nilai persentase."
            if discount_type == "percentage"
            else "**3/4:** Masukkan jumlah potongan harga."
        )
        discount_value = int((await ask(value_prompt)).text)

        uses_left = int(
            (await ask("**4/4:** Berapa kali kupon ini bisa digunakan?")).text
        )

        expiry_days_msg = await ask("**5/5:** Berapa hari kupon ini akan berlaku?")
        expiry_days = int(expiry_days_msg.text)

        expiry_date = (
            (datetime.now(timezone.utc) + timedelta(days=expiry_days)).isoformat()
            if expiry_days > 0
            else None
        )

        coupon_data = {
            "code": code,
            "discount_type": discount_type,
            "discount_value": discount_value,
            "uses_left": uses_left,
            "expiry_date": expiry_date,
        }

        await ctx.db.setListVars(client.me.id, "coupons", coupon_data)

        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('white_check_mark')} Kupon `{code}` berhasil dibuat."
            ),
        )

    except (listen.UserCancelled, asyncio.TimeoutError, ValueError):
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=f"{client.ns.emoji.md('cross_mark')} **Proses Dibatalkan**"
            ),
        )


@command(
    lambda ctx: filters.regex("^list_coupons_(\\d+)"),
    handler_type="callback",
)
async def list_coupons_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    page = int(callback_query.data.split("_")[2])
    coupons = await ctx.db.getListVars(client.me.id, "coupons") or []

    back_row = [
        {
            "text": "• Kembali •",
            "callback_data": "manage_coupons",
            "style": "blue",
            "emoji": client.ns.emoji.id("back_arrow"),
        }
    ]

    if not coupons:
        empty_rows = [["Jumlah Kupon", "`0`"], ["Status", "Belum ada kupon"]]
        table = client.ns.table
        text = (
            f"{client.ns.emoji.md('ticket_admit')} **Daftar Kupon**\n\n"
            f"{table.md(['Info', 'Nilai'], empty_rows)}"
        )
        btn = client.ns.telegram.button.build_button_grid([back_row])
        await callback_query.edit_message_text(
            rich_message=pyrogram.types.InputRichMessage(markdown=text),
            reply_markup=btn,
        )
        return

    total_pages = len(coupons)
    page = max(0, min(page, total_pages - 1))
    coupon = coupons[page]

    expiry_text = "Permanent"
    coupon_expiry = parse_dt(coupon.get("expiry_date"))
    if coupon_expiry:
        expiry_text = coupon_expiry.strftime("%d %b %Y")

    detail_rows = [
        ["Kode", f"`{coupon['code']}`"],
        ["Tipe", f"`{coupon['discount_type']}`"],
        ["Nilai", f"`{coupon['discount_value']}`"],
        ["Sisa Penggunaan", f"`{coupon['uses_left']}`"],
        ["Berlaku hingga", f"`{expiry_text}`"],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('pencil')} **Detail Kupon ({page + 1}/{total_pages})**\n\n"
        f"{table.md(['Info', 'Isi'], detail_rows)}"
    )

    layout = []
    pagination_row = []

    if total_pages > 1:
        prev_page = (page - 1 + total_pages) % total_pages
        next_page = (page + 1) % total_pages if page + 1 < total_pages else page

        pagination_row.extend(
            [
                {
                    "text": "«",
                    "callback_data": f"list_coupons_{prev_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                },
                {
                    "text": "»",
                    "callback_data": f"list_coupons_{next_page}",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("right_pointing"),
                },
            ]
        )

    layout.append(
        [
            {
                "text": "🗑️ Hapus Kupon Ini",
                "callback_data": f"delete_coupon {coupon['code']} {page}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            }
        ]
    )

    if pagination_row:
        layout.append(pagination_row)
    layout.append(back_row)

    btn = client.ns.telegram.button.build_button_grid(layout)

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=text),
        reply_markup=btn,
    )


@command(
    lambda ctx: filters.regex("^delete_coupon\\s(.+)\\s(\\d+)"),
    handler_type="callback",
)
async def delete_coupon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    _, code, page_str = callback_query.data.split()
    coupons = await ctx.db.getListVars(client.me.id, "coupons") or []
    coupon_to_remove = next((c for c in coupons if c.get("code") == code), None)

    if coupon_to_remove:
        await ctx.db.removeListVars(client.me.id, "coupons", coupon_to_remove)
        await callback_query.answer("Kupon berhasil dihapus.", show_alert=True)

    new_page = int(page_str)
    remaining_coupons = await ctx.db.getListVars(client.me.id, "coupons") or []

    if new_page >= len(remaining_coupons) and len(remaining_coupons) > 0:
        new_page = len(remaining_coupons) - 1

    callback_query.data = f"list_coupons_{new_page}"
    await list_coupons_callback(client, callback_query)
