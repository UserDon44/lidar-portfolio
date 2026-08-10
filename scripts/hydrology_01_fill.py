#!/usr/bin/env python3
"""
Stage 1 of hydrologic analysis: breach depressions (least-cost, minimal
terrain modification), then fill whatever the breach step can't resolve.
Reports fill/breach impact by direct DEM differencing -- not a tool
summary line -- so location and magnitude are independently verifiable.

Units are International Feet (EPSG:6405).
"""
import whitebox
import rasterio
import numpy as np
from pathlib import Path

ROOT = Path(r"C:\Users\ryans\lidar-portfolio")
DEM = ROOT / "output" / "dem" / "dem_w120_s0.15_t1.6.tif"
HYDRO = ROOT / "output" / "hydrology"
HYDRO.mkdir(parents=True, exist_ok=True)

wbt = whitebox.WhiteboxTools()
wbt.set_working_dir(str(HYDRO))
wbt.verbose = True

breached = HYDRO / "dem_01_breached.tif"
filled = HYDRO / "dem_02_filled.tif"

print("=== Step 1: BreachDepressionsLeastCost ===")
wbt.breach_depressions_least_cost(
    dem=str(DEM), output=str(breached),
    dist=1000, min_dist=True, fill=False,
)

print("\n=== Step 2: FillDepressions on any remainder ===")
wbt.fill_depressions(
    dem=str(breached), output=str(filled),
    fix_flats=True,
)

print("\n=== Differencing for impact report ===")
with rasterio.open(DEM) as ds:
    orig = ds.read(1).astype(np.float64)
    nodata = ds.nodata
    profile = ds.profile
    cell_ft = ds.res[0]

with rasterio.open(breached) as ds:
    brch = ds.read(1).astype(np.float64)

with rasterio.open(filled) as ds:
    fin = ds.read(1).astype(np.float64)

valid = (orig != nodata) & (brch != nodata) & (fin != nodata)

d_breach = np.where(valid, brch - orig, np.nan)      # breach-only impact
d_residual = np.where(valid, fin - brch, np.nan)     # fill-on-top-of-breach impact
d_total = np.where(valid, fin - orig, np.nan)        # total impact

cell_area = cell_ft ** 2

def report(name, d):
    changed = np.abs(d) > 0.01  # ft, ignore floating-point noise
    n = np.nansum(changed)
    vol = np.nansum(np.where(changed, d, 0)) * cell_area
    maxd = np.nanmax(d) if n else 0.0
    mind = np.nanmin(d) if n else 0.0
    print(f"{name}: {int(n):,} cells changed ({100*n/valid.sum():.3f}% of tile), "
          f"volume = {vol:,.1f} cu ft, max raise = {maxd:.3f} ft, max cut = {mind:.3f} ft")

report("Breach-only", d_breach)
report("Residual fill (on top of breach)", d_residual)
report("Total (fill+breach combined)", d_total)

# save difference rasters for spatial mapping
out_profile = profile.copy()
out_profile.update(dtype="float32", nodata=-9999)
for name, arr in [("fill_impact_breach.tif", d_breach),
                   ("fill_impact_residual.tif", d_residual),
                   ("fill_impact_total.tif", d_total)]:
    out = np.where(np.isnan(arr), -9999, arr).astype(np.float32)
    with rasterio.open(HYDRO / name, "w", **out_profile) as dst:
        dst.write(out, 1)

print("\nSaved:", HYDRO / "fill_impact_breach.tif")
print("Saved:", HYDRO / "fill_impact_residual.tif")
print("Saved:", HYDRO / "fill_impact_total.tif")
print("Final corrected DEM:", filled)
