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


def build_pipeline(tile, out_tif, window, slope, threshold, scalar, cell, res,
                    last_return_only=False, stats_dimensions=None,
                    neighbour_tiles=None, read_bounds=None, crop_bounds=None,
                    raster_grid=None):
    """Return the PDAL pipeline as a dict.

    last_return_only: if True, insert a filters.returns stage (groups=
        last,only) before ELM/outlier/SMRF, discarding first/intermediate
        returns (near-certain vegetation-canopy hits). Needed on tiles with
        real canopy penetration -- see the Tucson Mountains tile in
        CLAUDE.md item #10. Leaves the default (flat, sparse-vegetation
        tile) pipeline unchanged.

    stats_dimensions: if given (e.g. "Z"), insert a filters.stats stage
        after the ground-only filter, non-destructively reporting
        count/min/max/mean for those dimensions in the pipeline's
        --metadata output. Used by the batch processor to get
        ground-point count and ground-only Z range without a second
        read of the file.

    --- tile-edge buffering (item #12) ---

    neighbour_tiles / read_bounds / crop_bounds together implement buffered
    classification, which removes the edge artifact SMRF otherwise leaves at
    a tile boundary (points there have no neighbourhood context because
    whatever is just outside the tile isn't in the pipeline at all).

    neighbour_tiles: additional LAZ paths read alongside `tile` and merged
        with it, so the classifier sees across the boundary.
    read_bounds: ([minx,maxx],[miny,maxy]) -- the tile's own extent grown by
        the buffer distance. Applied right after the merge so the neighbours
        contribute only a margin, not their entire contents.
    crop_bounds: ([minx,maxx],[miny,maxy]) -- the tile's TRUE extent.
        Applied after classification and before rasterizing, so the buffer
        informs the ground/non-ground decision but never appears in the
        output. Without this the DEMs would overlap and the mosaic would
        double-cover every seam.

    All three must be given together; passing none reproduces the original
    unbuffered pipeline byte-for-byte.
    """
    if neighbour_tiles:
        return _buffered_pipeline(tile, out_tif, window, slope, threshold, scalar,
                                  cell, res, last_return_only, stats_dimensions,
                                  neighbour_tiles, read_bounds, crop_bounds,
                                  raster_grid)

    readers = [{"type": "readers.las", "filename": str(tile).replace("\\", "/")}]
    stages = list(readers)
    # wipe vendor classification - we classify from scratch
    stages.append({"type": "filters.assign", "assignment": "Classification[:]=0"})
    if last_return_only:
        # drop first/intermediate returns of multi-return pulses -- these
        # are near-certain vegetation canopy hits, not ground candidates
        stages.append({"type": "filters.returns", "groups": "last,only"})
    # low-outlier removal (craters)
    stages.append({"type": "filters.elm", "cell": 33.0, "threshold": 3.3})
    # statistical outlier removal -> marks class 7
    stages.append({"type": "filters.outlier", "method": "statistical",
                    "mean_k": 8, "multiplier": 3.0})
    # ground classification
    stages.append({"type": "filters.smrf", "cell": cell, "window": window,
                    "slope": slope, "threshold": threshold, "scalar": scalar,
                    "ignore": "Classification[7:7]"})
    # keep ground only
    stages.append({"type": "filters.range", "limits": "Classification[2:2]"})
    if stats_dimensions:
        stages.append({"type": "filters.stats", "dimensions": stats_dimensions})
    # rasterize
    stages.append({"type": "writers.gdal", "filename": str(out_tif).replace("\\", "/"),
                    "resolution": res, "output_type": "idw",
                    "window_size": 6, "nodata": -9999})
    return {"pipeline": stages}


def _buffered_pipeline(tile, out_tif, window, slope, threshold, scalar, cell, res,
                        last_return_only, stats_dimensions,
                        neighbour_tiles, read_bounds, crop_bounds, raster_grid):
    """Buffered pipeline, branched so the raster and the QC stats see
    different point sets.

    The key ordering point, and the reason this exists: the raster is
    written from the FULL buffered point set, over a grid deliberately
    extended by the buffer, and is clipped back to the tile afterwards as
    a raster operation. An earlier version cropped the POINTS to the tile
    before writers.gdal, which fixed the classification edge effect but
    left an interpolation one -- IDW's fallback search (window_size cells)
    still saw a one-sided neighbourhood at the boundary, which is exactly
    where seam discontinuity is measured. Cropping the raster instead
    means every output cell, including edge cells, is interpolated from a
    complete neighbourhood.

    QC stats stay tile-only via `filters.stats`'s `where` + `where_merge`,
    which computes statistics over just the matching points while passing
    every point through to the writer unchanged. Without that restriction
    ground_point_count would silently include the margin while
    ground_pct's denominator (the tile's own header count) would not, and
    the column would stop being comparable with unbuffered runs.

    A branched pipeline was tried first and abandoned: PDAL 2.10 reports no
    per-stage metadata for a second branch once a `writers.gdal` is
    present -- the branch collapses into an unnamed, empty metadata entry,
    so `filters.stats` becomes unreadable. Verified directly rather than
    inferred. Keeping the chain linear avoids the problem entirely.
    """
    stages = [{"type": "readers.las", "filename": str(t).replace("\\", "/")}
              for t in [tile] + list(neighbour_tiles)]
    stages.append({"type": "filters.merge"})
    # trim neighbours to just the margin before any real work
    stages.append({"type": "filters.crop", "bounds": read_bounds})
    stages.append({"type": "filters.assign", "assignment": "Classification[:]=0"})
    if last_return_only:
        stages.append({"type": "filters.returns", "groups": "last,only"})
    stages.append({"type": "filters.elm", "cell": 33.0, "threshold": 3.3})
    stages.append({"type": "filters.outlier", "method": "statistical",
                   "mean_k": 8, "multiplier": 3.0})
    stages.append({"type": "filters.smrf", "cell": cell, "window": window,
                   "slope": slope, "threshold": threshold, "scalar": scalar,
                   "ignore": "Classification[7:7]"})
    stages.append({"type": "filters.range", "limits": "Classification[2:2]"})
    if stats_dimensions:
        stages.append({"type": "filters.stats", "dimensions": stats_dimensions,
                       "where": crop_bounds, "where_merge": "auto"})
    stages.append({"type": "writers.gdal",
                   "filename": str(out_tif).replace("\\", "/"),
                   "resolution": res, "output_type": "idw",
                   "window_size": 6, "nodata": -9999,
                   "origin_x": raster_grid["origin_x"],
                   "origin_y": raster_grid["origin_y"],
                   "width": raster_grid["width"],
                   "height": raster_grid["height"]})
    return {"pipeline": stages}


def run(cmd):
    """Run a command, surface errors clearly.

    Raises RuntimeError on failure instead of exiting the process, so
    callers (e.g. a batch loop processing many tiles) can catch it and
    continue. main() below catches it and exits(1), preserving this
    script's original single-tile CLI behavior.
    """
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(str(c) for c in cmd)}\n"
            f"{result.stderr}"
        )
    return result


def main():
    p = argparse.ArgumentParser(description="Build bare-earth DEM via PDAL SMRF")
    p.add_argument("--tile", type=Path, default=TILE,
                   help=f"input LAZ tile (default {TILE.name})")
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
    p.add_argument("--last-return-only", action="store_true",
                   help="drop first/intermediate returns before classifying "
                        "(use on tiles with real canopy penetration)")
    args = p.parse_args()

    for d in (DEM_DIR, HS_DIR, PIPE_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # parameter-encoded filenames so runs are self-documenting
    tag = f"w{args.window:g}_s{args.slope:g}_t{args.threshold:g}"
    dem_tif = DEM_DIR / f"dem_{tag}.tif"
    hs_tif = HS_DIR / f"hs_{tag}.tif"
    pipe_json = PIPE_DIR / f"pipe_{tag}.json"

    print(f"\n=== {tag} ===")
    print(f"  tile={args.tile.name}")
    print(f"  window={args.window} ft  slope={args.slope}  "
          f"threshold={args.threshold} ft  res={args.res} ft")

    # write pipeline (keeps a record of exactly what was run)
    pipeline = build_pipeline(args.tile, dem_tif, args.window, args.slope,
                              args.threshold, args.scalar, args.cell, args.res,
                              last_return_only=args.last_return_only)
    pipe_json.write_text(json.dumps(pipeline, indent=2))

    try:
        print("\n[1/2] Classifying ground and rasterizing...")
        run(["pdal", "pipeline", str(pipe_json)])

        print("[2/2] Generating hillshade...")
        run(["gdaldem", "hillshade", str(dem_tif), str(hs_tif),
             "-az", "315", "-alt", "45"])
    except RuntimeError as e:
        print(f"  FAILED:\n{e}")
        sys.exit(1)

    print(f"\nDone.")
    print(f"  DEM:       {dem_tif}")
    print(f"  Hillshade: {hs_tif}")


if __name__ == "__main__":
    main()