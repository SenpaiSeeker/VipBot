import asyncio
import re
from datetime import datetime, timedelta, timezone

import pyrogram
from pyrogram import filters

from helpers import parse_dt
from helpers.modules import Modules

from .. import is_bot_owner, listen

_COUPON_CODE_RE = re.compile(r"^[A-Z0-9_-]{1,32}$")


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


async def add_coupon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    chat_id = callback_query.from_user.id
    await callback_query.message.delete()

    try:

        async def ask_value(prompt):
            answer = await ask(prompt)
            value = (answer.text or "").strip()
            if value.lower() == "/batal":
                raise listen.UserCancelled
            return value

        def ask(text):
            return client.ask(
                chat_id,
                f"{text}\n\nKetik `/batal` untuk membatalkan.",
                timeout=600,
            )

        rows = [["Contoh", "Kode kupon unik (misal: `DISKONBARU`)"]]
        code = (
            await ask_value(
                f"**1/4: Masukkan Kode Kupon**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        ).upper()

        if not _COUPON_CODE_RE.fullmatch(code):
            raise ValueError(
                "Kode kupon hanya boleh berisi huruf, angka, `_`, atau `-` "
                "(maksimal 32 karakter)."
            )

        existing_coupons = await client.db.getListVars(client.me.id, "coupons") or []
        if any(
            str(coupon.get("code", "")).upper() == code for coupon in existing_coupons
        ):
            raise ValueError("Kode kupon sudah digunakan.")

        rows = [
            ["1", "Persentase (%)"],
            ["2", "Potongan Harga Tetap"],
        ]
        type_text = await ask_value(
            f"**2/4: Pilih Tipe Diskon**\n\n"
            f"{client.ns.table.md(['Opsi', 'Keterangan'], rows)}"
        )
        if type_text not in {"1", "2"}:
            raise ValueError("Tipe diskon harus `1` atau `2`.")
        discount_type = "percentage" if type_text == "1" else "fixed"

        value_example = (
            "Masukkan nilai persentase (1-100)"
            if discount_type == "percentage"
            else "Masukkan jumlah potongan harga"
        )
        rows = [["Isi", value_example]]
        value_prompt = (
            f"**3/4: Nilai Diskon**\n\n"
            f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
        )
        discount_value = int(await ask_value(value_prompt))

        if discount_type == "percentage":
            if not 1 <= discount_value <= 100:
                raise ValueError("Persentase diskon harus antara 1 sampai 100.")
        elif discount_value <= 0:
            raise ValueError("Potongan harga harus lebih dari 0.")

        rows = [["Isi", "Berapa kali kupon ini bisa digunakan?"]]
        uses_left = int(
            await ask_value(
                f"**4/4: Batas Penggunaan**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
        if uses_left <= 0:
            raise ValueError("Batas penggunaan harus lebih dari 0.")

        rows = [["Isi", "Berapa hari kupon ini akan berlaku?"]]
        expiry_days = int(
            await ask_value(
                f"**5/5: Masa Berlaku**\n\n"
                f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
            )
        )
        if expiry_days < 0:
            raise ValueError("Masa berlaku tidak boleh negatif.")

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

        await client.db.setListVars(client.me.id, "coupons", coupon_data)

        rows = [
            ["Kode", f"`{code}`"],
            ["Status", "Aktif"],
        ]
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('white_check_mark')} **Kupon "
                    "Berhasil Dibuat!**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )

    except (listen.UserCancelled, asyncio.TimeoutError, ValueError):
        rows = [
            ["Status", "Dibatalkan"],
            ["Keterangan", "Pembuatan kupon dibatalkan"],
        ]
        await client.send_rich_message(
            chat_id,
            pyrogram.types.InputRichMessage(
                markdown=(
                    f"{client.ns.emoji.md('cross_mark')} **Proses "
                    "Dibatalkan**\n\n"
                    f"{client.ns.table.md(['Info', 'Nilai'], rows)}"
                )
            ),
        )


async def list_coupons_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    page = int(callback_query.data.split("_")[2])
    coupons = await client.db.getListVars(client.me.id, "coupons") or []

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
        f"{client.ns.emoji.md('pencil')} **Detail Kupon "
        f"({page + 1}/{total_pages})**\n\n"
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


async def delete_coupon_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return

    _, code, page_str = callback_query.data.split()
    coupons = await client.db.getListVars(client.me.id, "coupons") or []
    coupon_to_remove = next((c for c in coupons if c.get("code") == code), None)

    if coupon_to_remove:
        await client.db.removeListVars(client.me.id, "coupons", coupon_to_remove)
        await callback_query.answer("Kupon berhasil dihapus.", show_alert=True)

    new_page = int(page_str)
    remaining_coupons = await client.db.getListVars(client.me.id, "coupons") or []

    if new_page >= len(remaining_coupons) and len(remaining_coupons) > 0:
        new_page = len(remaining_coupons) - 1

    callback_query.data = f"list_coupons_{new_page}"
    await list_coupons_callback(client, callback_query)


class SettingsCoupons(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^manage_coupons"))(
            self.handle(manage_coupons_callback)
        )
        self.client.on_callback_query(filters.regex("^add_coupon"))(
            self.handle(add_coupon_callback)
        )
        self.client.on_callback_query(filters.regex("^list_coupons_(\\d+)"))(
            self.handle(list_coupons_callback)
        )
        self.client.on_callback_query(filters.regex("^delete_coupon\\s(.+)\\s(\\d+)"))(
            self.handle(delete_coupon_callback)
        )
