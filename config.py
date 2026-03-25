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
