import * as crypto from "crypto";
import QRCode from "qrcode";
import { chromium, type Browser } from "playwright";

const _CARD_SELECTOR = ".qris-card";

let _browserPromise: Promise<Browser> | undefined;

async function _getBrowser(): Promise<Browser> {
    if (!_browserPromise) {
        _browserPromise = chromium.launch().finally(() => {
            _browserPromise = undefined;
        });
    }
    return _browserPromise;
}

function _random_int(min: number, max: number): number {
    return min + Math.floor(Math.random() * (max - min + 1));
}

function _build_qris_html(
    clean_name: string,
    nmid_str: string,
    qr_base64: string,
    random_version: string
): string {
    return `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

                body {
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    font-family: 'Inter', sans-serif;
                }

                .qris-card {
                    background-color: #ffffff;
                    background-image: linear-gradient(#f0f0f0 1.5px, transparent 1.5px), linear-gradient(90deg, #f0f0f0 1.5px, transparent 1.5px);
                    background-size: 38px 38px;
                    width: 600px;
                    height: 850px;
                    box-sizing: border-box;
                    position: relative;
                    overflow: hidden;
                }

                .shape-left {
                    position: absolute;
                    left: -15px;
                    top: 220px;
                    width: 160px;
                    height: 340px;
                    background-color: #DA251D;
                    clip-path: polygon(0 0, 100% 50%, 0 100%);
                    z-index: 1;
                }

                .shape-right-bottom {
                    position: absolute;
                    right: 0;
                    bottom: 0;
                    width: 380px;
                    height: 320px;
                    background-color: #DA251D;
                    clip-path: polygon(100% 0, 0 100%, 100% 100%);
                    z-index: 1;
                }

                .content-wrapper {
                    position: absolute;
                    top: 0; left: 0; right: 0; bottom: 0;
                    z-index: 2;
                    display: flex;
                    flex-direction: column;
                    padding: 35px 45px 30px 45px;
                }

                .header-row {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    width: 100%;
                    padding-bottom: 25px;
                }

                .qris-block {
                    display: flex;
                    flex-direction: column;
                }

                .qris-group {
                    display: flex;
                    align-items: center;
                }

                .qris-logo {
                    height: 38px;
                    margin-right: 12px;
                }

                .qris-separator {
                    width: 2.5px;
                    height: 34px;
                    background-color: #000000;
                    margin-right: 12px;
                    border-radius: 1px;
                }

                .qris-text {
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    line-height: 1.15;
                }

                .qris-text span {
                    font-weight: 800;
                    font-size: 13.5px;
                    color: #000000;
                    letter-spacing: 0.1px;
                }

                .qris-underline {
                    width: 295px;
                    height: 5.5px;
                    background-color: #000000;
                    margin-top: 10px;
                }

                .gpn-logo {
                    height: 55px;
                }

                .merchant-info {
                    text-align: center;
                    margin-top: 25px;
                }

                .merchant-name {
                    font-size: 38px;
                    font-weight: 900;
                    color: #000000;
                    letter-spacing: 0.5px;
                    margin: 0;
                }

                .nmid {
                    font-size: 24px;
                    font-weight: 700;
                    color: #333333;
                    margin-top: 12px;
                }

                .terminal-id {
                    font-size: 24px;
                    font-weight: 800;
                    color: #333333;
                    margin-top: 6px;
                }

                .qr-section {
                    display: flex;
                    justify-content: center;
                    margin-top: 25px;
                }

                .qr-border-outer {
                    border: 2px solid #e0e0e0;
                    padding: 12px;
                    background-color: #ffffff;
                    border-radius: 8px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
                }

                .qr-code-img {
                    width: 320px;
                    height: 320px;
                    display: block;
                }

                .aspi-section {
                    text-align: center;
                    margin-top: 20px;
                }

                .aspi-title {
                    font-size: 18px;
                    font-weight: 900;
                    color: #222222;
                    letter-spacing: 0.5px;
                }

                .aspi-sub {
                    font-size: 12px;
                    font-weight: 500;
                    color: #666666;
                    margin-top: 4px;
                }

                .aspi-link {
                    font-size: 12px;
                    font-weight: 800;
                    color: #222222;
                    margin-top: 2px;
                }

                .footer-row {
                    margin-top: auto;
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-end;
                    width: 100%;
                }

                .footer-left {
                    font-size: 13px;
                    color: #888888;
                    line-height: 1.6;
                    font-weight: 500;
                    margin-bottom: -5px;
                }

                .footer-right {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 25px;
                    margin-right: -15px;
                }

                .instruction {
                    font-size: 14px;
                    font-weight: 700;
                    color: #ffffff;
                    text-align: right;
                    width: 100%;
                    margin-right: 5px;
                }

                .icons-row {
                    display: flex;
                    gap: 24px;
                    justify-content: center;
                    width: 100%;
                }

                .icon-item {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 8px;
                }

                .icon-circle {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background-color: #ffffff;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }

                .icon-circle svg {
                    width: 22px;
                    height: 22px;
                    fill: #D2142A;
                }

                .icon-label {
                    font-size: 8px;
                    color: #ffffff;
                    text-align: center;
                    font-weight: 700;
                    line-height: 1.2;
                }
            </style>
        </head>
        <body>
            <div class="qris-card">
                <div class="shape-left"></div>
                <div class="shape-right-bottom"></div>

                <div class="content-wrapper">
                    <div class="header-row">
                        <div class="qris-block">
                            <div class="qris-group">
                                <img src="https://upload.wikimedia.org/wikipedia/commons/a/a2/Logo_QRIS.svg" class="qris-logo" />
                                <div class="qris-separator"></div>
                                <div class="qris-text">
                                    <span>QR Code Standar</span>
                                    <span>Pembayaran Nasional</span>
                                </div>
                            </div>
                            <div class="qris-underline"></div>
                        </div>
                        <img src="https://upload.wikimedia.org/wikipedia/commons/8/83/Gerbang_Pembayaran_Nasional_logo.svg" class="gpn-logo" />
                    </div>

                    <div class="merchant-info">
                        <div class="merchant-name">${clean_name}</div>
                        <div class="nmid">${nmid_str}</div>
                        <div class="terminal-id">A01</div>
                    </div>

                    <div class="qr-section">
                        <div class="qr-border-outer">
                            <img class="qr-code-img" src="data:image/png;base64,${qr_base64}" />
                        </div>
                    </div>

                    <div class="aspi-section">
                        <div class="aspi-title">SATU QRIS UNTUK SEMUA</div>
                        <div class="aspi-sub">Cek aplikasi penyelenggara di:</div>
                        <div class="aspi-link">www.aspi-qris.id</div>
                    </div>

                    <div class="footer-row">
                        <div class="footer-left">
                            <div>Dicetak oleh: ${clean_name}</div>
                            <div>Versi cetak: ${random_version}</div>
                        </div>

                        <div class="footer-right">
                            <div class="instruction">Cara bayar dengan QRIS:</div>
                            <div class="icons-row">
                                <div class="icon-item">
                                    <div class="icon-circle">
                                        <svg viewBox="0 0 24 24">
                                            <path d="M17 1H7c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-2-2-2zm-5 21c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm5-4H7V4h10v14z"/>
                                        </svg>
                                    </div>
                                    <div class="icon-label">Buka Aplikasi<br>Berlogo QRIS</div>
                                </div>

                                <div class="icon-item">
                                    <div class="icon-circle">
                                        <svg viewBox="0 0 24 24">
                                            <path d="M20 4H4c-1.11 0-1.99.89-1.99 2L2 18c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/>
                                        </svg>
                                    </div>
                                    <div class="icon-label">Scan dan Cek<br>Nominal</div>
                                </div>

                                <div class="icon-item">
                                    <div class="icon-circle">
                                        <svg viewBox="0 0 24 24">
                                            <path d="M4 4h6v6H4zm2 2v2h2V6zm8-2h6v6h-6zm2 2v2h2V6zM4 14h6v6H4zm2 2v2h2v-2zm15 1h-2v-2h-2v2h-2v2h2v2h2v-2h2z"/>
                                        </svg>
                                    </div>
                                    <div class="icon-label">Bayar</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
    `;
}

export class QrCodeGenerator {
    async _render_html_with_playwright(
        html_content: string,
        selector: string = _CARD_SELECTOR,
        width: number = 600,
        height: number = 860
    ): Promise<Buffer> {
        const browser = await _getBrowser();
        const context = await browser.newContext({
            viewport: { width, height },
            deviceScaleFactor: 3.0,
        });
        try {
            const page = await context.newPage();
            await page.setContent(html_content);
            await page.waitForLoadState("networkidle");
            const element_handle = await page.$(selector);
            if (!element_handle) {
                throw new Error("Could not find the target selector.");
            }
            const buffer: Buffer = await element_handle.screenshot({
                type: "png",
                omitBackground: true,
            });
            return buffer;
        } finally {
            await context.close();
        }
    }

    async generate(
        data: string,
        creator_text?: string | null
    ): Promise<Buffer> {
        const qr_base64 = (
            await QRCode.toBuffer(data, {
                errorCorrectionLevel: "H",
                margin: 0,
                width: 320,
            })
        ).toString("base64");

        let clean_name = creator_text || "CAHAYA STORE";
        if (clean_name.includes("Created by:")) {
            clean_name = clean_name.replace("Created by:", "").trim();
        }
        clean_name = clean_name.toUpperCase();

        const hasher = crypto.createHash("sha256").update(clean_name, "utf-8");
        const hash_hex = hasher.digest("hex");
        const hash_int = BigInt(`0x${hash_hex}`);
        let nmid_digits = hash_int
            .toString()
            .split("")
            .filter((c) => c >= "0" && c <= "9")
            .join("")
            .slice(0, 13);
        while (nmid_digits.length < 13) {
            nmid_digits += "0";
        }
        const nmid_str = `NMID : ID${nmid_digits}`;

        const random_version = `1.0.${String(_random_int(10, 99)).padStart(2, "0")}.${String(_random_int(1, 12)).padStart(2, "0")}.${String(_random_int(1, 28)).padStart(2, "0")}`;

        const html_template = _build_qris_html(
            clean_name,
            nmid_str,
            qr_base64,
            random_version
        );

        return this._render_html_with_playwright(
            html_template,
            _CARD_SELECTOR,
            600,
            860
        );
    }
}