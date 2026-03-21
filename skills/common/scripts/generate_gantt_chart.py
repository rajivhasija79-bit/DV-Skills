#!/usr/bin/env python3
"""
generate_gantt_chart.py — DV Skills S3 Gantt chart generator
Produces:
  - gantt_schedule.png : Professional milestone Gantt chart (Matplotlib)

Usage:
    python3 generate_gantt_chart.py --data /tmp/<PROJECT>_verif_plan_data.json \
                                     --output ./out/ \
                                     --project APB_UART
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def load_data(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def parse_date(s: str) -> datetime:
    """Try several common date formats."""
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y",
                "%B %d, %Y", "%b %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: '{s}'")


def build_gantt(data: dict, output_dir: Path, project: str):
    try:
        import matplotlib
        matplotlib.use("Agg")          # headless backend — no display needed
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.dates import DateFormatter, MonthLocator
    except ImportError:
        print("ERROR: matplotlib not installed. Run: pip3 install matplotlib")
        sys.exit(1)

    schedule = data.get("schedule", {})
    milestones = schedule.get("milestones", [])

    # ── Build fallback milestones if none provided ────────────────────────
    if not milestones:
        today = datetime.today()
        milestones = [
            {
                "name":       "DV-I",
                "label":      "DV-I — Initial (Register Access)",
                "start":      today.strftime("%Y-%m-%d"),
                "end":        (today + timedelta(weeks=6)).strftime("%Y-%m-%d"),
                "deliverables": ["TB compiles", "Register access test passes",
                                 "Testplan approved"],
                "color":      "#2e6da4",
            },
            {
                "name":       "DV-C",
                "label":      "DV-C — Coding Complete",
                "start":      (today + timedelta(weeks=7)).strftime("%Y-%m-%d"),
                "end":        (today + timedelta(weeks=14)).strftime("%Y-%m-%d"),
                "deliverables": ["All directed tests passing",
                                 "≥90% functional coverage",
                                 "Regression ≥95% pass rate"],
                "color":      "#27ae60",
            },
            {
                "name":       "DV-F",
                "label":      "DV-F — Final Signoff",
                "start":      (today + timedelta(weeks=15)).strftime("%Y-%m-%d"),
                "end":        (today + timedelta(weeks=20)).strftime("%Y-%m-%d"),
                "deliverables": ["100% testplan passing",
                                 "100% code + functional coverage",
                                 "Zero blocking bugs"],
                "color":      "#c0392b",
            },
        ]

    # ── Parse dates ───────────────────────────────────────────────────────
    parsed = []
    for m in milestones:
        try:
            start = parse_date(m.get("start", ""))
            end   = parse_date(m.get("end",   ""))
            parsed.append({**m, "start_dt": start, "end_dt": end})
        except ValueError as e:
            print(f"  WARNING: Could not parse dates for milestone '{m.get('name','?')}': {e}")

    if not parsed:
        print("  ERROR: No valid milestone dates found. Gantt chart skipped.")
        return None

    # ── Plot ──────────────────────────────────────────────────────────────
    fig_w = max(14, (parsed[-1]["end_dt"] - parsed[0]["start_dt"]).days / 14 + 4)
    fig, ax = plt.subplots(figsize=(fig_w, max(5, len(parsed) * 1.8 + 2)))

    ax.set_facecolor("#f8f9fa")
    fig.patch.set_facecolor("white")

    y_labels = []
    y_ticks  = []

    for idx, m in enumerate(parsed):
        y    = idx * 2
        s    = matplotlib.dates.date2num(m["start_dt"])
        e    = matplotlib.dates.date2num(m["end_dt"])
        dur  = e - s
        col  = m.get("color", "#3498db")

        # Main bar
        ax.barh(y, dur, left=s, height=0.9,
                color=col, alpha=0.85, edgecolor="#333333", linewidth=0.8)

        # Duration label inside bar
        label_x = s + dur / 2
        weeks    = int(dur / 7)
        ax.text(label_x, y, f"{weeks}w",
                ha="center", va="center", fontsize=9,
                color="white", fontweight="bold")

        # Milestone name on left
        ax.text(s - 0.5, y, m.get("label", m["name"]),
                ha="right", va="center", fontsize=9,
                color="#333333", fontweight="bold")

        # Deliverables as small text below bar
        delivs = m.get("deliverables", [])
        for di, d in enumerate(delivs[:3]):
            ax.text(s, y - 0.6 - di * 0.22, f"  • {d}",
                    ha="left", va="top", fontsize=7, color="#555555",
                    style="italic")

        y_ticks.append(y)
        y_labels.append(m["name"])

    # ── Axes formatting ───────────────────────────────────────────────────
    all_dates = [m["start_dt"] for m in parsed] + [m["end_dt"] for m in parsed]
    x_min = min(all_dates) - timedelta(days=14)
    x_max = max(all_dates) + timedelta(days=14)

    ax.set_xlim(matplotlib.dates.date2num(x_min),
                matplotlib.dates.date2num(x_max))
    ax.set_ylim(-1.5, (len(parsed) - 1) * 2 + 1.5)

    ax.xaxis_date()
    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%b\n%Y"))
    ax.set_yticks([])
    ax.yaxis.set_visible(False)

    # Today marker
    today_num = matplotlib.dates.date2num(datetime.today())
    ax.axvline(x=today_num, color="#e74c3c", linewidth=1.5,
               linestyle="--", alpha=0.7, zorder=5)
    ax.text(today_num, (len(parsed) - 1) * 2 + 1.2, "Today",
            ha="center", va="bottom", fontsize=8, color="#e74c3c")

    # Gridlines
    ax.xaxis.grid(True, color="#dddddd", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    # Title & legend
    ax.set_title(f"{project} — DV Milestone Schedule",
                 fontsize=14, fontweight="bold", pad=15, color="#1a1a2e")

    legend_patches = [
        mpatches.Patch(color=m.get("color", "#3498db"),
                       label=m.get("label", m["name"]))
        for m in parsed
    ]
    ax.legend(handles=legend_patches, loc="lower right",
              fontsize=8, framealpha=0.9)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color("#cccccc")

    plt.tight_layout(pad=1.5)

    out_path = output_dir / "gantt_schedule.png"
    plt.savefig(str(out_path), dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    print(f"  ✓ Gantt chart:             {out_path}")
    return str(out_path)


def main():
    parser = argparse.ArgumentParser(description="Generate DV milestone Gantt chart PNG")
    parser.add_argument("--data",    required=True, help="Path to verif_plan_data.json")
    parser.add_argument("--output",  required=True, help="Output directory")
    parser.add_argument("--project", required=True, help="Project/IP name")
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"ERROR: Data file not found: {args.data}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = load_data(args.data)
    print(f"\n  Generating Gantt chart for: {args.project}")
    print("=" * 56)
    result = build_gantt(data, output_dir, args.project)
    if result:
        print(f"\n  Done. Gantt chart: {result}\n")


if __name__ == "__main__":
    main()
