import * as fs from "fs";
import * as fsp from "fs/promises";
import * as os from "os";

function _sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function _read_proc(path: string): string {
    try {
        return fs.readFileSync(path, "utf-8");
    } catch {
        return "";
    }
}

function _format_bytes(size: number): string {
    const power = 1024;
    let n = 0;
    const labels: Record<number, string> = { 0: "", 1: "K", 2: "M", 3: "G", 4: "T" };
    let s = size;
    while (s > power && n < 4) {
        s /= power;
        n++;
    }
    return `${s.toFixed(2)} ${labels[n]}B`;
}

function _create_progress_bar(percentage: number, length = 10): string {
    const filled = Math.floor((length * percentage) / 100);
    return "\u2588".repeat(filled) + "\u2591".repeat(length - filled);
}

function _timedelta_str(totalSeconds: number): string {
    totalSeconds = Math.max(0, Math.floor(totalSeconds));
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (days > 0) {
        return `${days} day${days > 1 ? "s" : ""}, ${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

interface CpuTimes {
    idle: number;
    total: number;
}

function _cpu_sample(): CpuTimes {
    const lines = _read_proc("/proc/stat").split("\n");
    for (const line of lines) {
        if (line.startsWith("cpu ")) {
            const parts = line.split(/\s+/).slice(1).map(Number);
            let idle = 0;
            if (parts.length >= 4) {
                idle = parts[3];
            }
            const total = parts.reduce((a, b) => a + (b || 0), 0);
            return { idle, total };
        }
    }
    return { idle: 0, total: 1 };
}

function _cpu_freq_mhz(): number | null {
    const lines = _read_proc("/proc/cpuinfo").split("\n");
    for (const line of lines) {
        const m = line.match(/cpu MHz\s*:\s*([\d.]+)/);
        if (m) {
            return Number(m[1]);
        }
    }
    return null;
}

function _ram_meminfo(): { percent: number; used: number; total: number } {
    const info: Record<string, number> = {};
    for (const line of _read_proc("/proc/meminfo").split("\n")) {
        const matches = line.match(/^([A-Za-z()]+):\s+(\d+)\s*kB/);
        if (matches) {
            info[matches[1].replace(/[()]/g, "")] = Number(matches[2]) * 1024;
        }
    }
    const total = info.MemTotal || 1;
    const free = info.MemFree || 0;
    const buffers = info.Buffers || 0;
    const cached = info.Cached || 0;
    const used = total - free - buffers - cached;
    const percent = total > 0 ? Math.round((used / total) * 100) : 0;
    return { percent, used, total };
}

function _net_counters(): { bytes_sent: number; bytes_recv: number } {
    let bytes_sent = 0;
    let bytes_recv = 0;
    for (const line of _read_proc("/proc/net/dev").split("\n").slice(2)) {
        const m = line.match(/:\s*(\d+)\s+(\d+)/);
        if (m) {
            bytes_recv += Number(m[1]);
            bytes_sent += Number(m[2]);
        }
    }
    return { bytes_sent, bytes_recv };
}

async function _statfs(path: string): Promise<{ percent: number; used: number; total: number }> {
    const s = await fsp.statfs(path);
    const total = s.bavail + s.blocks;
    const used = s.blocks - s.bfree;
    const percent = total > 0 ? Math.round((used / total) * 100) : 0;
    return { percent, used: used * s.bsize, total: total * s.bsize };
}

export interface MonitorStats {
    os: string;
    node: string;
    uptime: string;
    cpu: { percent: number; bar: string; freq: string; cores: number };
    ram: { percent: number; bar: string; used: string; total: string };
    disk: { percent: number; bar: string; used: string; total: string };
    network: { sent: string; recv: string };
}

export class ServerMonitor {
    boot_time: number;

    constructor() {
        const m = _read_proc("/proc/stat").match(/^btime\s+(\d+)/m);
        this.boot_time = m ? Number(m[1]) : Math.floor(Date.now() / 1000);
    }

    _get_uptime(): string {
        return _timedelta_str(Math.floor(Date.now() / 1000) - this.boot_time);
    }

    async _collect_stats(): Promise<MonitorStats> {
        const first = _cpu_sample();
        await _sleep(100);
        const second = _cpu_sample();
        const idleDiff = second.idle - first.idle;
        const totalDiff = second.total - first.total;
        const cpuPercent = totalDiff > 0 ? Math.round((1 - idleDiff / totalDiff) * 100) : 0;

        const freq = _cpu_freq_mhz();
        const cores = fs.readFileSync("/proc/cpuinfo", "utf-8").split(/processor\s*:/).length - 1;
        const ram = _ram_meminfo();
        const disk = await _statfs("/");
        const net = _net_counters();

        return {
            os: `${os.platform().charAt(0).toUpperCase() + os.platform().slice(1)} ${os.release()}`,
            node: os.release(),
            uptime: this._get_uptime(),
            cpu: {
                percent: cpuPercent,
                bar: _create_progress_bar(cpuPercent),
                freq: freq !== null ? `${Math.round(freq)}Mhz` : "N/A",
                cores: cores || 1,
            },
            ram: {
                percent: ram.percent,
                bar: _create_progress_bar(ram.percent),
                used: _format_bytes(ram.used),
                total: _format_bytes(ram.total),
            },
            disk: {
                percent: disk.percent,
                bar: _create_progress_bar(disk.percent),
                used: _format_bytes(disk.used),
                total: _format_bytes(disk.total),
            },
            network: {
                sent: _format_bytes(net.bytes_sent),
                recv: _format_bytes(net.bytes_recv),
            },
        };
    }

    async get_detailed_stats(): Promise<MonitorStats> {
        return this._collect_stats();
    }

    get_detailed_stats_sync(): Promise<MonitorStats> {
        return this._collect_stats();
    }
}