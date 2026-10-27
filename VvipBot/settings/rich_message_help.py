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
        ["Spoiler", "`<tg-spoiler>teks</tg-spoiler>`"],
        ["Garis bawah", "`<u>teks</u>` atau `<ins>teks</ins>`"],
        ["Subscript", "`<sub>teks</sub>`"],
        ["Superscript", "`<sup>teks</sup>`"],
        ["Link", "`[teks](https://t.me)`"],
        ["Mention", "`[nama](tg://user?id=123456789)`"],
        ["Email", "`[email](mailto:user@example.com)`"],
        ["Telepon", "`[telepon](tel:+123456789)`"],
        [
            "Emoji premium",
            "`![👍](tg://emoji?id=5368324170671202286)`",
        ],
        [
            "Waktu",
            "`![22:45 besok](tg://time?unix=1647531900&format=wDT)`",
        ],
        ["Rumus inline", "`$x^2 + y^2$`"],
        ["Rumus blok", "`$$E = mc^2$$`"],
    ]

    block_rows = [
        ["Heading", "`# Heading 1` sampai `###### Heading 6`"],
        ["List", "`- item`, `* item`, `+ item`, `1. item`"],
        ["Task list", "`- [ ] belum`, `- [x] selesai`"],
        ["Kutipan", "`> teks kutipan`"],
        ["Kutipan lipat", "`<blockquote expandable>teks</blockquote>`"],
        ["Garis pemisah", "`---`"],
        ["Details", "`<details open><summary>Judul</summary>Isi</details>`"],
        ["Footnote", "`[^1]` dan definisi `[^1]: isi catatan`"],
        ["Media", '`![](https://contoh.com/foto.jpg "Caption")`'],
        ["Collage", '`<tg-collage><img src="..."/></tg-collage>`'],
        ["Slideshow", '`<tg-slideshow><img src="..."/></tg-slideshow>`'],
        ["Map", '`<tg-map lat="41.9" long="12.5" zoom="14"/>`'],
        ["Pull quote", "`<aside>Teks<cite>Penulis</cite></aside>`"],
        ["Footer", "`<footer>Teks footer</footer>`"],
    ]

    button_type_rows = [
        ["`url`", '`url="https://..."` atau `url="tg://user?id=..."`'],
        ["`callback_data`", '`data="payload"`, 1-64 byte, harus ada handler'],
        ["`web_app`", '`url="https://..."`, hanya chat pribadi'],
        ["`login_url`", '`url="https://..."`, domain harus diatur via @BotFather'],
        ["`switch_inline_query`", '`query="..."`'],
        ["`switch_inline_query_current_chat`", '`query="..."`'],
        [
            "`switch_inline_query_chosen_chat`",
            '`query="..."` + atribut allow-*',
        ],
        ["`copy_text`", '`text="teks yang disalin"`'],
        ["`disabled`", "Tombol nonaktif"],
    ]

    rule_rows = [
        ["Pemisah", "Gunakan karakter pipa untuk memisahkan label dan properti"],
        ["Tipe", "`url=...` atau `callback_data=...`"],
        ["Style", "`link`, `red`, `blue`, atau `green`"],
        ["Default", "Style `blue` / `primary`"],
        ["Baris", "Satu baris `[[...]]` menjadi satu baris tombol"],
        ["Beberapa tombol", "Beberapa `[[...]]` pada baris yang sama tampil sejajar"],
        ["Label", "Tidak boleh mengandung karakter pipa atau `]]`"],
        ["Payload", "Tidak boleh mengandung karakter pipa atau `]]`"],
        ["Style link", "Hanya untuk tombol `callback_data`"],
        ["Align", '`TableBuilder.buttons(text, align="center")`'],
    ]

    note_rows = [
        [
            "Sintaks `[[...]]`",
            "Bukan sintaks native Telegram; ini shortcut helper `TableBuilder.buttons()`",
        ],
        [
            "Teks start",
            "Untuk tombol di template `/start`, gunakan HTML `<tg-button-row>` langsung",
        ],
        [
            "Tombol callback",
            "Pastikan `callback_data` cocok dengan handler yang terdaftar",
        ],
        [
            "Media",
            "Hanya URL HTTP/HTTPS dan harus ditulis sebagai blok terpisah",
        ],
        ["Tabel", "Sel hanya mendukung inline formatting, maksimal 20 kolom"],
        ["Batas", "32.768 karakter, 500 blok, 16 level nesting, 50 media"],
        ["HTML", "Tag di luar daftar resmi Telegram tidak didukung"],
    ]

    content = (
        f"{client.ns.emoji.md('open_book')} **Panduan Format Rich Message**\n\n"
        f"{table.md(['Info', 'Nilai'], [['Mode', 'Markdown atau HTML'], ['Dukungan', 'Heading, list, tabel, media, kutipan, details, footnote, rumus, dan tombol'], ['Berlaku', 'Pesan rich message Telegram']])}\n\n"
        f"**1. Teks & Gaya**\n\n"
        f"{table.md(['Format', 'Sintaks'], text_style_rows)}\n\n"
        f"Spoiler juga bisa ditulis dengan `||teks||` di Markdown.\n\n"
        f"**2. Blok & Struktur**\n\n"
        f"{table.md(['Blok', 'Sintaks'], block_rows)}\n\n"
        f"Contoh tabel Markdown:\n"
        f"```\n"
        f"| Header 1 | Header 2 |\n"
        f"|:---------|:--------:|\n"
        f"| kiri     | tengah   |\n"
        f"```\n\n"
        f"Contoh kode blok:\n"
        f"```python\n"
        f"print('Hello, world!')\n"
        f"```\n\n"
        f"**3. Tombol HTML Rich Message**\n\n"
        f"```\n"
        f'<tg-button-row align="center">\n'
        f'  <tg-button type="url" style="success" url="https://t.me">Buka</tg-button>\n'
        f'  <tg-button type="callback_data" style="primary" data="beli">Beli</tg-button>\n'
        f"</tg-button-row>\n"
        f"```\n\n"
        f"{table.md(['Tipe', 'Atribut'], button_type_rows)}\n\n"
        f"Style tombol: `danger`, `success`, `primary`, atau `link`. Style `link` hanya untuk tombol callback. Align baris: `left`, `center`, atau `right`.\n\n"
        f"**4. Shortcut `[[...]]`**\n\n"
        f"```\n"
        f"[[Buka | url=https://t.me | style=green]]\n"
        f"[[Beli | callback_data=beli | style=blue]]\n"
        f"[[Satu | callback_data=satu]] [[Dua | callback_data=dua | style=red]]\n"
        f"```\n\n"
        f"{table.md(['Aturan', 'Keterangan'], rule_rows)}\n\n"
        f"Contoh penggunaan helper:\n"
        f"```python\n"
        f"markup = client.ns.table.buttons(\n"
        f"    '[[Buka | url=https://t.me | style=green]]',\n"
        f"    align='center',\n"
        f")\n"
        f"```\n\n"
        f"**5. Catatan Penting**\n\n"
        f"{table.md(['Topik', 'Keterangan'], note_rows)}\n\n"
        f"Tag HTML yang didukung antara lain:\n"
        f"```\n"
        f"<b> <strong> <i> <em> <u> <ins> <s> <strike> <del>\n"
        f"<code> <mark> <sub> <sup> <tg-spoiler> <a> <tg-reference>\n"
        f"<tg-emoji> <tg-time> <tg-math>\n"
        f"<h1> sampai <h6> <p> <pre> <footer> <hr/>\n"
        f"<ul> <ol> <li> <blockquote> <aside>\n"
        f"<img> <video> <audio> <tg-document> <figure> <figcaption> <cite>\n"
        f"<tg-map> <tg-collage> <tg-slideshow>\n"
        f"<table> <tr> <th> <td> <details> <summary> <tg-math-block>\n"
        f"<tg-button-row> <tg-button>\n"
        f"```"
    )

    await callback_query.edit_message_text(
        rich_message=pyrogram.types.InputRichMessage(markdown=content),
        reply_markup=_back_button(client),
    )
