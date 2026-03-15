from config import BOT_TOKEN, DB_KEY, DB_NAME, OWNER_ID
from helpers.database import DataBase
from helpers.scheduler import Scheduler

schedule = Scheduler()

db = DataBase(
    storage_type="local",
    file_name=DB_NAME,
    keys_encrypt=DB_KEY,
    method_encrypt="bytes",
    auto_backup=True,
    backup_bot_token=BOT_TOKEN,
    backup_chat_id=OWNER_ID,
    backup_cron_spec="0 */3 * * *",
    scheduler_instance=schedule,
)
