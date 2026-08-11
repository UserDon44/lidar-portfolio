#!/usr/bin/env python3
"""
Check the flow accumulation raster's four tile edges for crossings above
the stream threshold, to determine whether the main wash enters and/or
exits the tile (a through-flowing channel means any watershed delineated
from within this tile is necessarily a lower bound on the true catchment).
"""
import rasterio
import numpy as np
from scipy import ndimage
from pathlib import Path

# Project root, resolved from this file's own location so these scripts
# run from any checkout rather than one hardcoded directory.
HYDRO = str(Path(__file__).resolve().parent.parent / "output" / "hydrology")
THRESHOLD = 5000  # cells, matches the chosen stream threshold

ds = rasterio.open(f"{HYDRO}/d8_flow_accum_cells.tif")
accum = ds.read(1)
nodata = ds.nodata
h, w = accum.shape
res = ds.res[0]

edges = {
    "NORTH (top row)": accum[0, :],
    "SOUTH (bottom row)": accum[-1, :],
    "WEST (left col)": accum[:, 0],
    "EAST (right col)": accum[:, -1],
}

print(f"Stream threshold: {THRESHOLD} cells ({THRESHOLD*9:,} sq ft, {THRESHOLD*9/43560:.3f} acres)\n")

total_perimeter_ft = 2 * (h + w) * res
crossing_length_ft = 0
crossings = []

for name, row in edges.items():
    above = row > THRESHOLD
    above = np.where(row == nodata, False, above)
    n_cells = above.sum()
    if n_cells:
        # cluster into contiguous crossing segments
        lbl, n = ndimage.label(above)
        for i in range(1, n + 1):
            idx = np.where(lbl == i)[0]
            length_ft = (idx.max() - idx.min() + 1) * res
            max_accum = row[idx].max()
            crossing_length_ft += length_ft
            # compute the actual geo coordinate of the peak-accumulation cell in this crossing
            peak_idx = idx[np.argmax(row[idx])]
            if "NORTH" in name:
                r, c = 0, peak_idx
            elif "SOUTH" in name:
                r, c = h - 1, peak_idx
            elif "WEST" in name:
                r, c = peak_idx, 0
            else:
                r, c = peak_idx, w - 1
            x, y = ds.xy(r, c)
            crossings.append((name, length_ft, max_accum, x, y))
            print(f"{name}: crossing #{i}, width {length_ft:.0f} ft, peak accum {max_accum:,.0f} cells "
                  f"({max_accum*9/43560:.2f} ac), peak location ({x:.1f}, {y:.1f})")
    else:
        print(f"{name}: no crossing above threshold")

print(f"\nTotal tile perimeter: {total_perimeter_ft:,.0f} ft")
print(f"Total crossing width (all edges, above threshold): {crossing_length_ft:.0f} ft "
      f"({100*crossing_length_ft/total_perimeter_ft:.3f}% of perimeter)")
print(f"\nNumber of distinct boundary crossings above threshold: {len(crossings)}")
for c in crossings:
    print(" ", c)
