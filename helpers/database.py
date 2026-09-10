import asyncio
import json
import os
import shutil
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

import aiofiles
import aiofiles.os
import aiohttp

from .encrypt import CipherHandler

_INITIAL_DATA = {"vars": {}, "bots": []}


class DataBase:
    def __init__(self, **options):
        self.storage_type = "local"
        self.file_name = options.get("file_name", "database")
        self.keys_encrypt = options.get("keys_encrypt", "default_db_key_12345")
        self.method_encrypt = options.get("method_encrypt", "bytes")
        self.cipher = CipherHandler(
            key=self.keys_encrypt,
            method=self.method_encrypt,
        )
        self._lock = asyncio.Lock()
        self.auto_backup = options.get("auto_backup", False)
        self.backup_bot_token = options.get("backup_bot_token")
        self.backup_chat_id = options.get("backup_chat_id")
        self.backup_cron_spec = options.get("backup_cron_spec", "0 */3 * * *")
        self.scheduler = options.get("scheduler_instance")
        self.data_file = f"{self.file_name}.json"

        if not os.path.exists(self.data_file):
            with open(self.data_file, "w") as f:
                json.dump(_INITIAL_DATA, f, indent=4)

        self._register_backup_task()

    async def _run_sync(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    def _register_backup_task(self):
        if self.auto_backup and self.scheduler:
            if not self.backup_bot_token or not self.backup_chat_id:
                return self.cipher.log.warning(
                    "Auto backup is disabled because token/chat_id is missing."
                )

            @self.scheduler.cron(self.backup_cron_spec)
            async def scheduled_backup_task():
                asyncio.create_task(self.perform_backup())

    async def _load_data(self):
        async with self._lock:
            try:
                async with aiofiles.open(self.data_file, "r") as f:
                    content = await f.read()
                    if not content.strip():
                        return dict(_INITIAL_DATA)
                    return json.loads(content)
            except (FileNotFoundError, json.JSONDecodeError):
                return dict(_INITIAL_DATA)

    async def _save_data(self, data):
        async with self._lock:
            temp_file = f"{self.data_file}.tmp"
            async with aiofiles.open(temp_file, "w") as f:
                await f.write(json.dumps(data, indent=4))
            await aiofiles.os.replace(temp_file, self.data_file)

    async def _encrypt_async(self, data: str) -> str:
        return await self._run_sync(self.cipher.encrypt, data)

    async def _decrypt_async(self, data: str):
        return await self._run_sync(self.cipher.decrypt, data)

    async def _user_vars(self, user_id):
        data = await self._load_data()
        return data.get("vars", {}).get(str(user_id), {})

    async def _replace_user_vars(self, user_id, user_data):
        full_data = await self._load_data()
        full_data.setdefault("vars", {})[str(user_id)] = user_data
        await self._save_data(full_data)

    async def setVars(self, user_id, query_name, value, var_key="variabel"):
        user_data = await self._user_vars(user_id)
        user_data.setdefault(var_key, {})[query_name] = await self._encrypt_async(
            json.dumps(value)
        )
        await self._replace_user_vars(user_id, user_data)

    async def getVars(self, user_id, query_name, var_key="variabel"):
        encrypted_value = (await self._user_vars(user_id)).get(var_key, {}).get(
            query_name
        )
        if not encrypted_value:
            return None
        decrypted = await self._decrypt_async(encrypted_value)
        if isinstance(decrypted, str):
            try:
                return json.loads(decrypted)
            except (json.JSONDecodeError, TypeError):
                return decrypted
        return decrypted

    async def removeVars(self, user_id, query_name, var_key="variabel"):
        user_data = await self._user_vars(user_id)
        if user_data.get(var_key, {}).pop(query_name, None):
            await self._replace_user_vars(user_id, user_data)

    async def setListVars(self, user_id, query_name, value, var_key="variabel"):
        encrypted_value = await self._encrypt_async(json.dumps(value))
        user_data = await self._user_vars(user_id)
        bucket = user_data.setdefault(var_key, {}).setdefault(query_name, [])
        if encrypted_value not in bucket:
            bucket.append(encrypted_value)
            await self._replace_user_vars(user_id, user_data)

    async def getListVars(self, user_id, query_name, var_key="variabel"):
        encrypted_list = (await self._user_vars(user_id)).get(var_key, {}).get(
            query_name, []
        )
        decoded_list = []
        for raw in encrypted_list:
            decrypted = await self._decrypt_async(raw)
            decoded_list.append(await self._decode(decrypted))
        return decoded_list

    async def removeListVars(self, user_id, query_name, value, var_key="variabel"):
        encrypted_value = await self._encrypt_async(json.dumps(value))
        user_data = await self._user_vars(user_id)
        try:
            user_data.get(var_key, {}).get(query_name, []).remove(encrypted_value)
            await self._replace_user_vars(user_id, user_data)
        except (ValueError, KeyError):
            pass

    async def removeAllVars(self, user_id):
        full_data = await self._load_data()
        if str(user_id) in full_data.get("vars", {}):
            del full_data["vars"][str(user_id)]
            await self._save_data(full_data)

    async def allVars(self, user_id, var_key="variabel"):
        encrypted_data = (await self._user_vars(user_id)).get(var_key, {})
        decoded = {}
        for key, value in encrypted_data.items():
            if isinstance(value, list):
                items = []
                for raw in value:
                    try:
                        items.append(await self._decode(await self._decrypt_async(raw)))
                    except Exception:
                        items.append(raw)
                decoded[key] = items
            else:
                try:
                    decoded[key] = await self._decode(await self._decrypt_async(value))
                except Exception:
                    decoded[key] = value
        return decoded

    async def _decode(self, decrypted):
        if isinstance(decrypted, str) and decrypted.startswith(("[", "{")):
            try:
                return json.loads(decrypted)
            except (json.JSONDecodeError, TypeError):
                return decrypted
        return decrypted

    async def saveBot(self, user_id, api_id, api_hash, value, is_token=False):
        field = "bot_token" if is_token else "session_string"
        enc_api_id, enc_api_hash = await asyncio.gather(
            self._encrypt_async(str(api_id)),
            self._encrypt_async(api_hash),
        )
        bot_data = {"api_id": enc_api_id, "api_hash": enc_api_hash}
        if value:
            bot_data[field] = await self._encrypt_async(value)

        full_data = await self._load_data()
        bots = full_data.get("bots", [])
        index = next(
            (i for i, d in enumerate(bots) if d.get("user_id") == str(user_id)),
            -1,
        )
        if index != -1:
            bots[index].update(bot_data)
        else:
            bots.append({"user_id": str(user_id), **bot_data})
        full_data["bots"] = bots
        await self._save_data(full_data)

    async def getBots(self, is_token=False):
        data = await self._load_data()

        async def _decrypt_bot(bot_data):
            try:
                decrypted = {"name": bot_data.get("user_id") or bot_data.get("_id")}
                targets = {
                    key: bot_data[key]
                    for key in ("api_id", "api_hash", "bot_token", "session_string")
                    if bot_data.get(key)
                }
                results = await asyncio.gather(
                    *(self._decrypt_async(v) for v in targets.values()),
                    return_exceptions=True,
                )
                for key, result in zip(targets.keys(), results):
                    if isinstance(result, Exception):
                        continue
                    value = result if isinstance(result, str) else str(result)
                    decrypted[key] = int(value) if key == "api_id" else value
                if (is_token and "bot_token" in decrypted) or (
                    not is_token and "session_string" in decrypted
                ):
                    return decrypted
            except Exception:
                pass
            return None

        results = await asyncio.gather(*[_decrypt_bot(b) for b in data.get("bots", [])])
        return [r for r in results if r is not None]

    async def removeBot(self, user_id):
        full_data = await self._load_data()
        full_data["bots"] = [
            b
            for b in full_data.get("bots", [])
            if b.get("user_id") != str(user_id)
        ]
        await self._save_data(full_data)

    async def perform_backup(self):
        temp_backup_dir = "temp_db_backup"
        zip_path = None
        async with self._lock:
            if not await aiofiles.os.path.exists(self.data_file):
                return
            await aiofiles.os.makedirs(temp_backup_dir, exist_ok=True)
            try:
                temp_db_path = os.path.join(
                    temp_backup_dir, os.path.basename(self.data_file)
                )
                await self._run_sync(shutil.copy2, self.data_file, temp_db_path)
            except Exception:
                await self._run_sync(
                    shutil.rmtree, temp_backup_dir, ignore_errors=True
                )
                return

        try:
            zip_path = await self._run_sync(
                self._create_zip_archive, [temp_db_path], temp_backup_dir
            )
            if zip_path:
                timestamp = datetime.now(ZoneInfo("Asia/Jakarta")).strftime(
                    "%Y-%m-%d %H:%M:%S %Z"
                )
                caption = (
                    f"Backup otomatis untuk `{os.path.basename(zip_path)}`\n"
                    f"Tipe DB: `{self.storage_type}`\n"
                    f"Waktu: `{timestamp}`"
                )
                await self._send_zip_to_telegram(zip_path, caption)
        except Exception:
            pass
        finally:
            await self._run_sync(shutil.rmtree, temp_backup_dir, ignore_errors=True)
            if zip_path and await aiofiles.os.path.exists(zip_path):
                try:
                    await aiofiles.os.remove(zip_path)
                except Exception:
                    pass

    def _create_zip_archive(self, source_paths, temp_dir):
        timestamp = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y%m%d_%H%M%S")
        zip_filename = f"backup_{self.file_name}_{timestamp}.zip"
        try:
            with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in source_paths:
                    zf.write(path, os.path.basename(path))
            return zip_filename
        except Exception:
            return None

    async def _send_zip_to_telegram(self, file_path, caption):
        url = f"https://api.telegram.org/bot{self.backup_bot_token}/sendDocument"
        async with aiofiles.open(file_path, "rb") as f:
            file_bytes = await f.read()
        data = aiohttp.FormData()
        data.add_field("chat_id", str(self.backup_chat_id))
        data.add_field("caption", caption)
        data.add_field("parse_mode", "Markdown")
        data.add_field("document", file_bytes, filename=os.path.basename(file_path))
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(url, data=data) as resp:
                    await resp.json()
            except Exception:
                pass