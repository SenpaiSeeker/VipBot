import random

_COLOR_CODES = {
    "BLACK": "\033[1;38;5;16m",
    "RED": "\033[1;38;5;196m",
    "GREEN": "\033[1;38;5;46m",
    "YELLOW": "\033[1;38;5;226m",
    "BLUE": "\033[1;38;5;21m",
    "MAGENTA": "\033[1;38;5;201m",
    "CYAN": "\033[1;38;5;51m",
    "WHITE": "\033[1;38;5;231m",
    "ORANGE": "\033[1;38;5;208m",
    "PINK": "\033[1;38;5;206m",
    "GRAY": "\033[1;38;5;244m",
    "BROWN": "\033[1;38;5;94m",
    "AQUA": "\033[1;38;5;123m",
    "PURPLE": "\033[1;38;5;93m",
    "GOLD": "\033[1;38;5;220m",
    "SILVER": "\033[1;38;5;250m",
    "INDIGO": "\033[1;38;5;54m",
    "TEAL": "\033[1;38;5;30m",
    "CRIMSON": "\033[1;38;5;160m",
    "LIME": "\033[1;38;5;154m",
    "TURQUOISE": "\033[1;38;5;45m",
    "VIOLET": "\033[1;38;5;128m",
    "CORAL": "\033[1;38;5;209m",
    "MAROON": "\033[1;38;5;88m",
    "NAVY": "\033[1;38;5;17m",
    "OLIVE": "\033[1;38;5;58m",
    "BEIGE": "\033[1;38;5;230m",
    "MINT": "\033[1;38;5;121m",
    "LIGHT_BLACK": "\033[1;38;5;235m",
    "LIGHT_RED": "\033[1;38;5;203m",
    "LIGHT_GREEN": "\033[1;38;5;120m",
    "LIGHT_YELLOW": "\033[1;38;5;227m",
    "LIGHT_BLUE": "\033[1;38;5;81m",
    "LIGHT_MAGENTA": "\033[1;38;5;219m",
    "LIGHT_CYAN": "\033[1;38;5;87m",
    "LIGHT_WHITE": "\033[1;38;5;255m",
    "LIGHT_ORANGE": "\033[1;38;5;214m",
    "LIGHT_PINK": "\033[1;38;5;218m",
    "LIGHT_GRAY": "\033[1;38;5;250m",
    "LIGHT_BROWN": "\033[1;38;5;180m",
    "LIGHT_AQUA": "\033[1;38;5;159m",
    "LIGHT_PURPLE": "\033[1;38;5;183m",
    "LIGHT_GOLD": "\033[1;38;5;228m",
    "LIGHT_SILVER": "\033[1;38;5;253m",
    "LIGHT_INDIGO": "\033[1;38;5;99m",
    "LIGHT_TEAL": "\033[1;38;5;37m",
    "LIGHT_CRIMSON": "\033[1;38;5;167m",
    "LIGHT_LIME": "\033[1;38;5;191m",
    "LIGHT_TURQUOISE": "\033[1;38;5;159m",
    "LIGHT_VIOLET": "\033[1;38;5;177m",
    "LIGHT_CORAL": "\033[1;38;5;216m",
    "LIGHT_MAROON": "\033[1;38;5;131m",
    "LIGHT_NAVY": "\033[1;38;5;33m",
    "LIGHT_OLIVE": "\033[1;38;5;100m",
    "LIGHT_BEIGE": "\033[1;38;5;253m",
    "LIGHT_MINT": "\033[1;38;5;157m",
}


class AnsiColors:
    def __init__(self):
        self.RESET = "\033[0m"
        for name, code in _COLOR_CODES.items():
            setattr(self, name, code)

    @property
    def print_all_colors(self):
        for name, code in vars(self).items():
            if name != "RESET":
                print(f"{code}{name}{self.RESET}")

    @property
    def random_color(self):
        codes = [code for name, code in vars(self).items() if name != "RESET"]
        return random.choice(codes), self.RESET