#!/usr/bin/env python3
"""
Stage 3: slope-area break-point analysis to derive a defensible stream
channelization threshold from this DEM's own geomorphology, rather than
importing a constant from humid-region literature.

Method: bin all cells by log10(contributing area), take the median slope
per bin, and look for where the log-log slope-area trend breaks from a
shallow/flat hillslope regime to a steeply declining power-law channel
regime. That break point is the channel-initiation threshold.
"""
import rasterio
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# Project root, resolved from this file's own location so these scripts
# run from any checkout rather than one hardcoded directory.
HYDRO = str(Path(__file__).resolve().parent.parent / "output" / "hydrology")

accum_ds = rasterio.open(f"{HYDRO}/d8_flow_accum_cells.tif")
accum = accum_ds.read(1).astype(np.float64)
accum_nodata = accum_ds.nodata

slope_ds = rasterio.open(f"{HYDRO}/slope_pct.tif")
slope = slope_ds.read(1).astype(np.float64)
slope_nodata = slope_ds.nodata

cell_ft = accum_ds.res[0]
cell_area_sqft = cell_ft ** 2
print(f"cell size: {cell_ft} ft, cell area: {cell_area_sqft} sq ft")

valid = (accum != accum_nodata) & (slope != slope_nodata) & (accum >= 1) & np.isfinite(slope)
print(f"valid cells: {valid.sum():,} / {accum.size:,}")

# Restrict to natural terrain west of the wash (x < 982000 ft), based on
# this project's extensive prior mapping this session: hills/residential
# consistently fall west of ~x=982000, the wash runs ~982600-983000, and
# ag fields are east of that. This avoids contaminating the slope-area
# signal with the ag fields' engineered (non-natural-drainage) geometry.
rows, cols = np.indices(accum.shape)
xs = accum_ds.transform.c + cols * accum_ds.transform.a
west_mask = xs < 982000
valid = valid & west_mask
print(f"valid cells restricted to natural terrain (x<982000 ft): {valid.sum():,}")

area_sqft = accum[valid] * cell_area_sqft
area_acres = area_sqft / 43560.0
slp = slope[valid]

log_area = np.log10(area_sqft)
# log-spaced bins across the observed range
n_bins = 60
bin_edges = np.linspace(log_area.min(), log_area.max(), n_bins + 1)
bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
median_slope = np.full(n_bins, np.nan)
n_per_bin = np.zeros(n_bins, dtype=int)

for i in range(n_bins):
    m = (log_area >= bin_edges[i]) & (log_area < bin_edges[i + 1])
    n_per_bin[i] = m.sum()
    if m.sum() >= 20:
        median_slope[i] = np.median(slp[m])

# local log-log gradient d(log slope)/d(log area) via finite differences
valid_bins = np.isfinite(median_slope) & (median_slope > 0)
lb_centers = bin_centers[valid_bins]
lb_logslope = np.log10(median_slope[valid_bins])
gradient = np.gradient(lb_logslope, lb_centers)

print("\nbin_center_log10(sqft)  area_sqft   area_acres   median_slope%  n_cells  local_gradient")
for i, c in enumerate(bin_centers):
    if np.isfinite(median_slope[i]):
        a_sqft = 10 ** c
        idx_in_valid = np.where(lb_centers == c)[0]
        grad_str = f"{gradient[idx_in_valid[0]]:.3f}" if len(idx_in_valid) else "  n/a"
        print(f"{c:8.3f}  {a_sqft:10.0f}  {a_sqft/43560:9.3f}  {median_slope[i]:12.2f}  {n_per_bin[i]:7d}  {grad_str}")

# plot
fig, ax = plt.subplots(figsize=(9, 6), dpi=130)
ax.scatter(lb_centers, lb_logslope, s=15)
ax2 = ax.twinx()
ax2.plot(lb_centers, gradient, color="red", alpha=0.6, label="local d(log slope)/d(log area)")
ax2.axhline(0, color="red", linewidth=0.5, linestyle=":")
ax.set_xlabel("log10(contributing area, sq ft)")
ax.set_ylabel("log10(median slope, %)")
ax2.set_ylabel("local gradient (red)", color="red")
ax.set_title("Slope-area relationship -- channel initiation break point")

# secondary x-axis in acres for readability
def sqft_log_to_acres_label(x):
    return f"{10**x/43560:.2f}"
xticks = ax.get_xticks()
ax3 = ax.secondary_xaxis('top')
ax3.set_xticks(xticks)
ax3.set_xticklabels([sqft_log_to_acres_label(x) for x in xticks])
ax3.set_xlabel("contributing area (acres)")

plt.tight_layout()
out = f"{HYDRO}/slope_area_analysis_west_natural.png"
plt.savefig(out)
print("\nsaved", out)
