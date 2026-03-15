from PIL import ImageFont

class FontManager:
    def _get_font_from_package(self, font_filename, size):
        return ImageFont.load_default()
