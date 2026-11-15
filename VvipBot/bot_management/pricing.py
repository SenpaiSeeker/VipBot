from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from helpers import parse_dt

BASE_PRICE_BOT = 100000
_TZ = ZoneInfo("Asia/Jakarta")


async def get_bot_base_price(client):
    candidates = [client.me.id]
    main_bot_id = getattr(getattr(client, "manager", None), "main_bot_id", None)
    if main_bot_id and main_bot_id not in candidates:
        candidates.append(main_bot_id)

    for bot_id in candidates:
        value = await client.db.getVars(bot_id, "bot_base_price")
        try:
            value = int(value)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value

    return BASE_PRICE_BOT


def calculate_bot_price(months, base_price=BASE_PRICE_BOT):
    try:
        months = max(1, min(12, int(months)))
    except (TypeError, ValueError):
        months = 1

    try:
        base_price = int(base_price)
    except (TypeError, ValueError):
        base_price = BASE_PRICE_BOT
    if base_price <= 0:
        base_price = BASE_PRICE_BOT

    total = base_price * months
    discount_percentage = 0

    if months >= 6:
        discount_percentage = 0.2
    elif months >= 3:
        discount_percentage = 0.1

    discount = int(total * discount_percentage)
    final_price = total - discount

    return total, discount, final_price


async def get_bot_purchase_panel(client, user_id, months=1):
    try:
        months = max(1, min(12, int(months)))
    except (TypeError, ValueError):
        months = 1

    base_price = await get_bot_base_price(client)
    total, discount, final_price = calculate_bot_price(months, base_price)

    formatted_price = f"{base_price:,}"
    formatted_total = f"{total:,}"
    formatted_discount = f"-Rp {discount:,}"
    formatted_final = f"{final_price:,}"

    discount_rows = [
        ["3+ Bulan", "`10%`"],
        ["6+ Bulan", "`20%`"],
    ]

    order_rows = [
        ["Durasi", f"**{months} bulan**"],
        ["Harga Normal", f"`Rp {formatted_total}`"],
        ["Diskon", f"`{formatted_discount}`"],
        ["Total Bayar", f"**`Rp {formatted_final}`**"],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('gem')} **Beli Akses Pembuatan Bot**\n\n"
        f"Dapatkan akses untuk membuat bot VVIP Anda sendiri dengan berlangganan.\n\n"
        f"Harga dasar: `Rp {formatted_price}/bulan`\n\n"
        f"{table.md(['Durasi', 'Diskon'], discount_rows)}\n\n"
        f"{table.md(['Item', 'Nilai'], order_rows)}"
    )

    layout = [
        [
            {
                "text": "➖",
                "callback_data": f"adjust_bot_month_{months - 1}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": f"{months} Bulan",
                "callback_data": "noop",
                "style": "blue",
            },
            {
                "text": "➕",
                "callback_data": f"adjust_bot_month_{months + 1}",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            },
        ],
        [
            {
                "text": f"Bayar via QRIS (Rp {formatted_final})",
                "callback_data": f"pay_bot_qris_{months}",
                "style": "green",
                "emoji": client.ns.emoji.id("gem"),
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": "start",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    return text, btn


async def get_bot_renewal_panel(client, bot_id, months=1):
    bot_id = int(bot_id)
    try:
        months = max(1, min(12, int(months)))
    except (TypeError, ValueError):
        months = 1

    base_price = await get_bot_base_price(client)
    total, discount, final_price = calculate_bot_price(months, base_price)

    bot_name = f"ID {bot_id}"
    bot_instance = client.manager.running_bots.get(bot_id)
    if bot_instance and bot_instance.me:
        bot_name = bot_instance.me.first_name

    current_expiry = parse_dt(await client.db.getVars(bot_id, "bot_expiration_date"))
    now = datetime.now(timezone.utc)
    start_date = current_expiry if current_expiry and current_expiry > now else now
    new_expiry = start_date + timedelta(days=30 * months)

    current_expiry_text = (
        current_expiry.astimezone(_TZ).strftime("%d-%m-%Y %H:%M WIB")
        if current_expiry
        else "Belum diatur"
    )
    new_expiry_text = new_expiry.astimezone(_TZ).strftime("%d-%m-%Y %H:%M WIB")

    formatted_total = f"{total:,}"
    formatted_discount = f"-Rp {discount:,}"
    formatted_final = f"{final_price:,}"

    rows = [
        ["Bot", f"**{bot_name}** (`{bot_id}`)"],
        ["Durasi", f"**{months} bulan**"],
        ["Masa Aktif Saat Ini", f"`{current_expiry_text}`"],
        ["Masa Aktif Baru", f"`{new_expiry_text}`"],
        ["Harga Normal", f"`Rp {formatted_total}`"],
        ["Diskon", f"`{formatted_discount}`"],
        ["Total Bayar", f"**`Rp {formatted_final}`**"],
    ]

    table = client.ns.table
    text = (
        f"{client.ns.emoji.md('repeat')} **Perpanjang Bot**\n\n"
        f"Perpanjang masa aktif bot Anda dengan pembayaran QRIS.\n\n"
        f"{table.md(['Info', 'Nilai'], rows)}"
    )

    layout = [
        [
            {
                "text": "➖",
                "callback_data": f"adjust_renew_month_{bot_id}_{months - 1}",
                "style": "red",
                "emoji": client.ns.emoji.id("minus"),
            },
            {
                "text": f"{months} Bulan",
                "callback_data": "noop",
                "style": "blue",
            },
            {
                "text": "➕",
                "callback_data": f"adjust_renew_month_{bot_id}_{months + 1}",
                "style": "green",
                "emoji": client.ns.emoji.id("plus"),
            },
        ],
        [
            {
                "text": f"Bayar via QRIS (Rp {formatted_final})",
                "callback_data": f"pay_bot_renew_qris_{bot_id}_{months}",
                "style": "green",
                "emoji": client.ns.emoji.id("gem"),
            }
        ],
        [
            {
                "text": "• Kembali •",
                "callback_data": f"manage_bot {bot_id}",
                "style": "blue",
                "emoji": client.ns.emoji.id("back_arrow"),
            }
        ],
    ]

    btn = client.ns.telegram.button.build_button_grid(layout)
    return text, btn
