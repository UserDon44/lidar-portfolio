#!/usr/bin/env python3
"""
Build a bare-earth DEM from a LAZ tile with configurable SMRF parameters.

Usage:
    python run_dem.py --window 120 --threshold 1.6
    python run_dem.py --window 120 --threshold 1.6 --slope 0.15 --res 3.0

Outputs are named by parameter so runs never overwrite each other.
Units are FEET (data is EPSG:6405, Arizona Central ft).
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# --- project paths -------------------------------------------------
ROOT = Path(r"C:\Users\ryans\lidar-portfolio")
TILE = ROOT / "data" / "raw" / "USGS_LPC_Eastern_Pima_County_Lidar_980398.laz"
DEM_DIR = ROOT / "output" / "dem"
HS_DIR = ROOT / "output" / "hillshade"
PIPE_DIR = ROOT / "scripts" / "pipelines"


def build_pipeline(tile, out_tif, window, slope, threshold, scalar, cell, res):
    """Return the PDAL pipeline as a dict."""
    return {
        "pipeline": [
            {"type": "readers.las", "filename": str(tile).replace("\\", "/")},
            # wipe vendor classification - we classify from scratch
            {"type": "filters.assign", "assignment": "Classification[:]=0"},
            # low-outlier removal (craters)
            {"type": "filters.elm", "cell": 33.0, "threshold": 3.3},
            # statistical outlier removal -> marks class 7
            {"type": "filters.outlier", "method": "statistical",
             "mean_k": 8, "multiplier": 3.0},
            # ground classification
            {"type": "filters.smrf", "cell": cell, "window": window,
             "slope": slope, "threshold": threshold, "scalar": scalar,
             "ignore": "Classification[7:7]"},
            # keep ground only
            {"type": "filters.range", "limits": "Classification[2:2]"},
            # rasterize
            {"type": "writers.gdal", "filename": str(out_tif).replace("\\", "/"),
             "resolution": res, "output_type": "idw",
             "window_size": 6, "nodata": -9999},
        ]
    }


def run(cmd):
    """Run a command, surface errors clearly."""
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("  FAILED:")
        print(result.stderr)
        sys.exit(1)
    return result


def main():
    p = argparse.ArgumentParser(description="Build bare-earth DEM via PDAL SMRF")
    p.add_argument("--window", type=float, default=120.0,
                   help="max non-ground object size, FEET (default 120)")
    p.add_argument("--slope", type=float, default=0.15,
                   help="terrain slope tolerance, dimensionless (default 0.15)")
    p.add_argument("--threshold", type=float, default=1.6,
                   help="elevation threshold, FEET (default 1.6)")
    p.add_argument("--scalar", type=float, default=1.25,
                   help="threshold scaling with slope (default 1.25)")
    p.add_argument("--cell", type=float, default=3.3,
                   help="SMRF cell size, FEET (default 3.3)")
    p.add_argument("--res", type=float, default=3.0,
                   help="output DEM resolution, FEET (default 3.0)")
    args = p.parse_args()

    for d in (DEM_DIR, HS_DIR, PIPE_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # parameter-encoded filenames so runs are self-documenting
    tag = f"w{args.window:g}_s{args.slope:g}_t{args.threshold:g}"
    dem_tif = DEM_DIR / f"dem_{tag}.tif"
    hs_tif = HS_DIR / f"hs_{tag}.tif"
    pipe_json = PIPE_DIR / f"pipe_{tag}.json"

    print(f"\n=== {tag} ===")
    print(f"  window={args.window} ft  slope={args.slope}  "
          f"threshold={args.threshold} ft  res={args.res} ft")

    # write pipeline (keeps a record of exactly what was run)
    pipeline = build_pipeline(TILE, dem_tif, args.window, args.slope,
                              args.threshold, args.scalar, args.cell, args.res)
    pipe_json.write_text(json.dumps(pipeline, indent=2))

    print("\n[1/2] Classifying ground and rasterizing...")
    run(["pdal", "pipeline", str(pipe_json)])

    print("[2/2] Generating hillshade...")
    run(["gdaldem", "hillshade", str(dem_tif), str(hs_tif),
         "-az", "315", "-alt", "45"])

    print(f"\nDone.")
    print(f"  DEM:       {dem_tif}")
    print(f"  Hillshade: {hs_tif}")


if __name__ == "__main__":
    main()