import asyncio
import io
import json
import time
from typing import Optional, Tuple

import cloudscraper25 as cloudscraper
from bs4 import BeautifulSoup

from .qrcode_gen import QrCodeGenerator

MAX_RETRIES = 3
RETRY_DELAY = 5
REQUEST_TIMEOUT = 15


class SaweriaScraper(QrCodeGenerator):
    BACKEND = "https://backend.saweria.co"
    FRONTEND = "https://saweria.co"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://saweria.co/",
    }

    def __init__(self):
        super().__init__()
        self.scraper = cloudscraper.create_scraper()

    async def get_user_id(self, username: str) -> Optional[str]:
        if not username or not isinstance(username, str):
            raise ValueError("Username harus berupa string dan tidak boleh kosong.")
        return await asyncio.to_thread(self._fetch_user_id, username)

    def _fetch_user_id(self, username: str):
        url = f"{self.FRONTEND}/{username}"
        for attempt in range(MAX_RETRIES):
            try:
                res = self.scraper.get(url, headers=self.HEADERS, timeout=REQUEST_TIMEOUT)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    next_data = soup.find(id="__NEXT_DATA__")
                    if next_data:
                        user_id = (
                            json.loads(next_data.text)
                            .get("props", {})
                            .get("pageProps", {})
                            .get("data", {})
                            .get("id")
                        )
                        if user_id:
                            return user_id
            except Exception:
                pass
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        return None

    async def create_payment(
        self,
        user_id: str,
        amount: int,
        name: str,
        email: str,
        message: str,
        creator_name: str = "bot_manager",
    ) -> Tuple[str, str, io.BytesIO, int]:
        if amount < 1000:
            raise ValueError("Jumlah minimum donasi adalah 1000")

        payload = {
            "agree": True,
            "notUnderage": True,
            "message": message,
            "amount": amount,
            "payment_type": "qris",
            "vote": "",
            "currency": "IDR",
            "customer_info": {
                "first_name": name,
                "email": email,
                "phone": "",
            },
        }
        data = await asyncio.to_thread(self._post_payment, user_id, payload)
        qr_string = data["qr_string"]
        transaction_id = data["id"]
        amount_raw = data["amount_raw"]

        qr_image_bytes = await self.generate(
            data=qr_string,
            creator_text=f"Created by: {creator_name}",
        )
        qr_image_stream = io.BytesIO(qr_image_bytes)
        qr_image_stream.name = f"{transaction_id}.png"

        return (qr_string, transaction_id, qr_image_stream, amount_raw)

    def _post_payment(self, user_id: str, payload: dict):
        res = self.scraper.post(
            f"{self.BACKEND}/donations/{user_id}",
            json=payload,
            headers=self.HEADERS,
        )
        if not res.ok:
            raise Exception(f"Gagal membuat pembayaran: {res.text}")
        return res.json()["data"]

    async def check_paid_status(self, transaction_id: str) -> bool:
        return await asyncio.to_thread(self._fetch_paid_status, transaction_id)

    def _fetch_paid_status(self, transaction_id: str) -> bool:
        res = self.scraper.get(
            f"{self.BACKEND}/donations/qris/{transaction_id}",
            headers=self.HEADERS,
        )
        if not res.ok:
            raise Exception("Transaction ID not found")
        return res.json()["data"]["qr_string"] == ""