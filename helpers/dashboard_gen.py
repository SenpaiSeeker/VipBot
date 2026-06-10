import asyncio
import io
from concurrent.futures import ThreadPoolExecutor

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

executor = ThreadPoolExecutor(max_workers=4)


class DashboardGenerator:
    def _sync_generate_dashboard(self, stats_data):
        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor("black")
        ax.set_facecolor("black")

        categories = ["CPU", "RAM", "Disk"]
        values = [
            stats_data["cpu"],
            stats_data["ram"],
            stats_data["disk"],
        ]
        colors = ["cyan", "lime", "magenta"]

        bars = ax.bar(
            categories,
            values,
            color=colors,
            edgecolor="white",
            linewidth=1.5,
        )
        ax.set_ylim(0, 100)
        ax.set_ylabel(
            "Persentase Penggunaan",
            color="white",
            fontsize=12,
        )
        ax.tick_params(colors="white", labelsize=12)
        ax.set_title(
            "Visualisasi Kesehatan Server",
            color="white",
            fontsize=16,
            fontweight="bold",
        )

        for bar in bars:
            yval = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                yval + 2,
                f"{yval}%",
                ha="center",
                va="bottom",
                color="white",
                fontsize=12,
                fontweight="bold",
            )

        buf = io.BytesIO()
        plt.savefig(
            buf,
            format="png",
            facecolor=fig.get_facecolor(),
            bbox_inches="tight",
        )
        buf.seek(0)
        plt.close(fig)
        buf.name = "dashboard_server.png"
        return buf

    async def generate_dashboard(self, stats_data):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            executor, self._sync_generate_dashboard, stats_data
        )
