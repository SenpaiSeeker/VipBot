import random

import pyfiglet


class Gradient:
    def __init__(self):
        self.figlet = pyfiglet.Figlet(font="slant")
        self.start_color = self.random_color()
        self.end_color = self.random_color()

    @staticmethod
    def random_color():
        return tuple(random.randint(128, 255) for _ in range(3))

    @staticmethod
    def _rgb_to_256_ansi_index(r, g, b):
        if r == g == b:
            if r < 8:
                return 16
            if r > 248:
                return 231
            return round(((r - 8) / 247) * 24) + 232
        r_idx = int(round(r / 255 * 5))
        g_idx = int(round(g / 255 * 5))
        b_idx = int(round(b / 255 * 5))
        return 16 + (36 * r_idx) + (6 * g_idx) + b_idx

    def rgb_to_ansi(self, r, g, b):
        return f"\033[38;5;{self._rgb_to_256_ansi_index(r, g, b)}m"

    def interpolate_color(self, factor):
        def _channel(start, end):
            return max(0, min(255, int(start + (end - start) * factor)))

        return tuple(
            _channel(s, e)
            for s, e in zip(self.start_color, self.end_color)
        )

    def render_text(self, text):
        rendered = self.figlet.renderText(text)
        chars = []
        for i, char in enumerate(rendered):
            factor = i / max(len(rendered) - 1, 1)
            r, g, b = self.interpolate_color(factor)
            chars.append(f"{self.rgb_to_ansi(r, g, b)}{char}")
        print("".join(chars) + "\033[0m")