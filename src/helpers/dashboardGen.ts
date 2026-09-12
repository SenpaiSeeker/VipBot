import { chromium } from "playwright";

export interface DashboardStats {
    cpu: number;
    ram: number;
    disk: number;
}

function _build_dashboard_html(stats_data: DashboardStats): string {
    const bars = [
        { label: "CPU", value: stats_data.cpu, color: "#00ffff" },
        { label: "RAM", value: stats_data.ram, color: "#00ff00" },
        { label: "Disk", value: stats_data.disk, color: "#ff00ff" },
    ];
    const barHtml = bars
        .map((b) => {
            const height = Math.max(0, Math.min(100, b.value));
            return `
                <div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:300px;width:140px;">
                    <div style="color:white;font:700 18px Arial;margin-bottom:10px;">${height}%</div>
                    <div style="width:120px;height:${height * 2.8}px;background:${b.color};border:3px solid white;box-sizing:border-box;"></div>
                    <div style="color:white;font:700 22px Arial;margin-top:16px;">${b.label}</div>
                </div>`;
        })
        .join("");
    return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:black;">
    <div style="width:760px;height:560px;background:black;display:flex;flex-direction:column;align-items:center;justify-content:center;box-sizing:border-box;padding:20px 30px;">
        <div style="color:white;font:700 26px Arial;margin-bottom:30px;">Visualisasi Kesehatan Server</div>
        <div style="display:flex;gap:60px;align-items:flex-end;">
            ${barHtml}
        </div>
        <div style="color:white;font:600 16px Arial;margin-top:24px;">Persentase Penggunaan</div>
    </div>
</body>
</html>`;
}

export class DashboardGenerator {
    async generate_dashboard(stats_data: DashboardStats): Promise<{ buffer: Buffer; name: string }> {
        const html = _build_dashboard_html(stats_data);
        const browser = await chromium.launch();
        try {
            const context = await browser.newContext({
                viewport: { width: 760, height: 560 },
                deviceScaleFactor: 1.2,
            });
            const page = await context.newPage();
            await page.setContent(html);
            await page.waitForLoadState("networkidle");
            const shot = await page.screenshot({ type: "png", omitBackground: false });
            await context.close();
            return { buffer: shot, name: "dashboard_server.png" };
        } finally {
            await browser.close();
        }
    }
}