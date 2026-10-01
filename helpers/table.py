from __future__ import annotations

import re
import unicodedata

_MARKDOWN_CUSTOM_EMOJI = re.compile(r"!\[([^\]]*)\]\(tg://emoji\?id=\d+\)")
_HTML_CUSTOM_EMOJI = re.compile(r"<tg-emoji emoji-id=\"\d+\">([^<]*)</tg-emoji>")
_HTML_TAG = re.compile(r"<[^>]+>")
_MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_WRAPPERS = ("**", "__", "~~", "`", "==", "||", "*", "_")
_ESC_AMP = "&amp;"
_ESC_LT = "&lt;"
_ESC_GT = "&gt;"


def _width(ch: str) -> int:
    if unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _text_width(text: str) -> int:
    return sum(_width(char) for char in str(text))


def _plain(text: str) -> str:
    text = _MARKDOWN_CUSTOM_EMOJI.sub(r"\1", str(text))
    text = _HTML_CUSTOM_EMOJI.sub(r"\1", text)
    text = _MARKDOWN_LINK.sub(r"\1", text)
    text = _HTML_TAG.sub("", text)
    for wrapper in _WRAPPERS:
        text = text.replace(wrapper, "")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&", _ESC_AMP).replace("<", _ESC_LT).replace(">", _ESC_GT)
    return text.strip()


def _truncate(text: str, width: int) -> str:
    text = str(text)
    if _text_width(text) <= width:
        return text
    out = []
    used = 0
    for char in text:
        char_width = _width(char)
        if used + char_width > width - 1:
            break
        out.append(char)
        used += char_width
    return "".join(out) + "…"


def _align(text: str, width: int, align: str) -> str:
    pad = max(0, width - _text_width(text))
    if align == "r":
        return " " * pad + text
    if align == "c":
        left = pad // 2
        return " " * left + text + " " * (pad - left)
    return text + " " * pad


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

    def caption(self, headers, rows, aligns=None, max_width=40, max_chars=1000):
        aligns = aligns or ["l"] * len(headers)
        rows = [list(row) for row in rows]

        if max_chars:
            while True:
                block = self._caption_block(headers, rows, aligns, max_width)
                if len(block) <= max_chars:
                    return block
                if len(rows) > 1:
                    rows = rows[: max(1, len(rows) - 1)]
                    continue
                if max_width > 8:
                    max_width -= 4
                    continue
                break
            return self._caption_block(headers, rows, aligns, 8)

        return self._caption_block(headers, rows, aligns, max_width)

    def caption_bundle(self, headers, rows, aligns=None, max_width=40, max_chars=1000, reserved=0):
        return self.caption(
            headers,
            rows,
            aligns,
            max_width=max_width,
            max_chars=max(200, max_chars - reserved),
        )

    def _caption_block(self, headers, rows, aligns, max_width):
        cells = [[_plain(header) for header in headers]]
        cells += [[_plain(cell) for cell in row] for row in rows]

        widths = [
            max(1, min(max_width, max(_text_width(_truncate(cell, max_width)) for cell in column)))
            for column in zip(*cells)
        ]

        def border(left, mid, right):
            return left + mid.join("─" * (width + 2) for width in widths) + right

        def row_line(row, align_default):
            cells_padded = [
                _align(
                    _truncate(row[index], widths[index]),
                    widths[index],
                    align_default if align_default else aligns[index],
                )
                for index in range(len(row))
            ]
            return "│ " + " │ ".join(cells_padded) + " │"

        lines = [
            border("┌", "┬", "┐"),
            row_line(cells[0], "c"),
            border("├", "┼", "┤"),
        ]
        for row in cells[1:]:
            lines.append(row_line(row, False))
        lines.append(border("└", "┴", "┘"))
        return "<pre>" + "\n".join(lines) + "</pre>"
