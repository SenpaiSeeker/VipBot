BASE_PRICE_BOT = 100000


def calculate_bot_price(months):
    total = BASE_PRICE_BOT * months
    discount_percentage = 0

    if months >= 6:
        discount_percentage = 0.2
    elif months >= 3:
        discount_percentage = 0.1

    discount = int(total * discount_percentage)
    final_price = total - discount

    return total, discount, final_price


async def get_bot_purchase_panel(client, user_id, months=1):
    total, discount, final_price = calculate_bot_price(months)

    formatted_price = f"{BASE_PRICE_BOT:,}"
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

    discount_caption = table.caption(['Durasi', 'Diskon'], discount_rows)
    caption_head = (
        f"{client.ns.emoji.html('gem')} <b>Beli Akses Pembuatan Bot</b>\n\n"
        f"Harga dasar: <code>Rp {formatted_price}/bulan</code>\n\n"
        f"{discount_caption}\n\n"
    )
    caption_text = caption_head + table.caption_bundle(
        ['Item', 'Nilai'],
        order_rows,
        max_chars=1024,
        reserved=len(caption_head) + len("<pre></pre>"),
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
    return text, caption_text, btn
