import pyrogram
from pyrogram import filters

from .. import command, is_bot_owner


def _back_button(client):
    return client.ns.telegram.button.build_button_grid(
        [
            [
                {
                    "text": "• Kembali ke Pengaturan •",
                    "callback_data": "settings",
                    "style": "blue",
                    "emoji": client.ns.emoji.id("back_arrow"),
                }
            ]
        ]
    )


@command(
    lambda ctx: filters.regex("^rich_message_help$"),
    handler_type="callback",
)
async def rich_message_help_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    table = client.ns.table
    text_style_rows = [
        ["Tebal", "`**teks**` atau `__teks__`"],
        ["Miring", "`*teks*` atau `_teks_`"],
        ["Coret", "`~~teks~~`"],
        ["Kode inline", "`` `teks` ``"],
        ["Mark", "`==teks==`"],
        ["Link", "`[teks](https://t.me)`"],
        ["Mention", "`[nama](tg://user?id=123456789)`"],
        ["Email", "`[email](mailto:user@example.com)`"],
        ["Telepon", "`[telepon](tel:+123456789)`"],
        ["Emoji premium", "`![👍](tg://emoji?id=5368324170671202286)`"],
        ["Waktu", "`![22:45 besok](tg://time?unix=1647531900&format=wDT)`"],
        ["Rumus inline", "`$x^2 + y^2$`"],
        ["Rumus blok", "`$$E = mc^2$$`"],
    ]

    block_rows = [
        ["Heading", "`# Heading 1` sampai `###### Heading 6`"],
        ["List", "`- item`, `* item`, `+ item`, `1. item`"],
        ["Task list", "`- [ ] belum`, `- [x] selesai`"],
        ["Kutipan", "`> teks kutipan`"],
        ["Garis pemisah", "`---`"],
        ["Footnote", "`[^1]` dan definisi `[^1]: isi catatan`"],
        ["Media", '`![](https://contoh.com/foto.jpg "Caption")`'],
        ["Tabel", "Lihat contoh di bawah"],
        ["Kode blok", "Lihat contoh di bawah"],
    ]

    button_rows = [
        ["Tombol URL", "Gunakan properti `url`"],
        ["Tombol callback", "Gunakan properti `callback_data`"],
        ["Style", "`link`, `red`, `blue`, atau `green`"],
        ["Default", "Style `blue` / `primary`"],
        ["Pemisah", "Gunakan karakter pipa antar properti"],
        ["Label", "Tidak boleh mengandung karakter pipa atau `]]`"],
        ["Callback", "`callback_data` harus cocok dengan handler"],
    ]

    note_rows = [
        ["Media", "Hanya URL HTTP/HTTPS dan ditulis sebagai blok terpisah"],
        ["Tabel", "Sel hanya mendukung inline formatting, maksimal 20 kolom"],
        ["Batas", "32.768 karakter, 500 blok, 16 level nesting, 50 media"],
        ["Tombol", "`[[...]]` adalah shortcut helper `TableBuilder.buttons()`"],
        [
            "Teks start",
            "Markdown teks dan blok bisa dipakai di menu Atur Teks Start",
        ],
    ]

    content = (
        f"{client.ns.emoji.md('open_book')} **Panduan Format Markdown**\n\n"
        f"{table.md(['Info', 'Nilai'], [['Format', 'Markdown rich message'], ['Dukungan', 'Heading, list, tabel, media, kutipan, footnote, rumus, dan tombol'], ['Batas', '32.768 karakter, 500 blok, 20 kolom, 50 media']])}\n\n"
        f"**1. Teks & Gaya**\n\n"
        f"{table.md(['Format', 'Sintaks'], text_style_rows)}\n\n"
        f"Spoiler: `||teks||`.\n\n"
        f"**2. Blok & Struktur**\n\n"
        f"{table.md(['Blok', 'Sintaks'], block_rows)}\n\n"
        f"Contoh tabel:\n"
        f"```\n"
        f"| Header 1 | Header 2 |\n"
        f"|:---------|:--------:|\n"
        f"| kiri     | tengah   |\n"
        f"```\n\n"
        f"Contoh kode blok:\n"
        f"```python\n"
        f"print('Hello, world!')\n"
        f"```\n\n"
        f"**3. Tombol `[[...]]`**\n\n"
        f"{table.md(['Aturan', 'Keterangan'], button_rows)}\n\n"
        f"Contoh tombol:\n"
        f"```\n"
        f"[[Buka | url=https://t.me | style=green]]\n"
        f"[[Beli | callback_data=beli | style=blue]]\n"
        f"[[Satu | callback_data=satu]] [[Dua | callback_data=dua | style=red]]\n"
        f"```\n\n"
        f"Setiap baris menjadi satu baris tombol.\n\n"
        f"**4. Catatan Penting**\n\n"
        f"{table.md(['Topik', 'Keterangan'], note_rows)}"
    )

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=content),
        reply_markup=_back_button(client),
    )
