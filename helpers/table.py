from __future__ import annotations

import pyrogram

_ALIAS_COUNTER = 0

_ALIGN_MARKDOWN = {"l": ":---", "c": ":---:", "r": "---:"}


class TableBuilder:
    def md(self, headers, rows, aligns=None):
        aligns = aligns or ["l"] * len(headers)
        lines = [
            "| " + " | ".join(str(header) for header in headers) + " |",
            "| " + " | ".join(_ALIGN_MARKDOWN[align] for align in aligns) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        return "\n".join(lines)
    def photo_block(self, photo, alias: str | None = None, markdown_text: str = ""):

        import pyrogram

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
        import pyrogram

        if not photo:
            return pyrogram.types.InputRichMessage(markdown=markdown)

        link, media = self.photo_block(photo, alias=alias)
        return pyrogram.types.InputRichMessage(markdown=f"{link}\n\n{markdown}", media=media)
