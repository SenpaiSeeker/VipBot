import { LoggerHandler } from "./logger";

const _METHODS = ["shift", "bytes", "binary"] as const;
type CipherMethod = (typeof _METHODS)[number];

export class CipherHandler {
    method: CipherMethod;
    key: string;
    delimiter: string;
    numeric_key: string;
    log = new LoggerHandler();

    constructor(options: Record<string, unknown> = {}) {
        this.method = (options.method as CipherMethod) || "shift";
        this.key = this._normalize_key(options.key ?? "my_s3cr3t_k3y_@2024!");
        this.delimiter = (options.delimiter as string) || "|";
        if (!this.key) {
            throw new Error("Key cannot be empty.");
        }
        this.numeric_key = this._get_numeric_key();
    }

    _normalize_key(key: unknown): string {
        try {
            if (Array.isArray(key)) {
                return key.map((k) => String(k)).join("");
            }
            return String(key);
        } catch {
            throw new Error("Key normalization failed");
        }
    }

    _get_numeric_key(): string {
        const totalOrdSum = Array.from(this.key).reduce((acc, c) => acc + c.charCodeAt(0), 0);
        return Array.from(this.key)
            .map((char, i) => String((char.charCodeAt(0) + totalOrdSum + i) % 10))
            .join("");
    }

    _offset(index: number): number {
        try {
            const keyCharCode = this.key.charCodeAt(index % this.key.length);
            return this.key.length * (index + 1) + keyCharCode;
        } catch {
            throw new Error(`Offset calculation failed at index ${index}`);
        }
    }

    _xor(data: Buffer): Buffer {
        const keyBytes = Buffer.from(this.key, "utf-8");
        const out = Buffer.alloc(data.length);
        for (let i = 0; i < data.length; i++) {
            out[i] = data[i] ^ keyBytes[i % keyBytes.length];
        }
        return out;
    }

    _base64_encode(data: string): string {
        return Buffer.from(data, "utf-8").toString("base64").replace(/=+$/, "");
    }

    _base64_decode(encoded_data: string): string {
        try {
            const padding = (4 - (encoded_data.length % 4)) % 4;
            const decoded = Buffer.from(encoded_data + "=".repeat(padding), "base64");
            return decoded.toString("utf-8");
        } catch {
            throw new Error(`Base64 decryption failed: ${encoded_data}`);
        }
    }

    encrypt_shift(text: string): string {
        const encoded = Array.from(text).map(
            (ch, i) => (ch.charCodeAt(0) + this.key.charCodeAt(i % this.key.length)).toString(16)
        );
        return encoded.join(this.delimiter);
    }

    decrypt_shift(encoded_text: string): string {
        try {
            const codes = encoded_text.split(this.delimiter);
            return codes
                .map((code, i) =>
                    String.fromCharCode(
                        parseInt(code, 16) - this.key.charCodeAt(i % this.key.length)
                    )
                )
                .join("");
        } catch {
            throw new Error(`Error during shift decryption: ${encoded_text}`);
        }
    }

    encrypt_bytes(message: string): string {
        return this._xor(Buffer.from(message, "utf-8")).toString("hex");
    }

    decrypt_bytes(encrypted_data: string): string {
        return this._xor(Buffer.from(encrypted_data, "hex")).toString("utf-8");
    }

    encrypt_binary(plaintext: string): string {
        const xorKey = parseInt(this.numeric_key, 10) % 256;
        return Array.from(plaintext)
            .map((ch) => (ch.charCodeAt(0) ^ xorKey).toString(2).padStart(8, "0"))
            .join("");
    }

    decrypt_binary(encrypted_bits: string): string {
        if (!encrypted_bits || encrypted_bits.length % 8 !== 0) {
            throw new Error("Data biner yang dienkripsi tidak valid atau kosong.");
        }
        const xorKey = parseInt(this.numeric_key, 10) % 256;
        let out = "";
        for (let i = 0; i < encrypted_bits.length; i += 8) {
            out += String.fromCharCode(parseInt(encrypted_bits.slice(i, i + 8), 2) ^ xorKey);
        }
        return out;
    }

    encrypt(data: unknown, only_base64 = false): string {
        if (only_base64) {
            return this._base64_encode(String(data));
        }
        const message =
            typeof data === "string" ? data : JSON.stringify(data);
        if (this.method === "bytes") {
            return this.encrypt_bytes(message);
        }
        if (this.method === "binary") {
            return this.encrypt_binary(message);
        }
        if (this.method === "shift") {
            return this.encrypt_shift(message);
        }
        throw new Error(`Metode enkripsi '${this.method}' tidak dikenali.`);
    }

    decrypt(encrypted_data: string, only_base64 = false): unknown {
        if (only_base64) {
            return this._base64_decode(encrypted_data);
        }
        let decrypted: string;
        if (this.method === "bytes") {
            decrypted = this.decrypt_bytes(encrypted_data);
        } else if (this.method === "binary") {
            decrypted = this.decrypt_binary(encrypted_data);
        } else if (this.method === "shift") {
            decrypted = this.decrypt_shift(encrypted_data);
        } else {
            throw new Error(`Metode dekripsi '${this.method}' tidak dikenali.`);
        }
        try {
            return JSON.parse(decrypted);
        } catch {
            return decrypted;
        }
    }
}