from config import DB_KEY, DB_NAME
from helpers.database import DataBase

db = DataBase(
    storage_type="local",
    file_name=DB_NAME,
    keys_encrypt=DB_KEY,
    method_encrypt="bytes",
)
