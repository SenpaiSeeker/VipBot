import { QrCodeGenerator } from "./qrcodeGen";

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 5000;
const REQUEST_TIMEOUT = 15000;

const BACKEND = "https://backend.saweria.co";
const FRONTEND = "https://saweria.co";
const HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    Accept: "application/json, text/plain, */*",
    Referer: "https://saweria.co/",
};

function sleep(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
}

function _extract_next_data(html: string): string | undefined {
    const re = /<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/;
    const m = html.match(re);
    return m ? m[1] : undefined;
}

export class SaweriaScraper extends QrCodeGenerator {
    async get_user_id(username: string): Promise<string | undefined> {
        if (!username || typeof username !== "string") {
            throw new Error(
                "Username harus berupa string dan tidak boleh kosong."
            );
        }
        const url = `${FRONTEND}/${username}`;
        for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
            try {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
                let res: Response;
                try {
                    res = await fetch(url, {
                        headers: HEADERS,
                        signal: controller.signal,
                    });
                } finally {
                    clearTimeout(timer);
                }
                if (res.status === 200) {
                    const text = await res.text();
                    const next_data = _extract_next_data(text);
                    if (next_data) {
                        const user_id = (
                            JSON.parse(next_data).props?.pageProps?.data ?? {}
                        ).id;
                        if (user_id) {
                            return user_id;
                        }
                    }
                }
            } catch {
                // retry below
            }
            if (attempt < MAX_RETRIES - 1) {
                await sleep(RETRY_DELAY_MS);
            }
        }
        return undefined;
    }

    async create_payment(
        user_id: string,
        amount: number,
        name: string,
        email: string,
        message: string,
        creator_name: string = "bot_manager"
    ): Promise<{
        qr_string: string;
        id: string;
        image: {
            buffer: Buffer;
            name: string;
        };
        amount_raw: number;
    }> {
        if (amount < 1000) {
            throw new Error("Jumlah minimum donasi adalah 1000");
        }

        const payload = {
            agree: true,
            notUnderage: true,
            message: message,
            amount: amount,
            payment_type: "qris",
            vote: "",
            currency: "IDR",
            customer_info: {
                first_name: name,
                email: email,
                phone: "",
            },
        };

        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
        let res: Response;
        try {
            res = await fetch(`${BACKEND}/donations/${user_id}`, {
                method: "POST",
                headers: { ...HEADERS, "Content-Type": "application/json" },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });
        } finally {
            clearTimeout(timer);
        }
        if (!res.ok) {
            throw new Error(`Gagal membuat pembayaran: ${await res.text()}`);
        }
        const data = (await res.json()).data;

        const qr_string = data.qr_string;
        const transaction_id = data.id;
        const amount_raw = Number(data.amount_raw);

        const qr_image_bytes = await this.generate(
            qr_string,
            `Created by: ${creator_name}`
        );

        return {
            qr_string,
            id: transaction_id,
            image: {
                buffer: qr_image_bytes,
                name: `${transaction_id}.png`,
            },
            amount_raw,
        };
    }

    async check_paid_status(transaction_id: string): Promise<boolean> {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
        let res: Response;
        try {
            res = await fetch(
                `${BACKEND}/donations/qris/${transaction_id}`,
                { headers: HEADERS, signal: controller.signal }
            );
        } finally {
            clearTimeout(timer);
        }
        if (!res.ok) {
            throw new Error("Transaction ID not found");
        }
        const json = await res.json();
        return json.data.qr_string === "";
    }
}