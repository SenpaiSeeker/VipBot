import re

_PLACEHOLDER_RE = re.compile(r"\{([a-z0-9_]+)\}")

INCOME_TEMPLATE_VARIABLES = [
    ("{mention}", "Mention pembeli (bisa diklik)"),
    ("{buyer_name}", "Nama lengkap pembeli"),
    ("{buyer_id}", "ID Telegram pembeli"),
    ("{buyer_username}", "Username pembeli (tanpa @)"),
    ("{order_id}", "ID transaksi"),
    ("{status}", "Status pembayaran"),
    ("{type}", "Tipe paket (Normal/Promo/Bundle)"),
    ("{quantity}", "Jumlah paket yang dibeli"),
    ("{item_name}", "Nama paket (digabung bila banyak)"),
    ("{item_price}", "Harga paket"),
    ("{item_duration}", "Durasi paket"),
    ("{item_chat_id}", "Chat ID paket"),
    ("{item_list}", "Daftar semua paket (multi-baris)"),
    ("{item_table}", "Tabel markdown semua paket"),
    ("{subtotal}", "Subtotal sebelum diskon"),
    ("{discount}", "Jumlah diskon kupon"),
    ("{coupon}", "Kode kupon (atau '-')"),
    ("{total}", "Total bayar"),
    ("{method}", "Metode pembayaran"),
    ("{time}", "Waktu transaksi (WIB)"),
    ("{bot_name}", "Nama bot"),
    ("{bot_username}", "Username bot (tanpa @)"),
    ("{bot_mention}", "Mention bot (bisa diklik)"),
    ("{sold_count}", "Jumlah item terjual"),
]


def render_income_template(template: str, values: dict) -> str:
    def replace(match):
        key = match.group(1)
        if key in values:
            return str(values[key])
        return match.group(0)

    return _PLACEHOLDER_RE.sub(replace, template)
