"""
charts.py
=========
Draws the three dashboard charts with Matplotlib and Seaborn and saves them
as PNG images in static/charts/. The numbers come from the saved CSV data
(through data_manager.get_statistics).
"""

import os
import threading

import matplotlib
matplotlib.use("Agg")            # draw to files, no pop-up windows
from matplotlib.figure import Figure
import seaborn as sns

sns.set_theme(style="whitegrid")

BLUE = "#2F6FDE"
PRIORITY_COLORS = {"High": "#D64545", "Medium": "#E8A33D", "Low": "#3FA66B"}
STATUS_COLORS = {"Pending": "#E8A33D", "In Progress": "#2F6FDE", "Resolved": "#3FA66B"}
BACKGROUND = "#FFFDF7"

CHART_FILES = {
    "category": "category_chart.png",
    "priority": "priority_chart.png",
    "status": "status_chart.png",
}

_chart_lock = threading.Lock()


def _new_figure():
    fig = Figure(figsize=(6, 4))
    fig.patch.set_facecolor(BACKGROUND)
    return fig, fig.subplots()


def _save(fig, path):
    fig.savefig(path, dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())


def _draw_empty_chart(title, path):
    """Shown when there is no data yet, so the page never breaks."""
    fig, ax = _new_figure()
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.text(0.5, 0.5, "No complaint data yet", ha="center", va="center",
            fontsize=13, color="#6B7280", transform=ax.transAxes)
    ax.set_axis_off()
    _save(fig, path)


def _draw_bar_chart(counts, colors, title, xlabel, path):
    """Bar chart (Seaborn) with the number written above each bar."""
    if sum(counts.values()) == 0:
        _draw_empty_chart(title, path)
        return

    labels = list(counts.keys())
    values = list(counts.values())
    fig, ax = _new_figure()
    sns.barplot(x=labels, y=values, hue=labels, palette=colors,
                legend=False, ax=ax)
    for position, value in enumerate(values):
        ax.text(position, value + max(values) * 0.02, str(value),
                ha="center", va="bottom", fontweight="bold")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Number of complaints")
    ax.set_ylim(0, max(values) * 1.2)
    _save(fig, path)


def _draw_status_pie(status_counts, path):
    """Pie chart of complaint statuses (zero-count statuses are left out)."""
    items = [(name, count) for name, count in status_counts.items() if count > 0]
    if not items:
        _draw_empty_chart("Complaints by Status", path)
        return

    fig, ax = _new_figure()
    ax.pie([count for _, count in items],
           labels=[name for name, _ in items],
           colors=[STATUS_COLORS[name] for name, _ in items],
           autopct=lambda percent: f"{percent:.0f}%",
           startangle=90,
           wedgeprops={"edgecolor": "white", "linewidth": 2})
    ax.set_title("Complaints by Status", fontsize=13, fontweight="bold")
    _save(fig, path)


def create_all_charts(stats, chart_dir):
    """Create all three charts and return their file names."""
    os.makedirs(chart_dir, exist_ok=True)
    category_colors = {name: BLUE for name in stats["category_counts"]}

    with _chart_lock:        # Matplotlib should draw one chart at a time
        _draw_bar_chart(stats["category_counts"], category_colors,
                        "Complaints by Category", "Category",
                        os.path.join(chart_dir, CHART_FILES["category"]))
        _draw_bar_chart(stats["priority_counts"], PRIORITY_COLORS,
                        "Complaints by Priority", "Priority",
                        os.path.join(chart_dir, CHART_FILES["priority"]))
        _draw_status_pie(stats["status_counts"],
                         os.path.join(chart_dir, CHART_FILES["status"]))
    return dict(CHART_FILES)
