import asyncio

import aiofiles
import yaml

from .colorize import AnsiColors
from .patcher import DataObject


class YamlHandler(AnsiColors):
    def __init__(self):
        super().__init__()

    async def loadAndConvert(self, filePath):
        try:
            async with aiofiles.open(filePath, "r", encoding="utf-8") as file:
                raw_content = await file.read()
            rawData = await asyncio.to_thread(yaml.safe_load, raw_content)
            return self._convertToNamespace(rawData)
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

    def _convertToNamespace(self, data):
        if isinstance(data, dict):
            string_keyed_dict = {
                str(k): self._convertToNamespace(v) for k, v in data.items()
            }
            return DataObject(**string_keyed_dict)
        elif isinstance(data, list):
            return [self._convertToNamespace(item) for item in data]
        else:
            return data
