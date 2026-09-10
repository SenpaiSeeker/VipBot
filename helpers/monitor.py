import asyncio
import platform
import time
from datetime import timedelta
from types import SimpleNamespace

import psutil


class ServerMonitor:
    def __init__(self):
        self.boot_time = psutil.boot_time()

    @staticmethod
    def _create_progress_bar(percentage: float, length: int = 10) -> str:
        filled = int(length * percentage // 100)
        return "█" * filled + "░" * (length - filled)

    def _get_uptime(self) -> str:
        return str(timedelta(seconds=int(time.time() - self.boot_time)))

    @staticmethod
    def _format_bytes(size: float) -> str:
        power = 2**10
        n = 0
        labels = {0: "", 1: "K", 2: "M", 3: "G", 4: "T"}
        while size > power:
            size /= power
            n += 1
        return f"{size:.2f} {labels[n]}B"

    def _collect_stats(self) -> SimpleNamespace:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        return SimpleNamespace(
            os=f"{platform.system()} {platform.release()}",
            python=platform.python_version(),
            uptime=self._get_uptime(),
            cpu={
                "percent": cpu_percent,
                "bar": self._create_progress_bar(cpu_percent),
                "freq": (f"{cpu_freq.current:.0f}Mhz" if cpu_freq else "N/A"),
                "cores": psutil.cpu_count(),
            },
            ram={
                "percent": ram.percent,
                "bar": self._create_progress_bar(ram.percent),
                "used": self._format_bytes(ram.used),
                "total": self._format_bytes(ram.total),
            },
            disk={
                "percent": disk.percent,
                "bar": self._create_progress_bar(disk.percent),
                "used": self._format_bytes(disk.used),
                "total": self._format_bytes(disk.total),
            },
            network={
                "sent": self._format_bytes(net.bytes_sent),
                "recv": self._format_bytes(net.bytes_recv),
            },
        )

    async def get_detailed_stats(self) -> SimpleNamespace:
        return await asyncio.to_thread(self._collect_stats)

    def get_detailed_stats_sync(self) -> SimpleNamespace:
        return self._collect_stats()