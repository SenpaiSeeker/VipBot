import base64
import binascii
import json

from .logger import LoggerHandler

_METHODS = ("shift", "bytes", "binary")


class CipherHandler:
    def __init__(self, **options):
        self.method = options.get("method", "shift")
        self.key = self._normalize_key(options.get("key", "my_s3cr3t_k3y_@2024!"))
        self.delimiter = options.get("delimiter", "|")
        if not self.key:
            raise ValueError("Key cannot be empty.")
        self.numeric_key = self._get_numeric_key()
        self.log = LoggerHandler()

    def _normalize_key(self, key) -> str:
        try:
            if isinstance(key, list):
                return "".join(map(str, key))
            return str(key)
        except Exception as e:
            raise ValueError(f"Key normalization failed: {e}")

    def _get_numeric_key(self) -> str:
        total_ord_sum = sum(ord(c) for c in self.key)
        return "".join(
            str((ord(char) + total_ord_sum + i) % 10)
            for i, char in enumerate(self.key)
        )

    def _offset(self, index: int) -> int:
        try:
            key_char_code = ord(self.key[index % len(self.key)])
            return len(self.key) * (index + 1) + key_char_code
        except Exception as e:
            raise Exception(f"Offset calculation failed at index {index}: {e}")

    def _xor(self, data: bytes) -> bytes:
        key_bytes = self.key.encode("utf-8")
        return bytes(
            data[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data))
        )

    def _base64_encode(self, data: str) -> str:
        return base64.b64encode(data.encode("utf-8")).decode("utf-8").rstrip("=")

    def _base64_decode(self, encoded_data: str) -> str:
        try:
            padding = (4 - len(encoded_data) % 4) % 4
            decoded = base64.b64decode(encoded_data + "=" * padding)
            return decoded.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as e:
            raise ValueError(f"Base64 decryption failed: {e}")

    def encrypt_shift(self, text: str) -> str:
        encoded = [
            hex(ord(text[i]) + ord(self.key[i % len(self.key)]))
            for i in range(len(text))
        ]
        return self.delimiter.join(encoded)

    def decrypt_shift(self, encoded_text: str) -> str:
        try:
            codes = encoded_text.split(self.delimiter)
            return "".join(
                chr(int(code, 16) - ord(self.key[i % len(self.key)]))
                for i, code in enumerate(codes)
            )
        except (ValueError, TypeError) as error:
            raise ValueError(f"Error during shift decryption: {error}")

    def encrypt_bytes(self, message: str) -> str:
        try:
            return self._xor(message.encode("utf-8")).hex()
        except Exception as e:
            raise Exception(f"Encryption failed for 'bytes' method: {e}")

    def decrypt_bytes(self, encrypted_data: str) -> str:
        try:
            return self._xor(bytes.fromhex(encrypted_data)).decode("utf-8")
        except Exception as e:
            raise Exception(f"Decryption failed for 'bytes' method: {e}")

    def encrypt_binary(self, plaintext: str) -> str:
        xor_key = int(self.numeric_key) % 256
        return "".join(format(ord(char) ^ xor_key, "08b") for char in plaintext)

    def decrypt_binary(self, encrypted_bits: str) -> str:
        if not encrypted_bits or len(encrypted_bits) % 8 != 0:
            raise ValueError("Data biner yang dienkripsi tidak valid atau kosong.")
        xor_key = int(self.numeric_key) % 256
        return "".join(
            chr(int(encrypted_bits[i : i + 8], 2) ^ xor_key)
            for i in range(0, len(encrypted_bits), 8)
        )

    def encrypt(self, data, only_base64: bool = False) -> str:
        if only_base64:
            return self._base64_encode(data)
        message = (
            data
            if isinstance(data, str)
            else json.dumps(data, separators=(",", ":"))
        )
        if self.method == "bytes":
            return self.encrypt_bytes(message)
        if self.method == "binary":
            return self.encrypt_binary(message)
        if self.method == "shift":
            return self.encrypt_shift(message)
        raise ValueError(f"Metode enkripsi '{self.method}' tidak dikenali.")

    def decrypt(self, encrypted_data: str, only_base64: bool = False):
        if only_base64:
            return self._base64_decode(encrypted_data)
        if self.method == "bytes":
            decrypted = self.decrypt_bytes(encrypted_data)
        elif self.method == "binary":
            decrypted = self.decrypt_binary(encrypted_data)
        elif self.method == "shift":
            decrypted = self.decrypt_shift(encrypted_data)
        else:
            raise ValueError(f"Metode dekripsi '{self.method}' tidak dikenali.")
        try:
            return json.loads(decrypted)
        except (json.JSONDecodeError, TypeError):
            return decrypted