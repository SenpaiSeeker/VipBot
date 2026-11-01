import asyncio
import json
import os
import shutil
import tempfile
from copy import deepcopy
from weakref import WeakValueDictionary

import aiofiles
import aiofiles.os

from .encrypt import CipherHandler
from .patcher import Object

_FILE_LOCKS = WeakValueDictionary()


def _get_file_lock(path):
    key = os.path.abspath(path)
    lock = _FILE_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _FILE_LOCKS[key] = lock
    return lock


class DataBase(Object):

    _ns_alias = "db"

    def __init__(self, client=None, **options):
        super().__init__(client)
        file_name = options.get("file_name")
        keys_encrypt = options.get("keys_encrypt")
        if client is not None and (file_name is None or keys_encrypt is None):
            from config import DB_KEY, DB_NAME

            if file_name is None:
                file_name = DB_NAME
            if keys_encrypt is None:
                keys_encrypt = DB_KEY
        self.file_name = file_name or "database"
        self.keys_encrypt = keys_encrypt or "default_db_key_12345"
        self.method_encrypt = options.get("method_encrypt", "bytes")

        self.cipher = CipherHandler(
            key=self.keys_encrypt,
            method=self.method_encrypt,
        )

        self.data_file = f"{self.file_name}.json"
        self._lock = _get_file_lock(self.data_file)
        self._mtime = None
        self._data = None
        self._member_cache = {}

        if not os.path.exists(self.data_file):
            with open(self.data_file, "w") as f:
                json.dump({"vars": {}, "bots": []}, f, indent=4)

    async def _run_sync(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    async def _file_mtime(self):
        try:
            stat = await self._run_sync(os.stat, self.data_file)
        except FileNotFoundError:
            return None
        return stat.st_mtime_ns

    async def _refresh_locked(self):
        mtime = await self._file_mtime()
        if self._data is None or self._mtime != mtime:
            self._data = await self._read_data_file()
            self._mtime = mtime

    async def _load_data(self):
        mtime = await self._file_mtime()
        if self._data is not None and self._mtime == mtime:
            return self._data

        async with self._lock:
            await self._refresh_locked()

        return self._data

    async def _mutate(self, mutator):
        async with self._lock:
            await self._refresh_locked()

            if mutator(self._data) is False:
                return

            await self._write_data_file()

    async def close_async(self):
        async with self._lock:
            self._data = None
            self._mtime = None
        self._invalidate_members()

    def _invalidate_members(self, user_id=None):
        if user_id is None:
            self._member_cache.clear()
            return

        target = str(user_id)
        for key in [k for k in self._member_cache if k[0] == target]:
            del self._member_cache[key]

    @staticmethod
    def _as_probe(value):
        try:
            return json.dumps(value, sort_keys=True)
        except (TypeError, ValueError):
            return str(value)

    async def isMemberOf(self, user_id, query_name, value, var_key="variabel"):
        cache_key = (str(user_id), var_key, query_name)
        members = self._member_cache.get(cache_key)

        if members is None:
            items = await self.getListVars(user_id, query_name, var_key)
            members = {self._as_probe(item) for item in items}
            self._member_cache[cache_key] = members

        return self._as_probe(value) in members

    async def _save_data(self, data):
        async with self._lock:
            self._data = data
            await self._write_data_file()

    async def _read_data_file(self):
        try:
            async with aiofiles.open(self.data_file, "r") as f:
                content = await f.read()
        except FileNotFoundError:
            return {"vars": {}, "bots": []}

        if not content.strip():
            return {"vars": {}, "bots": []}

        try:
            return await self._run_sync(json.loads, content)
        except json.JSONDecodeError as e:
            broken = f"{self.data_file}.corrupt"
            await self._run_sync(shutil.copy2, self.data_file, broken)
            raise RuntimeError(
                f"Database '{self.data_file}' rusak ({e}). "
                f"Salinan disimpan ke '{broken}'. Perbaiki atau hapus file "
                f"sebelum menjalankan bot lagi."
            ) from e

    async def _write_data_file(self):
        directory = os.path.dirname(os.path.abspath(self.data_file))
        fd, temp_file = tempfile.mkstemp(
            prefix=f"{os.path.basename(self.data_file)}.",
            suffix=".tmp",
            dir=directory,
        )
        os.close(fd)

        try:
            content = await self._run_sync(
                json.dumps, self._data, separators=(",", ":")
            )

            async with aiofiles.open(temp_file, "w") as f:
                await f.write(content)

            await aiofiles.os.replace(temp_file, self.data_file)
            self._mtime = await self._file_mtime()
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

    async def _encrypt_async(self, data: str) -> str:
        return await self._run_sync(self.cipher.encrypt, data)

    async def _decrypt_async(self, data: str):
        return await self._run_sync(self.cipher.decrypt, data)

    def _decrypt_sync(self, values):
        return [self.cipher.decrypt(v) for v in values]

    def _encrypt_sync(self, values):
        return [self.cipher.encrypt(v) for v in values]

    async def _decrypt_many_async(self, values):
        if not values:
            return []

        if len(values) < 16:
            return [await self._decrypt_async(v) for v in values]

        return await self._run_sync(self._decrypt_sync, values)

    def _namespace(self, data, user_id, var_key):
        return (
            data.setdefault("vars", {})
            .setdefault(str(user_id), {})
            .setdefault(var_key, {})
        )

    async def _get_user_vars(self, user_id):
        data = await self._load_data()
        return deepcopy(data.get("vars", {}).get(str(user_id), {}))

    async def _set_user_vars(self, user_id, user_data):
        user_id_str = str(user_id)
        snapshot = deepcopy(user_data)

        await self._mutate(
            lambda data: data.setdefault("vars", {}).__setitem__(user_id_str, snapshot)
        )

    async def setVars(self, user_id, query_name, value, var_key="variabel"):
        val_str = json.dumps(value)
        encrypted_value = await self._encrypt_async(val_str)

        def apply(data):
            self._namespace(data, user_id, var_key)[query_name] = encrypted_value
            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)

    async def setVarsOnce(self, user_id, query_name, value, var_key="variabel"):
        encrypted_value = await self._encrypt_async(json.dumps(value))
        result = {"created": False}

        def apply(data):
            bucket = self._namespace(data, user_id, var_key)
            if query_name in bucket:
                return False

            bucket[query_name] = encrypted_value
            result["created"] = True
            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)
        return result["created"]

    async def increment_sales_once(self, user_id, transaction_id, next_count):
        marker_key = f"sale_counted_{transaction_id}"
        enc_marker = await self._encrypt_async(json.dumps(True))
        enc_count = await self._encrypt_async(json.dumps(int(next_count)))
        result = {"incremented": False}

        def apply(data):
            bucket = self._namespace(data, user_id, "variabel")
            if marker_key in bucket:
                return False

            bucket[marker_key] = enc_marker
            bucket["sales_count"] = enc_count
            result["incremented"] = True
            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)
        return result["incremented"]

    async def getVars(self, user_id, query_name, var_key="variabel"):
        data = await self._load_data()
        encrypted_value = (
            data.get("vars", {}).get(str(user_id), {}).get(var_key, {}).get(query_name)
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
        def apply(data):
            bucket = data.get("vars", {}).get(str(user_id), {}).get(var_key)
            if not bucket or bucket.pop(query_name, None) is None:
                return False
            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)

    async def setListVars(
        self,
        user_id,
        query_name,
        value,
        var_key="variabel",
        check_duplicate=True,
    ):
        val_str = json.dumps(value)
        encrypted_value = await self._encrypt_async(val_str)

        def apply(data):
            target = self._namespace(data, user_id, var_key).setdefault(query_name, [])

            if check_duplicate and encrypted_value in target:
                return False

            target.append(encrypted_value)
            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)

    async def replaceListVars(self, user_id, query_name, values, var_key="variabel"):
        if not values:
            return await self.removeVars(user_id, query_name, var_key)

        encrypted_values = await self._run_sync(
            self._encrypt_sync, [json.dumps(v) for v in values]
        )

        def apply(data):
            self._namespace(data, user_id, var_key)[query_name] = encrypted_values
            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)

    async def getListVars(self, user_id, query_name, var_key="variabel"):
        data = await self._load_data()
        encrypted_list = (
            data.get("vars", {})
            .get(str(user_id), {})
            .get(var_key, {})
            .get(query_name, [])
        )
        decoded_list = []

        if not encrypted_list:
            return decoded_list

        decrypted_values = await self._decrypt_many_async(encrypted_list)

        for decrypted in decrypted_values:
            if isinstance(decrypted, str) and decrypted.startswith(("[", "{")):
                try:
                    decoded_list.append(json.loads(decrypted))
                except Exception:
                    decoded_list.append(decrypted)
            else:
                decoded_list.append(decrypted)

        return decoded_list

    async def removeListVars(self, user_id, query_name, value, var_key="variabel"):
        val_str = json.dumps(value)
        encrypted_value = await self._encrypt_async(val_str)

        def apply(data):
            target = (
                data.get("vars", {})
                .get(str(user_id), {})
                .get(var_key, {})
                .get(query_name)
            )
            if not target:
                return False

            try:
                target.remove(encrypted_value)
            except ValueError:
                return False

            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)

    async def updateListVars(self, user_id, query_name, updater, var_key="variabel"):
        async with self._lock:
            await self._refresh_locked()

            bucket = self._namespace(self._data, user_id, var_key)
            encrypted_list = list(bucket.get(query_name) or [])

            decoded_list = []
            if encrypted_list:
                decrypted_values = await self._decrypt_many_async(encrypted_list)
                for d in decrypted_values:
                    if isinstance(d, str) and d.startswith(("[", "{")):
                        try:
                            decoded_list.append(json.loads(d))
                        except Exception:
                            decoded_list.append(d)
                    else:
                        decoded_list.append(d)

            new_list = await updater(decoded_list)
            if new_list is None:
                return

            new_list = list(new_list)
            if not new_list:
                bucket.pop(query_name, None)
            else:
                bucket[query_name] = await self._run_sync(
                    self._encrypt_sync, [json.dumps(v) for v in new_list]
                )

            await self._write_data_file()

        self._invalidate_members(user_id)

    async def removeAllVars(self, user_id):
        user_id_str = str(user_id)

        def apply(data):
            if user_id_str not in data.get("vars", {}):
                return False

            del data["vars"][user_id_str]
            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)

    async def allVars(self, user_id, var_key="variabel"):
        user_data = await self._get_user_vars(user_id)
        encrypted_data = user_data.get(var_key, {})
        decrypted = {}

        def decode(raw_value):
            if isinstance(raw_value, str) and raw_value.startswith(("[", "{")):
                return json.loads(raw_value)
            return raw_value

        for key, value in encrypted_data.items():
            if isinstance(value, list):
                if not value:
                    decrypted[key] = []
                    continue

                try:
                    decoded = await self._decrypt_many_async(value)
                    decrypted[key] = [decode(d) for d in decoded]
                except Exception:
                    decrypted[key] = value
            else:
                try:
                    decrypted[key] = decode(await self._decrypt_async(value))
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

        def apply(data):
            bots_list = data.setdefault("bots", [])
            existing_index = next(
                (i for i, d in enumerate(bots_list) if d.get("user_id") == user_id_str),
                -1,
            )

            if existing_index != -1:
                bots_list[existing_index].update(bot_data)
            else:
                bots_list.append({"user_id": user_id_str, **bot_data})

            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)

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

        def apply(data):
            bots = data.get("bots", [])
            remaining = [b for b in bots if b.get("user_id") != user_id_str]

            if len(remaining) == len(bots):
                return False

            data["bots"] = remaining
            return True

        await self._mutate(apply)
        self._invalidate_members(user_id)
