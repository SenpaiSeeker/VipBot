import re

from telethon import Button as TelethonButton
from telethon.tl.types import KeyboardButtonCopy


class Button:
    def get_urls(self, text):
        return re.findall(
            r"(?:https?://)?(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:[/?]\S+)?|tg://\S+$",
            text,
        )

    def parse_buttons_and_text(self, text, mode="inline"):
        if mode == "inline":
            button_data = re.findall(r"\| ([^|]+) - ([^|]+) \|", text)
            extracted_text = (
                re.split(r"\| [^|]+ - [^|]+ \|", text)[0].strip()
                if "|" in text
                else text.strip()
            )

            return button_data, extracted_text

        elif mode == "reply":
            pattern = r"\|\s*([^\|]+?)\s*\|"
            raw_data = re.findall(pattern, text)
            extracted_text = re.sub(pattern, "", text).strip()
            buttons = []

            for chunk in raw_data:
                parts = chunk.split("-")

                for part in parts:
                    if ";" in part:
                        label, *params = part.split(";")
                        buttons.append(
                            (
                                label.strip().strip("]"),
                                [p.strip() for p in params],
                            )
                        )
                    else:
                        buttons.append((part.strip().strip("]"), []))

            return buttons, extracted_text

        else:
            raise ValueError("Invalid parse mode. Use 'inline' or 'reply'.")

    def create_inline_keyboard(
        self,
        text,
        inline_cmd=None,
        is_id=None,
        cb_prefix=None,
    ):
        layout = []
        buttons, remaining_text = self.parse_buttons_and_text(text, mode="inline")

        for label, payload in buttons:
            cb_data, *extra_params = payload.split(";")
            is_url = bool(self.get_urls(cb_data)) and "webapp" not in extra_params
            is_copy = "copy" in extra_params
            is_user = "user" in extra_params
            is_webapp = "webapp" in extra_params

            style = None
            icon = None

            for param in extra_params:
                param = param.strip()

                if param.startswith("style="):
                    style_val = param.split("=")[1].lower()

                    if style_val in ["red", "danger"]:
                        style = "danger"
                    elif style_val in ["blue", "primary"]:
                        style = "primary"
                    elif style_val in ["green", "success"]:
                        style = "success"

                elif param.startswith("emoji="):
                    emoji_val = param.split("=")[1]

                    try:
                        icon = int(emoji_val)
                    except ValueError:
                        icon = emoji_val

            if not is_url and not is_copy and not is_user and not is_webapp:
                if cb_prefix:
                    cb_data = f"{cb_prefix}_{cb_data}"
                elif inline_cmd and is_id:
                    cb_data = f"{inline_cmd} {is_id}_{cb_data}"
                elif inline_cmd:
                    cb_data = f"{inline_cmd} {cb_data}"

            if is_user:
                button = TelethonButton.inline(
                    label, data=f"usr_{cb_data}".encode("utf-8"), style=style, icon=icon
                )
            elif is_copy:
                button = KeyboardButtonCopy(text=label, copy_text=cb_data)
            elif is_webapp:
                button = TelethonButton.web_app(label, url=cb_data)
            elif is_url:
                button = TelethonButton.url(label, url=cb_data)
            else:
                button = TelethonButton.inline(
                    label, data=cb_data.encode("utf-8"), style=style, icon=icon
                )

            if "same" in extra_params and layout:
                layout[-1].append(button)
            else:
                layout.append([button])

        return layout if layout else None, remaining_text

    def create_button_keyboard(self, text):
        layout = []
        buttons, remaining_text = self.parse_buttons_and_text(text, mode="reply")

        for label, params in buttons:
            if "is_contact" in params:
                button = TelethonButton.request_phone(label)
            else:
                button = TelethonButton.text(label)

            if "same" in params and layout:
                layout[-1].append(button)
            else:
                layout.append([button])

        return layout if layout else None, remaining_text

    def remove_reply_keyboard(self, selective=False):
        return TelethonButton.clear()

    def build_button_grid(self, layout):
        keyboard = []

        for row_data in layout:
            row = []

            for button_info in row_data:
                text = button_info.get("text")
                url = button_info.get("url")
                cb_data = button_info.get("callback_data")
                web_app = button_info.get("web_app")
                copy_text = button_info.get("copy_text")
                style_val = button_info.get("style")
                emoji_val = button_info.get("emoji")

                style = None
                if style_val:
                    style_str = str(style_val).lower()

                    if style_str in ["red", "danger"]:
                        style = "danger"
                    elif style_str in ["blue", "primary"]:
                        style = "primary"
                    elif style_str in ["green", "success"]:
                        style = "success"

                icon = None
                if emoji_val:
                    try:
                        icon = int(emoji_val)
                    except (ValueError, TypeError):
                        icon = emoji_val

                if url:
                    row.append(TelethonButton.url(text, url, style=style, icon=icon))
                elif web_app:
                    row.append(
                        TelethonButton.web_app(text, web_app, style=style, icon=icon)
                    )
                elif copy_text:
                    row.append(KeyboardButtonCopy(text=text, copy_text=copy_text))
                elif cb_data:
                    row.append(
                        TelethonButton.inline(
                            text,
                            data=(
                                cb_data.encode("utf-8")
                                if isinstance(cb_data, str)
                                else cb_data
                            ),
                            style=style,
                            icon=icon,
                        )
                    )

            if row:
                keyboard.append(row)

        return keyboard if keyboard else None
