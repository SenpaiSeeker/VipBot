import base64
import binascii
import json

from .logger import LoggerHandler


class CipherHandler:
    def __init__(self, **options):
        self.method = options.get("method", "shift")
        self.key = self._normalize_key(options.get("key", "my_s3cr3t_k3y_@2024!"))
        self.numeric_key = self._get_numeric_key()
        self.delimiter = options.get("delimiter", "|")

        if not self.key:
            raise ValueError("Key cannot be empty.")

        self.log = LoggerHandler()

    def _normalize_key(self, key) -> str:
        try:
            if isinstance(key, list):
                return "".join(map(str, key))
            elif isinstance(key, (int, float)):
                return str(key)
            elif isinstance(key, str):
                return key
            else:
                return str(key)
        except Exception as e:
            raise ValueError(f"Key normalization failed: {e}")

    def _get_numeric_key(self) -> str:
        total_ord_sum = sum(ord(c) for c in self.key)
        return "".join(
            [
                str((ord(char) + total_ord_sum + i) % 10)
                for i, char in enumerate(self.key)
            ]
        )

    def _offset(self, index: int) -> int:
        try:
            key_char_code = ord(self.key[index % len(self.key)])
            return len(self.key) * (index + 1) + key_char_code
        except Exception as e:
            raise Exception(f"Offset calculation failed at index {index}: {e}")

    def _xor_encrypt_decrypt(self, data: bytes) -> bytes:
        key_bytes = self.key.encode("utf-8")
        if isinstance(data, str):
            data = data.encode("utf-8")
        return bytes(
            [data[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data))]
        )

    def _base64_encode(self, data: str) -> str:
        encoded_bytes = base64.b64encode(data.encode("utf-8"))
        return encoded_bytes.decode("utf-8").rstrip("=")

    def _base64_decode(self, encoded_data: str) -> str:
        try:
            padding_needed = (4 - len(encoded_data) % 4) % 4
            padded_data = encoded_data + "=" * padding_needed
            decoded_bytes = base64.b64decode(padded_data)
            return decoded_bytes.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as e:
            raise ValueError(f"Base64 decryption failed: {e}")

    def decrypt(self, encrypted_data: str, only_base64: bool = False):
        if only_base64:
            return self._base64_decode(encrypted_data)

        decrypted_string = ""
        if self.method == "bytes":
            decrypted_string = self.decrypt_bytes(encrypted_data)
        elif self.method == "binary":
            decrypted_string = self.decrypt_binary(encrypted_data)
        elif self.method == "shift":
            decrypted_string = self.decrypt_shift(encrypted_data)
        else:
            raise ValueError(f"Metode dekripsi '{self.method}' tidak dikenali.")

        try:
            return json.loads(decrypted_string)
        except (json.JSONDecodeError, TypeError):
            return decrypted_string

    def decrypt_binary(self, encrypted_bits: str) -> str:
        if not encrypted_bits or len(encrypted_bits) % 8 != 0:
            raise ValueError("Data biner yang dienkripsi tidak valid atau kosong.")
        decrypted_chars = [
            chr(int(encrypted_bits[i : i + 8], 2) ^ int(self.numeric_key) % 256)
            for i in range(0, len(encrypted_bits), 8)
        ]
        return "".join(decrypted_chars)

    def decrypt_bytes(self, encrypted_data: str) -> str:
        try:
            encrypted_bytes = bytes.fromhex(encrypted_data)
            decrypted_bytes = self._xor_encrypt_decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            raise Exception(f"Decryption failed for 'bytes' method: {e}")

    def decrypt_shift(self, encoded_text: str) -> str:
        try:
            codes = encoded_text.split(self.delimiter)
            return "".join(
                chr(int(code, 16) - ord(self.key[i % len(self.key)]))
                for i, code in enumerate(codes)
            )
        except (ValueError, TypeError) as error:
            raise ValueError(f"Error during shift decryption: {error}")

    def encrypt(self, data, only_base64: bool = False) -> str:
        if only_base64:
            return self._base64_encode(data)

        if not isinstance(data, str):
            message_to_encrypt = json.dumps(data, separators=(",", ":"))
        else:
            message_to_encrypt = data

        if self.method == "bytes":
            return self.encrypt_bytes(message_to_encrypt)
        elif self.method == "binary":
            return self.encrypt_binary(message_to_encrypt)
        elif self.method == "shift":
            return self.encrypt_shift(message_to_encrypt)
        else:
            raise ValueError(f"Metode enkripsi '{self.method}' tidak dikenali.")

    def encrypt_binary(self, plaintext: str) -> str:
        xor_key = int(self.numeric_key) % 256
        encrypted_bits = "".join(
            format(ord(char) ^ xor_key, "08b") for char in plaintext
        )
        return encrypted_bits

    def encrypt_bytes(self, message: str) -> str:
        try:
            encrypted_bytes = self._xor_encrypt_decrypt(message.encode("utf-8"))
            return encrypted_bytes.hex()
        except Exception as e:
            raise Exception(f"Encryption failed for 'bytes' method: {e}")

    def encrypt_shift(self, text: str) -> str:
        encoded_hex = [
            hex(ord(text[i]) + ord(self.key[i % len(self.key)]))
            for i in range(len(text))
        ]
        return self.delimiter.join(encoded_hex)
