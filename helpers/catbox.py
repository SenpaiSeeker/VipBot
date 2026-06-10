import os

import aiohttp


class CatboxUploader:
    def __init__(self):
        self.url = "https://telegra.ph/upload"

    async def upload(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} tidak ditemukan.")

        filename = os.path.basename(file_path)
        if "." not in filename:
            filename += ".jpg"

        data = aiohttp.FormData()

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        data.add_field("file", file_bytes, filename=filename, content_type="image/jpeg")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(self.url, data=data) as resp:
                result_json = await resp.json()
                path = result_json[0]["src"]
                return f"https://telegra.ph{path}"
