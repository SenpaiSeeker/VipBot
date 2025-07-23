import os
from nsdev import YamlHandler

yaml = YamlHandler()
LANGS = {}

strings_path = "strings"
if os.path.isdir(strings_path):
    for file in os.listdir(strings_path):
        if file.endswith(".yml"):
            lang_code = file[:-4]
            LANGS[lang_code] = yaml.loadAndConvert(os.path.join(strings_path, file))


def get_lang(db, user_id):
    return db.getVars(user_id, "language", var_key="user_info") or "id"


def get_string(lang_code, key):
    try:
        keys = key.split(".")
        node = LANGS.get(lang_code, LANGS.get("id"))
        for k in keys:
            node = getattr(node, k, None)
            if node is None:
                node_default = LANGS.get("id")
                for k_def in keys:
                    node_default = getattr(node_default, k_def, f"[{key}]")
                return node_default
        return node if isinstance(node, str) else f"[{key}]"
    except Exception:
        return f"[{key}]"


class Language:
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
        self.lang_code = get_lang(self.db, self.user_id)

    def get(self, key, *args, **kwargs):
        raw_string = get_string(self.lang_code, key)
        try:
            return raw_string.format(*args, **kwargs)
        except (KeyError, IndexError):
            return raw_string
