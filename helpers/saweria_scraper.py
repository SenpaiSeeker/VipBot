import asyncio
import io
import json
from typing import Optional, Tuple

import cloudscraper25 as cloudscraper
from bs4 import BeautifulSoup

from .patcher import Object
from .qrcode_gen import QrCodeGenerator


class SaweriaScraper(Object, QrCodeGenerator):
    _ns_alias = "payment"
    BACKEND = "https://backend.saweria.co"
    FRONTEND = "https://saweria.co"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://saweria.co/",
    }

    def __init__(self, client=None, saweria_user_id: Optional[str] = None):
        if isinstance(client, str) and saweria_user_id is None:
            saweria_user_id = client
            client = None
        super().__init__(client)
        self.saweria_user_id = saweria_user_id
        self.scraper = cloudscraper.create_scraper()

    def close(self):
        try:
            self.scraper.close()
        except Exception:
            pass

    async def get_user_id(self, username: str) -> Optional[str]:
        if not username or not isinstance(username, str):
            raise ValueError("Username harus berupa string dan tidak boleh kosong.")

        def _sync_get_with_retries(retries=3, delay=5):
            url = f"{self.FRONTEND}/{username}"
            for attempt in range(retries):
                try:
                    res = self.scraper.get(url, headers=self.HEADERS, timeout=15)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "html.parser")
                        next_data = soup.find(id="__NEXT_DATA__")
                        if next_data:
                            data = json.loads(next_data.text)
                            user_id = (
                                data.get("props", {})
                                .get("pageProps", {})
                                .get("data", {})
                                .get("id")
                            )
                            if user_id:
                                return user_id
                except Exception:
                    pass
                if attempt < retries - 1:
                    import time

                    time.sleep(delay)
            return None

        try:
            return await asyncio.to_thread(_sync_get_with_retries)
        finally:
            self.close()

    async def create_payment(
        self,
        amount: int,
        name: str,
        email: str,
        message: str,
        creator_name: str = "bot_manager",
    ) -> Tuple[str, str, io.BytesIO, int]:
        if not self.saweria_user_id:
            raise ValueError("SAWERIA_USER_ID belum diatur")

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

        def _sync_post():
            res = self.scraper.post(
                f"{self.BACKEND}/donations/{self.saweria_user_id}",
                json=payload,
                headers=self.HEADERS,
                timeout=20,
            )
            if not res.ok:
                raise Exception(f"Gagal membuat pembayaran: {res.text}")
            return res.json()["data"]

        try:
            data = await asyncio.to_thread(_sync_post)
        finally:
            self.close()
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

    async def check_paid_status(
        self,
        transaction_id: str,
        expected_amount: Optional[int] = None,
    ) -> bool:
        def _sync_get():
            res = self.scraper.get(
                f"{self.BACKEND}/donations/qris/{transaction_id}",
                headers=self.HEADERS,
                timeout=20,
            )
            if not res.ok:
                raise Exception("Transaction ID not found")

            data = res.json().get("data") or {}
            if data.get("qr_string") != "":
                return False

            if expected_amount is not None and data.get("amount_raw") is not None:
                try:
                    paid_amount = int(data.get("amount_raw"))
                except (TypeError, ValueError):
                    return False
                if paid_amount != int(expected_amount):
                    return False

            return True

        try:
            return await asyncio.to_thread(_sync_get)
        finally:
            self.close()


SaweriaScraper.SaweriaScraper = SaweriaScraper
