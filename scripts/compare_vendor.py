#!/usr/bin/env python3
"""
compare_vendor.py -- Is it my classification, or is it the terrain?

Renders THREE things from the same tile so you can settle the question
empirically instead of guessing at SMRF parameters:

  1. vendor  -- USGS's own delivered ground classification (class 2), untouched
  2. mine    -- your SMRF result at the given parameters
  3. diff    -- vendor DEM minus your DEM, so disagreement is visible as
                bright/dark patches instead of something you have to eyeball

If the rectangles show up in the VENDOR hillshade too, they are real ground
features (pads, foundations, graded lots) and you have been chasing artifacts
that were never errors. If they only show up in YOURS, it is a tuning problem
and the diff raster tells you exactly where and by how much.

Usage:
    python compare_vendor.py
    python compare_vendor.py --window 120 --threshold 0.5 --slope 0.05

Units are FEET throughout (EPSG:6405, NAD83(2011) Arizona Central ft).
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\ryans\lidar-portfolio")
TILE = ROOT / "data" / "raw" / "USGS_LPC_Eastern_Pima_County_Lidar_980398.laz"
DEM_DIR = ROOT / "output" / "dem"
HS_DIR = ROOT / "output" / "hillshade"
PIPE_DIR = ROOT / "scripts" / "pipelines"
RES = 3.0  # output cell size, feet

# Fixed tile extent (from the source LAZ header) that every run gets warped
# onto before differencing. writers.gdal computes each run's raster extent
# from that run's own point cloud bounding box, so two runs with slightly
# different point populations (e.g. vendor class-2-only vs. your SMRF output)
# round to different pixel grids (1668x1668 vs 1667x1667) and gdal_calc
# refuses to difference them. Forcing both through gdalwarp onto this
# explicit grid fixes it.
TILE_EXTENT = (980112.76, 398427.81, 985112.75, 403427.80)  # minx miny maxx maxy


def align(src_tif, out_tif):
    """Warp a DEM onto the fixed tile grid so it can be differenced against
    any other aligned DEM, regardless of what extent PDAL originally wrote."""
    minx, miny, maxx, maxy = TILE_EXTENT
    sh(["gdalwarp", "-te", str(minx), str(miny), str(maxx), str(maxy),
        "-tr", str(RES), str(RES), "-r", "bilinear", "-overwrite",
        str(src_tif), str(out_tif)])
    return out_tif


def sh(cmd):
    print("  $ " + " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("  FAILED:\n" + r.stderr)
        sys.exit(1)
    return r


def write_pipe(name, stages):
    p = PIPE_DIR / f"{name}.json"
    p.write_text(json.dumps({"pipeline": stages}, indent=2))
    return p


def fwd(p):
    """PDAL wants forward slashes even on Windows."""
    return str(p).replace("\\", "/")


def vendor_dem(out_tif):
    """USGS's delivered classification, no reprocessing at all."""
    return [
        {"type": "readers.las", "filename": fwd(TILE)},
        # keep only what the vendor already called ground
        {"type": "filters.range", "limits": "Classification[2:2]"},
        {"type": "writers.gdal", "filename": fwd(out_tif),
         "resolution": RES, "output_type": "idw",
         "window_size": 6, "nodata": -9999},
    ]


def my_dem(out_tif, window, slope, threshold, scalar, cell):
    """Classify from scratch with SMRF."""
    return [
        {"type": "readers.las", "filename": fwd(TILE)},
        {"type": "filters.assign", "assignment": "Classification[:]=0"},
        {"type": "filters.elm", "cell": 33.0, "threshold": 3.3},
        {"type": "filters.outlier", "method": "statistical",
         "mean_k": 8, "multiplier": 3.0},
        {"type": "filters.smrf", "cell": cell, "window": window,
         "slope": slope, "threshold": threshold, "scalar": scalar,
         "ignore": "Classification[7:7]"},
        {"type": "filters.range", "limits": "Classification[2:2]"},
        {"type": "writers.gdal", "filename": fwd(out_tif),
         "resolution": RES, "output_type": "idw",
         "window_size": 6, "nodata": -9999},
    ]


def hillshade(dem, hs):
    sh(["gdaldem", "hillshade", str(dem), str(hs), "-az", "315", "-alt", "45"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=float, default=120.0)
    ap.add_argument("--slope", type=float, default=0.15)
    ap.add_argument("--threshold", type=float, default=1.6)
    ap.add_argument("--scalar", type=float, default=1.25)
    ap.add_argument("--cell", type=float, default=3.3)
    a = ap.parse_args()

    for d in (DEM_DIR, HS_DIR, PIPE_DIR):
        d.mkdir(parents=True, exist_ok=True)

    tag = f"w{a.window:g}_s{a.slope:g}_t{a.threshold:g}"

    vend_tif = DEM_DIR / "dem_VENDOR.tif"
    vend_hs = HS_DIR / "hs_VENDOR.tif"
    mine_tif = DEM_DIR / f"dem_{tag}.tif"
    mine_hs = HS_DIR / f"hs_{tag}.tif"
    diff_tif = DEM_DIR / f"diff_VENDOR_minus_{tag}.tif"

    # --- 1. vendor baseline (only build it once) --------------------
    if vend_tif.exists():
        print(f"\n[1/4] Vendor DEM already exists, skipping build.")
    else:
        print(f"\n[1/4] Building VENDOR DEM (USGS delivered classification)...")
        sh(["pdal", "pipeline", str(write_pipe("pipe_VENDOR",
                                               vendor_dem(vend_tif)))])
        hillshade(vend_tif, vend_hs)

    # --- 2. your classification -------------------------------------
    print(f"\n[2/4] Building YOUR DEM  ({tag})...")
    print(f"      window={a.window} ft  slope={a.slope}  "
          f"threshold={a.threshold} ft")
    sh(["pdal", "pipeline",
        str(write_pipe(f"pipe_{tag}",
                       my_dem(mine_tif, a.window, a.slope,
                              a.threshold, a.scalar, a.cell)))])

    print(f"\n[3/4] Hillshading yours...")
    hillshade(mine_tif, mine_hs)

    # --- 3. difference raster ---------------------------------------
    # Positive = vendor is HIGHER than yours = you removed something they kept.
    # Negative = you are higher = you kept something they removed (buildings).
    # Align both onto the fixed tile grid first -- writers.gdal gives each
    # run its own extent, and gdal_calc refuses to difference mismatched grids.
    print(f"\n[4/4] Aligning both DEMs to a common grid, then differencing...")
    vend_aligned = align(vend_tif, DEM_DIR / "dem_VENDOR_aligned.tif")
    mine_aligned = align(mine_tif, DEM_DIR / f"dem_{tag}_aligned.tif")
    sh(["gdal_calc", "-A", str(vend_aligned), "-B", str(mine_aligned),
        "--outfile", str(diff_tif),
        "--calc", "A-B", "--NoDataValue", "-9999", "--overwrite"])

    print(f"""
Done. Open these three together in QGIS:

  VENDOR    {vend_hs}
  YOURS     {mine_hs}
  DIFF      {diff_tif}

How to read it
--------------
Flip between the two hillshades first. Look at the residential block on the
left side and the cluster along the bottom edge.

  Rectangles in BOTH  -> they are real ground features. Concrete pads, graded
                         building sites, foundations, walls. Not your bug.
                         Stop tuning; document it and move on.

  Rectangles in YOURS only -> tuning problem. Now open the diff raster and
                         style it in QGIS: Properties > Symbology > Singleband
                         pseudocolor, and set the range to about -20 to +20 ft.
                         Strong NEGATIVE blobs are roofs you kept. Their depth
                         in feet is the building height, which tells you how
                         far off threshold really is.

  Diff near zero everywhere else -> your parameters agree with a professional
                         contractor's across open terrain. That number is worth
                         putting in the QC memo.

If gdal_calc errors, try 'gdal_calc.py' instead on line ~150.
""")


if __name__ == "__main__":
    main()
