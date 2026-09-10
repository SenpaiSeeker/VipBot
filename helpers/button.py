import re
from typing import Dict, List

import pyrogram


class Button:
    URL_PATTERN = (
        r"(?:https?://)?(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:[/?]\S+)?|tg://\S+$"
    )
    INLINE_PATTERN = r"\| ([^|]+) - ([^|]+) \|"
    REPLY_PATTERN = r"\|\s*([^\|]+?)\s*\|"

    def get_urls(self, text):
        return re.findall(self.URL_PATTERN, text)

    def parse_buttons_and_text(self, text, mode="inline"):
        if mode == "inline":
            button_data = re.findall(self.INLINE_PATTERN, text)
            if "|" in text:
                extracted_text = re.split(self.INLINE_PATTERN, text)[0].strip()
            else:
                extracted_text = text.strip()
            return button_data, extracted_text

        if mode == "reply":
            raw_data = re.findall(self.REPLY_PATTERN, text)
            extracted_text = re.sub(self.REPLY_PATTERN, "", text).strip()
            buttons = []
            for chunk in raw_data:
                for part in chunk.split("-"):
                    if ";" in part:
                        label, *params = part.split(";")
                        buttons.append((label.strip().strip("]"), [p.strip() for p in params]))
                    else:
                        buttons.append((part.strip().strip("]"), []))
            return buttons, extracted_text

        raise ValueError("Invalid parse mode. Use 'inline' or 'reply'.")

    @staticmethod
    def _style_enum(style_val):
        if style_val == "red":
            return pyrogram.enums.ButtonStyle.DANGER
        if style_val == "blue":
            return pyrogram.enums.ButtonStyle.PRIMARY
        if style_val == "green":
            return pyrogram.enums.ButtonStyle.SUCCESS
        return None

    @staticmethod
    def _custom_emoji_id(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return value

    def create_inline_keyboard(self, text, inline_cmd=None, is_id=None, cb_prefix=None):
        layout = []
        buttons, remaining_text = self.parse_buttons_and_text(text, mode="inline")

        for label, payload in buttons:
            cb_data, *extra_params = payload.split(";")

            is_url = bool(self.get_urls(cb_data)) and "webapp" not in extra_params
            is_copy = "copy" in extra_params
            is_user = "user" in extra_params
            is_webapp = "webapp" in extra_params

            if not (is_url or is_copy or is_user or is_webapp):
                if cb_prefix:
                    cb_data = f"{cb_prefix}_{cb_data}"
                elif inline_cmd and is_id:
                    cb_data = f"{inline_cmd} {is_id}_{cb_data}"
                elif inline_cmd:
                    cb_data = f"{inline_cmd} {cb_data}"

            button_kwargs = {"text": label}

            for param in extra_params:
                param = param.strip()
                if param.startswith("style="):
                    style_val = param.split("=")[1].lower()
                    style_enum = self._style_enum(style_val)
                    if style_enum is not None:
                        button_kwargs["style"] = style_enum
                elif param.startswith("emoji="):
                    button_kwargs["icon_custom_emoji_id"] = self._custom_emoji_id(
                        param.split("=")[1]
                    )

            if is_user:
                button_kwargs["user_id"] = cb_data
            elif is_copy:
                button_kwargs["copy_text"] = pyrogram.types.CopyTextButton(text=cb_data)
            elif is_webapp:
                button_kwargs["web_app"] = pyrogram.types.WebAppInfo(url=cb_data)
            elif is_url:
                button_kwargs["url"] = cb_data
            else:
                button_kwargs["callback_data"] = cb_data

            button = pyrogram.types.InlineKeyboardButton(**button_kwargs)

            if "same" in extra_params and layout:
                layout[-1].append(button)
            else:
                layout.append([button])

        return pyrogram.types.InlineKeyboardMarkup(layout), remaining_text

    def create_button_keyboard(self, text):
        layout = []
        buttons, remaining_text = self.parse_buttons_and_text(text, mode="reply")
        for label, params in buttons:
            if "is_contact" in params:
                button = pyrogram.types.KeyboardButton(label, request_contact=True)
            else:
                button = pyrogram.types.KeyboardButton(label)
            if "same" in params and layout:
                layout[-1].append(button)
            else:
                layout.append([button])
        return (
            pyrogram.types.ReplyKeyboardMarkup(layout, resize_keyboard=True),
            remaining_text,
        )

    def remove_reply_keyboard(self, selective=False):
        return pyrogram.types.ReplyKeyboardRemove(selective=selective)

    def build_button_grid(self, layout: List[List[Dict]]):
        keyboard = []
        for row_data in layout:
            row = []
            for button_info in row_data:
                btn_kwargs = button_info.copy()

                if "web_app" in btn_kwargs and isinstance(btn_kwargs["web_app"], str):
                    btn_kwargs["web_app"] = pyrogram.types.WebAppInfo(
                        url=btn_kwargs["web_app"]
                    )

                if "style" in btn_kwargs and isinstance(btn_kwargs["style"], str):
                    style_enum = self._style_enum(btn_kwargs["style"].lower())
                    if style_enum is not None:
                        btn_kwargs["style"] = style_enum

                if "emoji" in btn_kwargs:
                    emoji_val = btn_kwargs.pop("emoji")
                    btn_kwargs["icon_custom_emoji_id"] = self._custom_emoji_id(emoji_val)

                row.append(pyrogram.types.InlineKeyboardButton(**btn_kwargs))

            if row:
                keyboard.append(row)

        return pyrogram.types.InlineKeyboardMarkup(keyboard) if keyboard else None