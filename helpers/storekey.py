import argparse
import sys

import setproctitle

from .logger import LoggerHandler


class KeyManager:
    def __init__(self):
        self.logger = LoggerHandler()

    def handle_arguments(self):
        parser = argparse.ArgumentParser(
            description="Pemuat konfigurasi skrip.",
            epilog="Argumen --key dan --env wajib disertakan untuk menjalankan skrip.",
        )
        parser.add_argument("--key", type=str, help="Kunci rahasia untuk enkripsi data.")
        parser.add_argument("--env", type=str, help="Nama file environment yang akan dimuat")
        args = parser.parse_args()

        if not args.key or not args.env:
            self.logger.print(
                f"{self.logger.RED}Argumen --key dan --env harus disertakan "
                f"untuk menjalankan bot."
            )
            sys.exit(1)

        self.redact_key_arg()
        return args.key, args.env

    def redact_key_arg(self):
        cleaned_argv = []
        skip_next = False
        for i, arg in enumerate(sys.argv):
            if skip_next:
                skip_next = False
                continue
            if arg == "--key":
                cleaned_argv.extend([arg, "[REDACTED]"])
                if i + 1 < len(sys.argv):
                    skip_next = True
            else:
                cleaned_argv.append(arg)
        try:
            setproctitle.setproctitle(" ".join(cleaned_argv))
        except Exception as e:
            self.logger.print(
                f"{self.logger.YELLOW}Gagal menyembunyikan argumen proses: {e}"
            )