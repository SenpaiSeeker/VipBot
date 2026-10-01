from __future__ import annotations

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
