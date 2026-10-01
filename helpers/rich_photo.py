from __future__ import annotations

import pyrogram

_ALIAS_COUNTER = 0


def photo_block(photo, alias: str | None = None, markdown_text: str = ""):
    """Markdown pengait foto untuk rich message.

    Mengembalikan tuple ``(markdown, media)`` di mana ``markdown`` adalah
    ``![label](tg://photo?id=alias)`` yang harus dipasangkan dengan ``media``
    berisi ``InputRichMessageMedia``.
    """
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


def rich(photo=None, markdown: str = "", alias: str | None = None):
    """Bangun ``InputRichMessage`` dengan foto opsional tertanam di markdown."""
    if not photo:
        return pyrogram.types.InputRichMessage(markdown=markdown)

    link, media = photo_block(photo, alias=alias)
    return pyrogram.types.InputRichMessage(markdown=f"{link}\n\n{markdown}", media=media)
