#!/usr/bin/env python3
"""
Figures for item #12, multi-tile seam handling.

  fig11_seam_baseline.png     5-tile mosaic with the four measured seams
  fig13_seam_before_after.png unbuffered vs 150 ft-buffered seam RMS

Numbers are NOT hardcoded here: this script calls measure_seams.main() for
both DEM variants and plots what it returns, so the figure cannot drift
from the measurement. That costs ~2 minutes of sampling per run and is
worth it -- a figure carrying stale numbers is exactly the failure this
project has already had to correct twice.

Run:  python scripts/render_seam_figures.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from render_figures import add_scalebar, add_north_arrow, DPI, FIG_DIR
import measure_seams as ms

ROOT = Path(r"C:\Users\ryans\lidar-portfolio")
UNBUF_TAG = "w120_s0.15_t1.6"
BUF_TAG = "w120_s0.15_t1.6_buf150"
BUFFER_FT = 150

# N/S seams run E-W, so they cut ACROSS this collection's N-S flight lines;
# E/W seams run parallel to them. That split is the figure's whole point.
ORIENT = {"N": "across", "S": "across", "E": "parallel", "W": "parallel"}


def fig_baseline_map():
    """5-tile mosaic with seam locations. Regenerated here so it is
    reproducible -- the first version of this figure was rendered from a
    throwaway inline script and could not be rebuilt."""
    mos = ROOT / "output" / "seams" / "hs_mosaic_unbuffered.tif"
    if not mos.exists():
        print(f"  skipping baseline map, missing {mos.name}")
        return
    T = ms.TILE
    ds = rasterio.open(mos)
    hs = ds.read(1)
    b = ds.bounds
    fig, ax = plt.subplots(figsize=(10, 10), dpi=DPI)
    ax.imshow(hs, cmap="gray", extent=[b.left, b.right, b.bottom, b.top],
              origin="upper", zorder=1)
    for x in (975112.76, 980112.76, 985112.76, 990112.75):
        ax.axvline(x, color="#3399ff", lw=0.7, ls=":", zorder=3)
    for y in (393427.81, 398427.81, 403427.81, 408427.79):
        ax.axhline(y, color="#3399ff", lw=0.7, ls=":", zorder=3)
    for xs, ys in [((T["minx"], T["minx"]), (T["miny"], T["maxy"])),
                   ((T["maxx"], T["maxx"]), (T["miny"], T["maxy"])),
                   ((T["minx"], T["maxx"]), (T["maxy"], T["maxy"])),
                   ((T["minx"], T["maxx"]), (T["miny"], T["miny"]))]:
        ax.plot(xs, ys, color="red", lw=2.2, zorder=4)
    cx, cy = (T["minx"] + T["maxx"]) / 2, (T["miny"] + T["maxy"]) / 2
    ax.text(T["minx"] - 120, cy, "W", color="red", ha="right", va="center",
            fontsize=12, fontweight="bold")
    ax.text(T["maxx"] + 120, cy, "E", color="red", ha="left", va="center",
            fontsize=12, fontweight="bold")
    ax.text(cx, T["maxy"] + 120, "N", color="red", ha="center", va="bottom",
            fontsize=12, fontweight="bold")
    ax.text(cx, T["miny"] - 120, "S", color="red", ha="center", va="top",
            fontsize=12, fontweight="bold")
    ax.text(cx, cy, "980398", color="#3399ff", ha="center", va="center",
            fontsize=11, fontweight="bold")
    ax.legend(handles=[Line2D([0], [0], color="red", lw=2.2, label="measured seam"),
                       Line2D([0], [0], color="#3399ff", lw=0.7, ls=":",
                              label="tile boundary")],
              loc="lower left", fontsize=8, framealpha=0.9)
    ax.set_title("Item #12: five-tile mosaic and the four measured seams\n"
                 "Centre tile 980398 with its edge-sharing neighbours")
    ax.set_xlabel("Easting (ft, EPSG:6405)")
    ax.set_ylabel("Northing (ft, EPSG:6405)")
    add_scalebar(ax, 2500)
    add_north_arrow(ax)
    fig.tight_layout()
    out = FIG_DIR / "fig11_seam_baseline.png"
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


def fig_before_after(u_res, u_base, b_res, b_base):
    sides = ["N", "S", "E", "W"]
    x = np.arange(len(sides), dtype=float)
    x[2:] += 0.55                      # visual gap between the two groups
    w = 0.34

    fig, ax = plt.subplots(figsize=(10, 6.4), dpi=DPI)
    before = [u_res[s]["rms"] for s in sides]
    after = [b_res[s]["rms"] for s in sides]
    base = [u_base[s]["rms"] for s in sides]

    ax.bar(x - w / 2, before, w, label=f"unbuffered", color="#c0392b")
    ax.bar(x + w / 2, after, w, label=f"buffered {BUFFER_FT} ft", color="#2e86c1")
    for xi, bv in zip(x, base):
        ax.plot([xi - w, xi + w], [bv, bv], color="black", lw=2.0, zorder=5)

    for xi, bef, aft in zip(x, before, after):
        pct = 100 * (aft - bef) / bef
        ax.annotate(f"{pct:+.1f}%", xy=(xi, max(bef, aft)),
                    xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=10, fontweight="bold",
                    color="#1a6b1a" if pct < -10 else "#8a6d00")

    # extra headroom so the legend (upper right) and the group labels below
    # it never collide -- they did at 1.30
    ymax = max(before) * 1.52
    ax.axvline((x[1] + x[2]) / 2, color="#888888", ls="--", lw=1.0,
               ymax=0.80)
    label_y = ymax * 0.79
    ax.text((x[0] + x[1]) / 2, label_y,
            "seams that cut ACROSS flight lines",
            ha="center", va="top", fontsize=9.5, style="italic")
    ax.text((x[2] + x[3]) / 2, label_y,
            "seams PARALLEL to flight lines",
            ha="center", va="top", fontsize=9.5, style="italic")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{s} seam" for s in sides])
    ax.set_ylabel("Seam step RMS (ft, International Feet)")
    ax.set_ylim(0, ymax)
    ax.set_title(
        "Buffering removes the edge-effect component, and nothing else\n"
        "Seams crossing the flight lines improve 32–41%; those parallel to them, 4–6%",
        fontsize=12)
    handles, labels = ax.get_legend_handles_labels()
    handles.append(Line2D([0], [0], color="black", lw=2.0))
    labels.append("local natural 3 ft terrain step (per side)")
    ax.legend(handles=handles, labels=labels, fontsize=9, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = FIG_DIR / "fig13_seam_before_after.png"
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


if __name__ == "__main__":
    print("=== measuring unbuffered ===")
    u_res, u_base = ms.main(UNBUF_TAG)
    print("\n=== measuring buffered ===")
    b_res, b_base = ms.main(BUF_TAG)
    print()
    fig_baseline_map()
    fig_before_after(u_res, u_base, b_res, b_base)
