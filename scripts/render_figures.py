#!/usr/bin/env python3
"""
Render presentation-quality PNG figures into output/figures/ for the PDF
report. Every figure gets a scale bar, north arrow, and a legend/colorbar
with units explicitly stated (International Feet for all linear
quantities; point density is pts/m^2, the unit QL2 itself is specified in
-- stated explicitly on the figure so it's never ambiguous).

Source data is all International Feet, EPSG:6405 (see CLAUDE.md). North
is already "up" in these projected coordinates -- no rotation needed for
the north arrow.

Convention going forward (see CLAUDE.md "How I want to work"): any figure
generated for review is saved here at render time, not left in the
session scratchpad.
"""
import rasterio
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, Rectangle
from pathlib import Path

ROOT = Path(r"C:\Users\ryans\lidar-portfolio")
DEM_DIR = ROOT / "output" / "dem"
HS_DIR = ROOT / "output" / "hillshade"
FIG_DIR = ROOT / "output" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

DPI = 300


def nice_scalebar_length(extent_ft):
    """Pick a round scale-bar length that's roughly 1/5 of the view width."""
    target = extent_ft / 5
    for candidate in [10, 25, 50, 100, 250, 500, 1000, 2000, 2500, 5000]:
        if candidate >= target:
            return candidate
    return 5000


def add_scalebar(ax, length_ft=None, loc=(0.05, 0.06)):
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    w, h = xlim[1] - xlim[0], ylim[1] - ylim[0]
    if length_ft is None:
        length_ft = nice_scalebar_length(w)
    x0 = xlim[0] + loc[0] * w
    y0 = ylim[0] + loc[1] * h
    tick_h = h * 0.010

    # legibility backing
    pad = h * 0.025
    ax.add_patch(Rectangle((x0 - pad, y0 - pad), length_ft + 2 * pad, tick_h * 2 + h * 0.035 + pad,
                            facecolor="white", edgecolor="none", alpha=0.75, zorder=9, transform=ax.transData))

    ax.plot([x0, x0 + length_ft], [y0, y0], color="black", linewidth=2.5, zorder=10, solid_capstyle="butt")
    for xx in (x0, x0 + length_ft):
        ax.plot([xx, xx], [y0 - tick_h, y0 + tick_h], color="black", linewidth=2, zorder=10)
    ax.text(x0 + length_ft / 2, y0 + tick_h * 1.6, f"{length_ft:,.0f} ft",
             ha="center", va="bottom", fontsize=9, fontweight="bold", zorder=10)


def add_north_arrow(ax, loc=(0.94, 0.88), size=0.06):
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    w, h = xlim[1] - xlim[0], ylim[1] - ylim[0]
    x = xlim[0] + loc[0] * w
    y = ylim[0] + loc[1] * h
    dy = h * size
    pad = h * 0.02
    ax.add_patch(Rectangle((x - dy * 0.7, y - pad), dy * 1.4, dy + dy * 0.55 + pad,
                            facecolor="white", edgecolor="none", alpha=0.75, zorder=9))
    ax.annotate("N", xy=(x, y + dy), xytext=(x, y),
                arrowprops=dict(facecolor="black", edgecolor="black", width=4, headwidth=13, headlength=10),
                ha="center", va="center", fontsize=11, fontweight="bold", zorder=10)


def base_axes(figsize=(10, 10)):
    fig, ax = plt.subplots(figsize=figsize, dpi=DPI)
    ax.set_xlabel("Easting (ft, EPSG:6405)")
    ax.set_ylabel("Northing (ft, EPSG:6405)")
    return fig, ax


def hillshade_bg(ax, path=HS_DIR / "hs_w120_s0.15_t1.6.tif"):
    ds = rasterio.open(path)
    hs = ds.read(1)
    extent = [ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top]
    ax.imshow(hs, cmap="gray", extent=extent, origin="upper", zorder=1)
    return ds


# ============================================================
# 1. Vendor difference raster
# ============================================================
def fig_vendor_diff():
    fig, ax = base_axes()
    hillshade_bg(ax)
    ds = rasterio.open(DEM_DIR / "diff_VENDOR_minus_w120_s0.15_t1.6.tif")
    d = ds.read(1)
    nodata = ds.nodata
    valid = d != nodata
    n = int(valid.sum())
    disp = np.where(valid, d, np.nan)
    extent = [ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top]

    LIM = 1.0  # ft -- matches the already-reported |diff|>1ft outlier threshold
    im = ax.imshow(disp, cmap="coolwarm", vmin=-LIM, vmax=LIM, extent=extent, origin="upper",
                    alpha=0.85, zorder=2)
    cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.03, extend="both")
    cbar.set_label("Vendor minus mine, elevation (ft)")

    ax.set_title(f"Vendor vs. project DEM difference\nRMSE = 0.162 ft, n={n:,} cells, "
                 f"color range clipped to \u00b1{LIM:g} ft")
    add_scalebar(ax, 1000)
    add_north_arrow(ax)
    fig.tight_layout()
    out = FIG_DIR / "fig01_vendor_diff.png"
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


# ============================================================
# 2. Swath offset raster
# ============================================================
def fig_swath_diff():
    fig, ax = base_axes()
    hillshade_bg(ax)
    ds = rasterio.open(DEM_DIR / "diff_swath_600_minus_519.tif")
    d = ds.read(1)
    nodata = ds.nodata
    valid = d != nodata
    n = int(valid.sum())
    disp = np.where(valid, d, np.nan)
    extent = [ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top]

    LIM = 0.5  # ft -- symmetric range chosen to make the systematic +0.124 ft bias visible as a tint, not washed out
    im = ax.imshow(disp, cmap="coolwarm", vmin=-LIM, vmax=LIM, extent=extent, origin="upper",
                    alpha=0.9, zorder=2)
    cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.03, extend="both")
    cbar.set_label("Flight line 600 minus 519, elevation (ft)")

    ax.set_title(f"Flight-line overlap offset (swath 600 \u2212 519)\n"
                 f"Mean = +0.124 ft, RMSE = 0.222 ft, n={n:,} cells")
    add_scalebar(ax, 1000)
    add_north_arrow(ax)
    fig.tight_layout()
    out = FIG_DIR / "fig02_swath_offset.png"
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


# ============================================================
# 3. Point density map, QL2 threshold clearly distinguishable
# ============================================================
def fig_density():
    fig, ax = base_axes()
    ds = rasterio.open(DEM_DIR / "density_count_3ft_aligned.tif")
    count = ds.read(1)
    nodata = ds.nodata
    valid = count != nodata
    cell_ft = ds.res[0]
    cell_m2 = (cell_ft * 0.3048) ** 2
    density = np.where(valid, count / cell_m2, np.nan)
    extent = [ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top]

    void = valid & (count == 0)
    below = valid & (density < 2.0) & (count > 0)
    ok = valid & (density >= 2.0)

    cls = np.full(count.shape, np.nan)
    cls[ok] = 2
    cls[below] = 1
    cls[void] = 0

    from matplotlib.colors import ListedColormap, BoundaryNorm
    cmap = ListedColormap(["#d62728", "#ffbf00", "#2ca02c"])
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)
    ax.imshow(cls, cmap=cmap, norm=norm, extent=extent, origin="upper", zorder=2)

    pct_void = 100 * void.sum() / valid.sum()
    pct_below_combined = 100 * (void.sum() + below.sum()) / valid.sum()

    from matplotlib.patches import Patch
    legend_elems = [
        Patch(facecolor="#2ca02c", label=f"Meets QL2 (\u2265 2 pts/m\u00b2) \u2014 {100-pct_below_combined:.1f}% of tile"),
        Patch(facecolor="#ffbf00", label=f"Below QL2 minimum, not void \u2014 {pct_below_combined-pct_void:.1f}%"),
        Patch(facecolor="#d62728", label=f"Void, zero returns \u2014 {pct_void:.2f}%"),
    ]
    ax.legend(handles=legend_elems, loc="upper left", fontsize=8.5, framealpha=0.9)

    ax.set_title("First-return point density vs. QL2 minimum (2 pts/m\u00b2)\n"
                 f"Mean 3.70 pts/m\u00b2 tile-wide; {pct_below_combined:.1f}% of cells locally below spec "
                 "(density in points/m\u00b2; grid cells are 3 ft)")
    add_scalebar(ax, 1000)
    add_north_arrow(ax)
    fig.tight_layout()
    out = FIG_DIR / "fig03_density_ql2.png"
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


# ============================================================
# 4. CHM
# ============================================================
def fig_chm():
    fig, ax = base_axes()
    hillshade_bg(ax)
    ds = rasterio.open(DEM_DIR / "chm.tif")
    chm = ds.read(1)
    nodata = ds.nodata
    valid = (chm != nodata) & np.isfinite(chm)
    extent = [ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top]

    VMAX = 15.0  # ft -- covers roof-scale (~8ft) with margin; the 72.87ft pole is intentionally off-scale
    show = np.where(valid & (chm > 1.0), chm, np.nan)  # declutter: only show cells >1ft above ground
    im = ax.imshow(show, cmap="YlOrRd", vmin=0, vmax=VMAX, extent=extent, origin="upper",
                   alpha=0.9, zorder=2)
    cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.03, extend="max")
    cbar.set_label("Height above ground (ft)")

    ax.set_title("Canopy/structure height model (DSM \u2212 DEM)\n"
                 f"Color range 0\u2013{VMAX:g} ft (clipped); max in tile is 72.87 ft (utility pole, off-scale)")
    add_scalebar(ax, 1000)
    add_north_arrow(ax)
    fig.tight_layout()
    out = FIG_DIR / "fig04_chm.png"
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


# ============================================================
# 5-7. Three key hillshades
# ============================================================
def fig_hillshade(path, name, title, scalebar_ft=1000):
    fig, ax = base_axes()
    ds = rasterio.open(path)
    hs = ds.read(1)
    extent = [ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top]
    ax.imshow(hs, cmap="gray", extent=extent, origin="upper", zorder=1)
    ax.set_title(title)
    add_scalebar(ax, scalebar_ft)
    add_north_arrow(ax)
    fig.tight_layout()
    out = FIG_DIR / name
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


if __name__ == "__main__":
    fig_vendor_diff()
    fig_swath_diff()
    fig_density()
    fig_chm()
    fig_hillshade(HS_DIR / "hs_VENDOR.tif", "fig05_hillshade_vendor.png",
                  "Hillshade \u2014 vendor delivered classification (baseline)")
    fig_hillshade(HS_DIR / "hs_w120_s0.15_t1.6.tif", "fig06_hillshade_w120.png",
                  "Hillshade \u2014 project SMRF result (window=120ft, slope=0.15, threshold=1.6ft)")
    fig_hillshade(HS_DIR / "hs_w60_t16.tif", "fig07_hillshade_w60.png",
                  "Hillshade \u2014 SMRF window=60ft, threshold=1.6ft (first attempt, "
                  "near-identical to w120 \u2014 supports item #1)")
    print("\nAll figures written to", FIG_DIR)
