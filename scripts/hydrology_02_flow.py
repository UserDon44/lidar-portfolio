#!/usr/bin/env python3
"""
Stage 2: D8 flow direction and accumulation off the breached+filled DEM.
Also computes percent-slope (for the slope-area threshold analysis in
stage 3) off the SAME corrected DEM.
"""
import whitebox
from pathlib import Path

ROOT = Path(r"C:\Users\ryans\lidar-portfolio")
HYDRO = ROOT / "output" / "hydrology"
filled = HYDRO / "dem_02_filled.tif"

wbt = whitebox.WhiteboxTools()
wbt.set_working_dir(str(HYDRO))
wbt.verbose = True

pntr = HYDRO / "d8_pointer.tif"
accum = HYDRO / "d8_flow_accum_cells.tif"
slope = HYDRO / "slope_pct.tif"

print("=== D8Pointer ===")
wbt.d8_pointer(dem=str(filled), output=str(pntr))

print("\n=== D8FlowAccumulation (cells) ===")
wbt.d8_flow_accumulation(i=str(pntr), output=str(accum), out_type="cells", pntr=True)

print("\n=== Slope (percent) ===")
wbt.slope(dem=str(filled), output=str(slope), units="percent")

print("\nDone.")
print("Pointer:", pntr)
print("Accumulation:", accum)
print("Slope:", slope)
