from __future__ import annotations

import html
import re

import pyrogram

_ALIAS_COUNTER = 0

_BUTTON_ENTRY_RE = re.compile(r"\[\[(.+?)\]\]")

_BUTTON_STYLE_MAP = {
    "blue": "primary",
    "primary": "primary",
    "green": "success",
    "success": "success",
    "red": "danger",
    "danger": "danger",
    "link": "link",
}

_BUTTON_TYPE_MAP = {
    "url": "url",
    "link": "url",
    "query": "callback_data",
    "callback": "callback_data",
    "callback_data": "callback_data",
    "data": "callback_data",
    "user": "url",
    "user_id": "url",
    "mention": "url",
}

_DEFAULT_BUTTON_STYLE = "blue"


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

    def parse_button(self, entry: str):
        parts = [part.strip() for part in str(entry).split("|")]
        label = html.escape(parts[0], quote=False)
        if not label:
            return None

        btn_type = None
        payload = None
        style = _DEFAULT_BUTTON_STYLE
        has_unknown = False

        for part in parts[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key = key.strip().lower()
            value = value.strip()

            if not value:
                continue
            if key == "style":
                style = value
            elif key == "type":
                btn_type = _BUTTON_TYPE_MAP.get(value.lower())
            elif key in ("url", "link"):
                btn_type, payload = "url", value
            elif key in ("query", "callback", "callback_data", "data"):
                btn_type, payload = "callback_data", value
            elif key in ("user", "user_id", "mention"):
                btn_type, payload = "url", f"tg://user?id={value}"
            else:
                has_unknown = True

        if payload is None:
            if has_unknown or btn_type not in (None, "callback_data"):
                return None
            btn_type = "callback_data"
            payload = label

        style_name = _BUTTON_STYLE_MAP.get(style.lower(), "primary")
        attr = "data" if btn_type == "callback_data" else "url"
        payload = html.escape(payload, quote=True)

        return (
            f'<tg-button type="{btn_type}" {attr}="{payload}" '
            f'style="{style_name}">{label}</tg-button>'
        )

    def buttons(self, text, align: str = "center"):
        rows = []
        for line in str(text).strip().splitlines():
            row = [
                button
                for button in (
                    self.parse_button(entry)
                    for entry in _BUTTON_ENTRY_RE.findall(line)
                )
                if button
            ]
            if row:
                rows.append(row)

        if not rows:
            return ""

        lines = [f'<tg-button-row align="{align}">']
        for row in rows:
            lines.extend(row)
        lines.append("</tg-button-row>")
        return "\n".join(lines)