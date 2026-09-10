import asyncio
from types import SimpleNamespace

import aiofiles
import yaml

from .colorize import AnsiColors


class YamlHandler(AnsiColors):
    async def loadAndConvert(self, filePath):
        try:
            async with aiofiles.open(filePath, "r", encoding="utf-8") as file:
                raw_content = await file.read()
            raw_data = await asyncio.to_thread(yaml.safe_load, raw_content)
            return self._to_namespace(raw_data)
        except FileNotFoundError:
            print(
                f"{self.YELLOW}File {self.LIGHT_CYAN}'{filePath}' "
                f"{self.RED}tidak ditemukan.{self.RESET}"
            )
        except yaml.YAMLError as e:
            print(
                f"{self.YELLOW}Kesalahan saat memproses file YAML: "
                f"{self.RED}{e}{self.RESET}"
            )
        return None

    def _to_namespace(self, data):
        if isinstance(data, dict):
            return SimpleNamespace(
                **{str(k): self._to_namespace(v) for k, v in data.items()}
            )
        if isinstance(data, list):
            return [self._to_namespace(item) for item in data]
        return data