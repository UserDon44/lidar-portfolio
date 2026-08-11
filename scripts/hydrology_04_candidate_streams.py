#!/usr/bin/env python3
"""
Stage 4a: extract candidate stream networks at a spread of thresholds
(informed by, but not dictated by, the slope-area analysis, since that
signal didn't show a sharp break) and render each over the hillshade
with the ag fields / pivot field in frame, for visual judgment.
"""
import whitebox
import rasterio
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# Project root, resolved from this file's own location so these scripts
# run from any checkout rather than one hardcoded directory.
ROOT = Path(__file__).resolve().parent.parent
HYDRO = ROOT / "output" / "hydrology"
accum_path = HYDRO / "d8_flow_accum_cells.tif"

wbt = whitebox.WhiteboxTools()
wbt.set_working_dir(str(HYDRO))
wbt.verbose = False

CANDIDATES = [50, 150, 500, 1500, 5000, 15000]  # cells; 1 cell = 9 sq ft
cell_area_sqft = 9.0

for t in CANDIDATES:
    out = HYDRO / f"streams_t{t}.tif"
    wbt.extract_streams(flow_accum=str(accum_path), output=str(out), threshold=float(t), zero_background=True)

print("Extraction done. Rendering comparison figure...")

hs_ds = rasterio.open(ROOT / "output" / "hillshade" / "hs_w120_s0.15_t1.6.tif")
hs = hs_ds.read(1)
extent = [hs_ds.bounds.left, hs_ds.bounds.right, hs_ds.bounds.bottom, hs_ds.bounds.top]

fig, axes = plt.subplots(2, 3, figsize=(18, 18), dpi=120)
for ax, t in zip(axes.flat, CANDIDATES):
    ax.imshow(hs, cmap="gray", extent=extent, origin="upper")
    with rasterio.open(HYDRO / f"streams_t{t}.tif") as ds:
        s = ds.read(1)
        nd = ds.nodata
    mask = (s != nd) & (s > 0)
    overlay = np.zeros((*s.shape, 4))
    overlay[mask] = [1, 0.1, 0.1, 1]
    ax.imshow(overlay, extent=extent, origin="upper")
    acres = t * cell_area_sqft / 43560
    ax.set_title(f"threshold={t} cells ({t*cell_area_sqft:.0f} sqft, {acres:.3f} ac)")
    ax.set_xlabel("Easting (ft)")
    ax.set_ylabel("Northing (ft)")

plt.tight_layout()
out = HYDRO / "stream_threshold_comparison.png"
plt.savefig(out)
print("saved", out)
