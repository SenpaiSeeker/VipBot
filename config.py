import os
import sys

import dotenv

from helpers.storekey import KeyManager

key_manager = KeyManager()
DB_KEY, env_file = key_manager.handle_arguments()

if not os.path.exists(env_file):
    key_manager.logger.print(
        f"{key_manager.logger.RED}File environment '{env_file}' tidak ditemukan."
    )
    sys.exit(1)

dotenv.load_dotenv(env_file)

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
DB_NAME = os.getenv("DB_NAME")
BACKUP_BOT = os.getenv("BACKUP_BOT")

TELEGRAM_API_CREDENTIALS = [
    ("Android", 6, "eb06d4abfb49dc3eeb1aeb98ae0f581e"),
    ("AndroidX", 21724, "3e0cb5efcd52300aec5994fdfc5bdc16"),
    ("Desktop", 2040, "b18441a1ff607e10a989891a5462e627"),
    ("iOS", 10840, "33c45224029d59cb3ad0c16134215aeb"),
    ("macOS", 2834, "68875f756c9b437a8b916ca3de215815"),
    ("Web", 2496, "8da85b0d5bfe62527e5b244c209159c3"),
]
