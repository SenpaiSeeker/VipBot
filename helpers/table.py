from __future__ import annotations

import html
import re

import pyrogram

_ALIAS_COUNTER = 0

_BUTTON_RE = re.compile(r"\[\[(.+?)\]\]")

# style yang dipakai -> style yang dikirim ke Telegram
_BUTTON_STYLES = {
    "blue": "primary",
    "green": "success",
    "red": "danger",
    "link": "link",
}

# tipe tombol -> (atribut, tipe Telegram)
_BUTTON_TYPES = {
    "url": ("url", "url"),
    "callback_data": ("data", "callback_data"),
    "user": ("url", "url"),
}


class TableBuilder:
    def md(self, headers, rows, aligns=None):
        headers = list(headers)
        lines = [
            "| " + " | ".join(str(header) for header in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        return "\n".join(lines)

    def photo_block(self, photo, alias: str | None = None, markdown_text: str = ""):
        global _ALIAS_COUNTER

        if alias is None:
            _ALIAS_COUNTER += 1
            alias = f"photo_{_ALIAS_COUNTER}"

        markdown = f"![{markdown_text or 'foto'}](tg://photo?id={alias})"
        return markdown, [
            pyrogram.types.InputRichMessageMedia(
                id=alias,
                media=pyrogram.types.InputMediaPhoto(media=photo),
            )
        ]

    def rich_photo(self, photo=None, markdown: str = "", alias: str | None = None):
        if not photo:
            return pyrogram.types.InputRichMessage(markdown=markdown)

        link, media = self.photo_block(photo, alias=alias)
        return pyrogram.types.InputRichMessage(
            markdown=f"{link}\n\n{markdown}", media=media
        )

    def parse_button(self, entry: str) -> str | None:
        parts = [part.strip() for part in entry.split("|")]
        label = parts[0]
        if not label:
            return None

        btn_type = payload = None
        style = "blue"
        unknown = False

        for part in parts[1:]:
            key, _, value = part.partition("=")
            key, value = key.strip().lower(), value.strip()
            if not value:
                continue
            if key == "style":
                style = value.lower()
            elif key == "type":
                if value.lower() not in _BUTTON_TYPES:
                    return None
                btn_type = value.lower()
            elif key in _BUTTON_TYPES:
                btn_type = key
                payload = f"tg://user?id={value}" if key == "user" else value
            else:
                unknown = True

        if unknown:
            return None

        btn_type = btn_type or "callback_data"
        if payload is None:
            if btn_type != "callback_data":
                return None
            payload = label

        attr, tg_type = _BUTTON_TYPES[btn_type]
        return (
            f'<tg-button type="{tg_type}" {attr}="{html.escape(payload, quote=True)}" '
            f'style="{_BUTTON_STYLES.get(style, "primary")}">'
            f"{html.escape(label, quote=False)}</tg-button>"
        )

    def buttons(self, text, align: str = "center") -> str:
        rows = [
            [button for button in map(self.parse_button, _BUTTON_RE.findall(line)) if button]
            for line in str(text).strip().splitlines()
        ]
        rows = [row for row in rows if row]
        if not rows:
            return ""

        return "\n".join(
            [f'<tg-button-row align="{align}">']
            + [button for row in rows for button in row]
            + ["</tg-button-row>"]
        )