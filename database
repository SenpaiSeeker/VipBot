import nsdev
from config import BOT_TOKEN, OWNER_ID

db = nsdev.DataBase(
    storage_type="local",
    file_name="database",
    binary_keys="@NorSodikin",
    method_encrypt="bytes",
    auto_backup=True,
    backup_bot_token=BOT_TOKEN,
    backup_chat_id=OWNER_ID,
    backup_interval_hours=6,
)
