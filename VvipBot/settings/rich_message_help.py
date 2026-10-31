import pyrogram
from pyrogram import filters

from helpers.modules import Modules

from .. import is_bot_owner


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


async def rich_message_help_callback(client, callback_query):
    if not await is_bot_owner(client, callback_query.from_user.id):
        return await callback_query.answer(
            "🚫 Anda tidak memiliki akses ke menu ini.",
            show_alert=True,
        )

    table = client.ns.table
    rich_message_rows = [
        ["Input", "Disimpan dari `ask_text_msg.text.markdown`"],
        ["Teks", "Format dari Telegram otomatis dipertahankan"],
        ["Blok", "Heading, list, tabel, kutipan, footnote, rumus"],
        ["Tombol", "Gunakan `[[...]]`"],
        ["Render", "Dikirim sebagai `InputRichMessage(markdown=...)`"],
    ]

    block_rows = [
        ["Heading", "`# Heading 1` sampai `###### Heading 6`"],
        ["List", "`- item`, `* item`, `+ item`, `1. item`"],
        ["Task list", "`- [ ] belum`, `- [x] selesai`"],
        ["Kutipan", "`> teks kutipan`"],
        ["Garis pemisah", "`---`"],
        ["Footnote", "`[^1]` dan definisi `[^1]: isi catatan`"],
        ["Tabel", "Gunakan template di bawah"],
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
        ["Tabel", "Sel hanya mendukung inline formatting, maksimal 20 kolom"],
        ["Batas", "32.768 karakter, 500 blok, 16 level nesting, 50 media"],
        ["Tombol", "`[[...]]` otomatis dirender di teks start"],
        [
            "Teks start",
            "Markdown teks, blok, dan tombol bisa dipakai di menu Atur Teks Start",
        ],
    ]

    content = (
        f"{client.ns.emoji.md('open_book')} **Panduan Rich Message**\n\n"
        f"{table.md(['Info', 'Nilai'], [['Format', 'Rich message Markdown'], ['Input', '`text.markdown`'], ['Tombol', '`[[...]]`'], ['Batas', '32.768 karakter, 500 blok, 20 kolom, 50 media']])}\n\n"
        f"**1. Rich Message**\n\n"
        f"{table.md(['Topik', 'Keterangan'], rich_message_rows)}\n\n"
        f"**2. Blok & Struktur**\n\n"
        f"{table.md(['Blok', 'Sintaks'], block_rows)}\n\n"
        f"Template tabel:\n"
        f"```\n"
        f"| Header 1 | Header 2 | Header 3 |\n"
        f"| --- | --- | --- |\n"
        f"| Isi 1 | Isi 2 | Isi 3 |\n"
        f"```\n\n"
        f"Ganti teks Header dan Isi sesuai kebutuhan.\n\n"
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


class SettingsRichMessageHelp(Modules):
    def __init__(self, client):
        super().__init__(client)
        self.client.on_callback_query(filters.regex("^rich_message_help$"))(
            self.handle(rich_message_help_callback)
        )
