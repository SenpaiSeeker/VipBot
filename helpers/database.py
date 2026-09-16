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
                json.dump({"vars": {}, "bots": []}, f, indent=4)

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

    async def perform_backup(self):
        zip_path = None
        temp_backup_dir = "temp_db_backup"
        db_path = self.data_file

        async with self._lock:
            if not await aiofiles.os.path.exists(db_path):
                return

            await aiofiles.os.makedirs(temp_backup_dir, exist_ok=True)

            try:
                temp_db_path = os.path.join(temp_backup_dir, os.path.basename(db_path))
                await self._run_sync(shutil.copy2, db_path, temp_db_path)
            except Exception:
                await self._run_sync(shutil.rmtree, temp_backup_dir, ignore_errors=True)
                return

        try:
            source_paths = [temp_db_path]
            zip_path = await self._run_sync(
                self._create_zip_archive, source_paths, temp_backup_dir
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

    def _create_zip_archive(self, source_paths: list, temp_dir: str):
        timestamp = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y%m%d_%H%M%S")
        zip_filename = f"backup_{self.file_name}_{timestamp}.zip"

        try:
            with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in source_paths:
                    arcname = os.path.basename(path)
                    zf.write(path, arcname)
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

    async def _load_data(self):
        async with self._lock:
            try:
                async with aiofiles.open(self.data_file, "r") as f:
                    content = await f.read()

                    if not content.strip():
                        return {"vars": {}, "bots": []}

                    return json.loads(content)
            except (FileNotFoundError, json.JSONDecodeError):
                return {"vars": {}, "bots": []}

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

    async def _get_user_vars(self, user_id):
        user_id_str = str(user_id)
        data = await self._load_data()
        return data.get("vars", {}).get(user_id_str, {})

    async def _set_user_vars(self, user_id, user_data):
        user_id_str = str(user_id)
        full_data = await self._load_data()

        full_data.setdefault("vars", {})[user_id_str] = user_data
        await self._save_data(full_data)

    async def setVars(self, user_id, query_name, value, var_key="variabel"):
        val_str = json.dumps(value)
        encrypted_value = await self._encrypt_async(val_str)

        user_data = await self._get_user_vars(user_id)
        user_data.setdefault(var_key, {})[query_name] = encrypted_value

        await self._set_user_vars(user_id, user_data)

    async def getVars(self, user_id, query_name, var_key="variabel"):
        user_data = await self._get_user_vars(user_id)
        encrypted_value = user_data.get(var_key, {}).get(query_name)

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
        user_data = await self._get_user_vars(user_id)

        if user_data.get(var_key, {}).pop(query_name, None):
            await self._set_user_vars(user_id, user_data)

    async def setListVars(self, user_id, query_name, value, var_key="variabel"):
        val_str = json.dumps(value)
        encrypted_value = await self._encrypt_async(val_str)

        user_data = await self._get_user_vars(user_id)
        user_data.setdefault(var_key, {}).setdefault(query_name, [])

        if encrypted_value not in user_data[var_key][query_name]:
            user_data[var_key][query_name].append(encrypted_value)
            await self._set_user_vars(user_id, user_data)

    async def getListVars(self, user_id, query_name, var_key="variabel"):
        user_data = await self._get_user_vars(user_id)
        encrypted_list = user_data.get(var_key, {}).get(query_name, [])
        decoded_list = []

        for v in encrypted_list:
            decrypted = await self._decrypt_async(v)

            try:
                s = decrypted if isinstance(decrypted, str) else json.dumps(decrypted)
                decoded_list.append(
                    json.loads(s)
                    if isinstance(decrypted, str) and decrypted.startswith(("[", "{"))
                    else decrypted
                )
            except Exception:
                decoded_list.append(decrypted)

        return decoded_list

    async def removeListVars(self, user_id, query_name, value, var_key="variabel"):
        val_str = json.dumps(value)
        encrypted_value = await self._encrypt_async(val_str)

        user_data = await self._get_user_vars(user_id)

        try:
            user_data.get(var_key, {}).get(query_name, []).remove(encrypted_value)
            await self._set_user_vars(user_id, user_data)
        except (ValueError, KeyError):
            pass

    async def removeAllVars(self, user_id):
        user_id_str = str(user_id)
        full_data = await self._load_data()

        if user_id_str in full_data.get("vars", {}):
            del full_data["vars"][user_id_str]
            await self._save_data(full_data)

    async def allVars(self, user_id, var_key="variabel"):
        user_data = await self._get_user_vars(user_id)
        encrypted_data = user_data.get(var_key, {})
        decrypted = {}

        for key, value in encrypted_data.items():
            if isinstance(value, list):
                temp_list = []

                for v in value:
                    try:
                        decrypted_v = await self._decrypt_async(v)
                        s = (
                            decrypted_v
                            if isinstance(decrypted_v, str)
                            else json.dumps(decrypted_v)
                        )
                        temp_list.append(
                            json.loads(s)
                            if isinstance(decrypted_v, str)
                            and decrypted_v.startswith(("[", "{"))
                            else decrypted_v
                        )
                    except Exception:
                        temp_list.append(v)

                decrypted[key] = temp_list
            else:
                try:
                    decrypted_v = await self._decrypt_async(value)
                    s = (
                        decrypted_v
                        if isinstance(decrypted_v, str)
                        else json.dumps(decrypted_v)
                    )
                    decrypted[key] = (
                        json.loads(s)
                        if isinstance(decrypted_v, str)
                        and decrypted_v.startswith(("[", "{"))
                        else decrypted_v
                    )
                except Exception:
                    decrypted[key] = value

        return decrypted

    async def saveBot(self, user_id, api_id, api_hash, value, is_token=False):
        user_id_str = str(user_id)
        field = "bot_token" if is_token else "session_string"

        enc_api_id, enc_api_hash = await asyncio.gather(
            self._encrypt_async(str(api_id)),
            self._encrypt_async(api_hash),
        )

        bot_data = {"api_id": enc_api_id, "api_hash": enc_api_hash}

        if value:
            bot_data[field] = await self._encrypt_async(value)

        full_data = await self._load_data()
        bots_list = full_data.get("bots", [])

        existing_index = next(
            (i for i, d in enumerate(bots_list) if d.get("user_id") == user_id_str),
            -1,
        )

        if existing_index != -1:
            bots_list[existing_index].update(bot_data)
        else:
            bots_list.append({"user_id": user_id_str, **bot_data})

        full_data["bots"] = bots_list
        await self._save_data(full_data)

    async def getBots(self, is_token=False):
        data = await self._load_data()
        raw_bots = data.get("bots", [])

        async def _decrypt_bot(bot_data):
            try:
                decrypted = {"name": bot_data.get("user_id") or bot_data.get("_id")}

                decrypt_tasks = {
                    key: self._decrypt_async(bot_data[key])
                    for key in ["api_id", "api_hash", "bot_token", "session_string"]
                    if bot_data.get(key)
                }

                results = await asyncio.gather(
                    *decrypt_tasks.values(), return_exceptions=True
                )

                for key, result in zip(decrypt_tasks.keys(), results):
                    if isinstance(result, Exception):
                        continue

                    val = result if isinstance(result, str) else str(result)
                    decrypted[key] = int(val) if key == "api_id" else val

                if (is_token and "bot_token" in decrypted) or (
                    not is_token and "session_string" in decrypted
                ):
                    return decrypted
            except Exception:
                pass
            return None

        results = await asyncio.gather(*[_decrypt_bot(b) for b in raw_bots])
        return [r for r in results if r is not None]

    async def removeBot(self, user_id):
        user_id_str = str(user_id)
        full_data = await self._load_data()

        full_data["bots"] = [
            b for b in full_data.get("bots", []) if b.get("user_id") != user_id_str
        ]

        full_data.setdefault("vars", {}).pop(user_id_str, None)

        await self._save_data(full_data)
