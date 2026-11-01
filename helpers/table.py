from __future__ import annotations

import html
import re

import pyrogram

from .patcher import Object

_ALIAS_COUNTER = 0

_BUTTON_ENTRY_RE = re.compile(r"\[\[(.+?)\]\]")

_BUTTON_TYPES = {"url": "url", "callback_data": "data"}

_BUTTON_STYLES = {
    "link": "link",
    "red": "danger",
    "blue": "primary",
    "green": "success",
}

_DEFAULT_STYLE = "primary"

_BUTTON_PAD = "\u2800" * 8


class TableBuilder(Object):
    _ns_alias = "table"

    def md(self, headers, rows) -> str:
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
        parts = [part.strip() for part in str(entry).split("|")]
        label = parts[0]
        btn_type = payload = None
        style = _DEFAULT_STYLE

        for part in parts[1:]:
            key, _, value = part.partition("=")
            key, value = key.strip().lower(), value.strip()

            if not value:
                continue
            if key == "style":
                style = _BUTTON_STYLES.get(value, _DEFAULT_STYLE)
            elif key in _BUTTON_TYPES:
                btn_type, payload = key, value

        if not label or not payload:
            return None

        attr = _BUTTON_TYPES[btn_type]
        return (
            f'<tg-button type="{btn_type}" {attr}="{html.escape(payload, quote=True)}"'
            f' style="{style}">{_BUTTON_PAD}{html.escape(label, quote=False)}'
            f"{_BUTTON_PAD}</tg-button>"
        )

    def buttons(self, text, align: str = "center") -> str:
        blocks = []
        for line in str(text).strip().splitlines():
            row = [
                button
                for button in map(self.parse_button, _BUTTON_ENTRY_RE.findall(line))
                if button
            ]
            if row:
                body = "\n".join(row)
                blocks.append(
                    f'<tg-button-row align="{align}">\n{body}\n</tg-button-row>'
                )

        return "\n".join(blocks)

    def render_buttons(self, text, align: str = "center"):
        raw = str(text or "")
        markup = self.buttons(raw, align=align)
        if not markup:
            return raw, ""

        lines = [_BUTTON_ENTRY_RE.sub("", line).rstrip() for line in raw.splitlines()]
        cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines).strip())
        return cleaned, markup


Table = TableBuilder
