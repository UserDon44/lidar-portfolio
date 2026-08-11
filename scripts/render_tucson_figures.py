#!/usr/bin/env python3
"""
Figures for the Tucson Mountains parameter-adaptation case study -- a
second, standalone deliverable separate from the San Xavier QC report
(see CLAUDE.md item #10 for the full derivation story these figures
illustrate). Written to output/figures/tucson_*.png.

Reuses add_scalebar/add_north_arrow from render_figures.py so both
deliverables share one visual style.

Rebuilt around the corrected, real story: what was originally documented
as "five iterations" is four real data points and one that turned out to
be a no-op. Attempt 4 (window widened 33->65 ft) is byte-identical to
attempt 3 -- verified by checksum and an independent from-scratch
pipeline re-run -- so the "window trades detail for reduced speckle"
figure this script used to render was built on a comparison that never
happened, and got cut. The real final step (last-return prefiltering)
doesn't produce a visually dramatic hillshade change either -- speckle
persists at similar density on purpose, a disclosed limitation, not a
fix -- so that comparison is now framed honestly as "looks similar,
here's what actually changed and why" instead of a before/after that
would overclaim what the image shows. See CLAUDE.md item #10's
correction note for the full account.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_figures import add_scalebar, add_north_arrow, DPI, FIG_DIR, DEM_DIR, HS_DIR  # noqa: E402

import rasterio
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Project root, resolved from this file's own location so these scripts
# run from any checkout rather than one hardcoded directory.
ROOT = Path(__file__).resolve().parent.parent

# standard crop for every iteration-comparison figure: a lit slope with
# real gully structure AND dense speckle texture, so a reader can judge
# both "did real relief detail survive" and "did the speckle change"
# from the same frame -- picked by visual inspection, not the default
# full-tile view (too small to see per-cell texture at print size)
CROP_CX, CROP_CY, CROP_HALF = 933000, 472400, 200


def load_crop(path, cx=CROP_CX, cy=CROP_CY, half=CROP_HALF):
    ds = rasterio.open(path)
    row0, col0 = ds.index(cx - half, cy + half)
    row1, col1 = ds.index(cx + half, cy - half)
    arr = ds.read(1)
    return arr[row0:row1, col0:col1], [cx - half, cx + half, cy - half, cy + half]


def panel_row(specs, suptitle, out_name, figsize_per_panel=4.6, dpi=DPI):
    """specs: list of (hillshade_path, label) tuples, same crop for all."""
    n = len(specs)
    fig, axes = plt.subplots(1, n, figsize=(figsize_per_panel * n, figsize_per_panel + 0.6), dpi=dpi)
    if n == 1:
        axes = [axes]
    for ax, (path, label) in zip(axes, specs):
        crop, extent = load_crop(path)
        ax.imshow(crop, cmap="gray", extent=extent, origin="upper", zorder=1)
        ax.set_title(label, fontsize=11)
        ax.set_xlabel("Easting (ft)", fontsize=9)
        ax.tick_params(labelsize=8)
        add_scalebar(ax, 100, loc=(0.04, 0.05))
        add_north_arrow(ax, loc=(0.90, 0.87), size=0.08)
    axes[0].set_ylabel("Northing (ft)", fontsize=9)
    fig.suptitle(suptitle, fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    out = FIG_DIR / out_name
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)
    return out


# ============================================================
# A. Terrain context: measured slope, tile-wide, with percentile
#    annotations. Sets up *why* this tile needed different parameters
#    before showing the iteration story.
# ============================================================
def fig_terrain_context():
    hs_ds = rasterio.open(HS_DIR / "hs_tucson_lastreturn_w33_s0.6_t1.3.tif")
    hs = hs_ds.read(1)
    extent = [hs_ds.bounds.left, hs_ds.bounds.right, hs_ds.bounds.bottom, hs_ds.bounds.top]

    slope_ds = rasterio.open(DEM_DIR / "tucson_slope_probe_pct.tif")
    slope = slope_ds.read(1)
    slope_nodata = slope_ds.nodata
    slope_extent = [slope_ds.bounds.left, slope_ds.bounds.right,
                     slope_ds.bounds.bottom, slope_ds.bounds.top]
    valid = slope != slope_nodata
    disp = np.where(valid, slope, np.nan)

    fig, ax = plt.subplots(figsize=(9, 9), dpi=DPI)
    ax.imshow(hs, cmap="gray", extent=extent, origin="upper", zorder=1)
    im = ax.imshow(disp, cmap="YlOrRd", vmin=0, vmax=150, extent=slope_extent,
                    origin="upper", alpha=0.75, zorder=2)
    cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.03, extend="max")
    cbar.set_label("Slope (%)")

    ax.set_title("Measured terrain slope (vendor ground points, gdaldem slope -p)\n"
                  "Median 28.0% · p90 91.5% · p95 114.2% · p99.9 192.5% "
                  "(near-vertical rock faces)")
    ax.set_xlabel("Easting (ft, EPSG:6405)")
    ax.set_ylabel("Northing (ft, EPSG:6405)")
    add_scalebar(ax, 500)
    add_north_arrow(ax)
    fig.tight_layout()
    out = FIG_DIR / "tucson_fig_A_terrain_context.png"
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


# ============================================================
# B. The two negative results: threshold and slope changes produced no
#    visible change, ruling both out as the controlling lever.
# ============================================================
def fig_negative_results():
    panel_row(
        [
            (HS_DIR / "hs_tucson_w33_s1.0_t3.3.tif", "1. w=33 s=1.0 t=3.3\n(baseline attempt)"),
            (HS_DIR / "hs_tucson_w33_s1.0_t1.3.tif", "2. w=33 s=1.0 t=1.3\nthreshold tightened -- no change"),
            (HS_DIR / "hs_tucson_w33_s0.6_t1.3.tif", "3. w=33 s=0.6 t=1.3\nslope backed off -- no change"),
        ],
        "Two negative results: tightening threshold, then backing off slope, changed nothing\n"
        "(same 400x400 ft crop, window held constant at 33 ft throughout)",
        "tucson_fig_B_negative_results.png",
    )


# ============================================================
# C. The real fix wasn't a geometry knob -- it was changing which points
#    get classified at all. A bar chart, not a hillshade: the effect is
#    in the input data fed to SMRF, not something a rendered surface can
#    show directly.
# ============================================================
def fig_input_filtering():
    import laspy

    las = laspy.open(ROOT / "data" / "raw" / "tucson_mtns_484572_epsg6405.laz").read()
    rn = np.array(las.return_number)
    nr = np.array(las.number_of_returns)
    total = len(rn)
    kept = int((rn == nr).sum())
    dropped = total - kept

    fig, ax = plt.subplots(figsize=(7, 5), dpi=DPI)
    bars = ax.bar(
        ["Kept\n(last/only return)", "Dropped\n(first/intermediate return)"],
        [kept, dropped],
        color=["#2ca02c", "#d62728"],
    )
    for b, v in zip(bars, [kept, dropped]):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,}\n({100*v/total:.1f}%)",
                 ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("Points")
    ax.set_title("Attempt 5's actual change: filter input points by return geometry,\n"
                  "not another SMRF geometry parameter (27,722,077 points total)")
    ax.set_ylim(0, total * 1.15)
    fig.tight_layout()
    out = FIG_DIR / "tucson_fig_C_input_filtering.png"
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


# ============================================================
# D. Attempt 3 vs. final (attempt 5), honestly captioned: this looks
#    similar, on purpose -- the change is upstream of what a hillshade
#    can show, and persistent speckle is a disclosed limitation, not a
#    failure. Not a "before/after" -- that framing already overclaimed
#    once in this project (see the retracted attempt-4 comparison).
# ============================================================
def fig_final_comparison():
    panel_row(
        [
            (HS_DIR / "hs_tucson_w33_s0.6_t1.3.tif", "3. All returns, geometry-only\n(last real attempt before the fix)"),
            (HS_DIR / "hs_tucson_lastreturn_w33_s0.6_t1.3.tif", "5. Last-return prefilter (final)\nvisually similar -- by design, see caption"),
        ],
        "Visually near-identical, and that's expected: the change is which points enter\n"
        "SMRF (Figure C), not classification geometry -- persistent speckle is a disclosed\n"
        "limitation (rock vs. cactus, indistinguishable by return count alone), not a fix",
        "tucson_fig_D_final_comparison.png",
        figsize_per_panel=5.2,
    )


if __name__ == "__main__":
    fig_terrain_context()
    fig_negative_results()
    fig_input_filtering()
    fig_final_comparison()
    print("\nAll Tucson figures written to", FIG_DIR)
