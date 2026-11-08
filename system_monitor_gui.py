#!/usr/bin/env python3
"""
System Resource Monitor
------------------------
A desktop app (Tkinter) showing live CPU, RAM, disk, and network usage,
with rolling graphs of recent history.

Requirements:
  sudo apt install python3-psutil python3-matplotlib
  (or: pip install psutil matplotlib --break-system-packages)

No root required — this only reads public system stats.
"""

import time
import tkinter as tk
from tkinter import ttk
from collections import deque
from datetime import datetime

import psutil
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

HISTORY_LENGTH = 60     # how many data points (seconds) to keep on the graphs
UPDATE_INTERVAL_MS = 1000

BG_COLOR = "#1e1e1e"
FG_COLOR = "#dddddd"
ACCENT = "#4fa3f7"
WARN = "#e05656"
GOOD = "#5cc26a"


class SystemMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Resource Monitor")
        self.root.geometry("900x650")
        self.root.minsize(750, 550)
        self.root.configure(bg=BG_COLOR)

        # History buffers
        self.cpu_history = deque([0] * HISTORY_LENGTH, maxlen=HISTORY_LENGTH)
        self.ram_history = deque([0] * HISTORY_LENGTH, maxlen=HISTORY_LENGTH)
        self.net_sent_history = deque([0] * HISTORY_LENGTH, maxlen=HISTORY_LENGTH)
        self.net_recv_history = deque([0] * HISTORY_LENGTH, maxlen=HISTORY_LENGTH)

        self.last_net = psutil.net_io_counters()
        self.last_sample_time = time.monotonic()

        self._build_ui()
        self._update_loop()

    # ---------------- UI ----------------

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=("Consolas", 11))
        style.configure("Big.TLabel", background=BG_COLOR, foreground=ACCENT, font=("Consolas", 22, "bold"))
        style.configure("Small.TLabel", background=BG_COLOR, foreground="#999999", font=("Consolas", 9))

        # ---- Top summary cards ----
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")

        self.cpu_label = self._make_card(top_frame, "CPU", 0)
        self.ram_label = self._make_card(top_frame, "RAM", 1)
        self.disk_label = self._make_card(top_frame, "Disk", 2)
        self.net_label = self._make_card(top_frame, "Network", 3)

        for i in range(4):
            top_frame.columnconfigure(i, weight=1)

        # ---- Graphs ----
        graph_frame = ttk.Frame(self.root, padding=10)
        graph_frame.pack(fill="both", expand=True)

        self.fig = Figure(figsize=(9, 5), dpi=90, facecolor=BG_COLOR)

        self.ax_cpu = self.fig.add_subplot(311)
        self.ax_ram = self.fig.add_subplot(312)
        self.ax_net = self.fig.add_subplot(313)

        for ax, title in [(self.ax_cpu, "CPU %"), (self.ax_ram, "RAM %"), (self.ax_net, "Network (KB/s)")]:
            ax.set_facecolor("#141414")
            ax.set_title(title, color=FG_COLOR, fontsize=10, loc="left")
            ax.tick_params(colors="#888888", labelsize=8)
            for spine in ax.spines.values():
                spine.set_color("#444444")

        self.fig.tight_layout(pad=2)

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # ---- Bottom info ----
        bottom = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")
        self.detail_label = ttk.Label(bottom, text="", style="Small.TLabel")
        self.detail_label.pack(anchor="w")

    def _make_card(self, parent, title, column):
        frame = ttk.Frame(parent, padding=10)
        frame.grid(row=0, column=column, sticky="nsew", padx=5)
        ttk.Label(frame, text=title, style="Small.TLabel").pack(anchor="w")
        value_label = ttk.Label(frame, text="--", style="Big.TLabel")
        value_label.pack(anchor="w")
        return value_label

    # ---------------- Update loop ----------------

    def _update_loop(self):
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        now = time.monotonic()
        elapsed = max(now - self.last_sample_time, 0.001)
        self.last_sample_time = now
        sent_rate = max(0, net.bytes_sent - self.last_net.bytes_sent) / 1024 / elapsed
        recv_rate = max(0, net.bytes_recv - self.last_net.bytes_recv) / 1024 / elapsed
        self.last_net = net

        self.cpu_history.append(cpu_percent)
        self.ram_history.append(mem.percent)
        self.net_sent_history.append(sent_rate)
        self.net_recv_history.append(recv_rate)

        # Update summary cards
        self.cpu_label.config(text=f"{cpu_percent:.0f}%", foreground=self._color_for(cpu_percent))
        self.ram_label.config(text=f"{mem.percent:.0f}%", foreground=self._color_for(mem.percent))
        self.disk_label.config(text=f"{disk.percent:.0f}%", foreground=self._color_for(disk.percent))
        self.net_label.config(text=f"↑{sent_rate:.0f} ↓{recv_rate:.0f} KB/s", foreground=ACCENT)

        detail = (
            f"RAM: {self._gb(mem.used)} / {self._gb(mem.total)} GB   |   "
            f"Disk: {self._gb(disk.used)} / {self._gb(disk.total)} GB free {self._gb(disk.free)} GB   |   "
            f"Cores: {psutil.cpu_count(logical=True)}   |   "
            f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.detail_label.config(text=detail)

        self._redraw_graphs()

        self.root.after(UPDATE_INTERVAL_MS, self._update_loop)

    def _color_for(self, percent):
        if percent >= 85:
            return WARN
        elif percent >= 60:
            return "#e0b356"
        return GOOD

    def _gb(self, bytes_val):
        return f"{bytes_val / (1024 ** 3):.1f}"

    def _redraw_graphs(self):
        x = range(len(self.cpu_history))

        self.ax_cpu.clear()
        self.ax_cpu.set_facecolor("#141414")
        self.ax_cpu.set_title("CPU %", color=FG_COLOR, fontsize=10, loc="left")
        self.ax_cpu.set_ylim(0, 100)
        self.ax_cpu.plot(x, self.cpu_history, color=ACCENT, linewidth=1.5)
        self.ax_cpu.fill_between(x, self.cpu_history, color=ACCENT, alpha=0.15)
        self.ax_cpu.tick_params(colors="#888888", labelsize=8)

        self.ax_ram.clear()
        self.ax_ram.set_facecolor("#141414")
        self.ax_ram.set_title("RAM %", color=FG_COLOR, fontsize=10, loc="left")
        self.ax_ram.set_ylim(0, 100)
        self.ax_ram.plot(x, self.ram_history, color="#c774e8", linewidth=1.5)
        self.ax_ram.fill_between(x, self.ram_history, color="#c774e8", alpha=0.15)
        self.ax_ram.tick_params(colors="#888888", labelsize=8)

        self.ax_net.clear()
        self.ax_net.set_facecolor("#141414")
        self.ax_net.set_title("Network (KB/s)", color=FG_COLOR, fontsize=10, loc="left")
        max_val = max(max(self.net_sent_history, default=1), max(self.net_recv_history, default=1), 1)
        self.ax_net.set_ylim(0, max_val * 1.2)
        self.ax_net.plot(x, self.net_recv_history, color=GOOD, linewidth=1.3, label="Download")
        self.ax_net.plot(x, self.net_sent_history, color=WARN, linewidth=1.3, label="Upload")
        self.ax_net.legend(loc="upper left", fontsize=7, facecolor="#141414", labelcolor=FG_COLOR, frameon=False)
        self.ax_net.tick_params(colors="#888888", labelsize=8)

        for ax in (self.ax_cpu, self.ax_ram, self.ax_net):
            ax.set_xticks([])
            for spine in ax.spines.values():
                spine.set_color("#444444")

        self.fig.tight_layout(pad=2)
        self.canvas.draw()


def main():
    root = tk.Tk()
    SystemMonitorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
