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

EXTRA = [10000, 20000, 40000]
for t in EXTRA:
    out = HYDRO / f"streams_t{t}.tif"
    if not out.exists():
        wbt.extract_streams(flow_accum=str(accum_path), output=str(out), threshold=float(t), zero_background=True)

CANDIDATES = [10000, 20000, 40000, 5000]
cell_area_sqft = 9.0

hs_ds = rasterio.open(ROOT / "output" / "hillshade" / "hs_w120_s0.15_t1.6.tif")
hs_full = hs_ds.read(1)

# window covering both the hills (west) and the pivot field + ag fields (east)
# clamp to the tile's actual bounds (980112.76-985112.75, 398427.81-403427.80)
minx, maxx = 980120, 985105
miny, maxy = 399810, 401700
row0, col0 = hs_ds.index(minx, maxy)
row1, col1 = hs_ds.index(maxx, miny)
print("row0,col0,row1,col1:", row0, col0, row1, col1, " raster shape:", hs_full.shape)
hs = hs_full[row0:row1, col0:col1]
extent = [minx, maxx, miny, maxy]

fig, axes = plt.subplots(2, 2, figsize=(20, 9), dpi=130)
for ax, t in zip(axes.flat, CANDIDATES):
    ax.imshow(hs, cmap="gray", extent=extent, origin="upper")
    with rasterio.open(HYDRO / f"streams_t{t}.tif") as ds:
        s_full = ds.read(1)
        nd = ds.nodata
    s = s_full[row0:row1, col0:col1]
    mask = (s != nd) & (s > 0)
    overlay = np.zeros((*s.shape, 4))
    overlay[mask] = [1, 0.1, 0.1, 1]
    ax.imshow(overlay, extent=extent, origin="upper")
    acres = t * cell_area_sqft / 43560
    ax.set_title(f"threshold={t} cells ({acres:.3f} ac)")
    ax.set_xlabel("Easting (ft)")
    ax.set_ylabel("Northing (ft)")
    ax.set_aspect("equal")

plt.tight_layout()
out = HYDRO / "stream_threshold_zoom_compare_high.png"
plt.savefig(out)
print("saved", out)
