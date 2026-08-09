#!/usr/bin/env python3
"""
Batch-process every .laz tile in data/raw/ into a bare-earth DEM + hillshade.

Reuses build_pipeline() and run() from run_dem.py rather than duplicating
the PDAL pipeline logic. Per-tile SMRF parameters come from
scripts/tile_params.json -- ground classification parameters are terrain-
dependent judgment calls (see CLAUDE.md item #10), not something this
script tries to guess.

Usage:
    python batch_process.py
    python batch_process.py --force     # reprocess tiles even if a DEM
                                         # for them already exists

Units are FEET (EPSG:6405, Arizona Central ft). Tiles whose header CRS
isn't EPSG:6405 are skipped with a warning naming the CRS found -- not
auto-reprojected. Reprojecting silently inside an unattended batch loop is
exactly the kind of step this project already found a subtle bug in this
session (Z staying in meters after a "successful" horizontal reprojection);
it needs a human sanity check, not a hidden automatic step.

QC CSV column definitions are documented in
output/reports/batch_qc_README.md, written alongside the CSV.

Known limitation: SMRF ground classification degrades near a tile's edge
(no neighborhood context beyond the tile boundary). This script does not
buffer across adjacent tiles -- see "Known Limitations" in CLAUDE.md.
"""

import argparse
import csv
import json
import re
import sys
import time
import traceback
from pathlib import Path

import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_dem import build_pipeline, run, ROOT, DEM_DIR, HS_DIR, PIPE_DIR  # noqa: E402

RAW_DIR = ROOT / "data" / "raw"
PARAMS_FILE = ROOT / "scripts" / "tile_params.json"
REPORTS_DIR = ROOT / "output" / "reports"
CSV_PATH = REPORTS_DIR / "batch_qc.csv"
README_PATH = REPORTS_DIR / "batch_qc_README.md"
CATALOG_VRT = DEM_DIR / "catalog.vrt"

EXPECTED_EPSG = "6405"
INTL_FT_TO_M = 0.3048  # EPSG:6405 uses the international foot, not US survey foot

CSV_FIELDS = [
    "tile", "status", "window", "slope", "threshold", "scalar", "cell", "res",
    "last_return_only", "point_count", "ground_point_count", "ground_pct",
    "z_min_ft", "z_max_ft", "point_density_per_m2", "void_cell_count",
    "void_cell_pct", "runtime_sec", "dem_path", "error_message",
]

README_TEXT = """\
# Batch QC CSV -- column definitions

Written by scripts/batch_process.py. One row per tile in data/raw/.

- **tile** -- source LAZ filename.
- **status** -- one of:
  - `success` -- processed this run, all fields populated.
  - `skipped_existing` -- DEM already existed and --force wasn't passed.
    Numeric QC fields are blank: they reflect whatever run originally
    produced that DEM, not necessarily this run, so this script doesn't
    guess at them. Check `dem_path`'s timestamp if you need to know when.
  - `skipped_wrong_crs` -- header CRS isn't EPSG:6405; not processed.
    `error_message` names the CRS actually found.
  - `error` -- an exception was raised somewhere in this tile's pipeline.
    `error_message` has the first line of it; full traceback goes to
    stdout/console at run time, not into the CSV.
- **window / slope / threshold / scalar / cell / res / last_return_only**
  -- the exact SMRF parameters used for this tile (from
  scripts/tile_params.json). Also written to the tile's own pipeline JSON
  in scripts/pipelines/ per the project's existing audit-trail convention.
- **point_count** -- total points in the source LAZ (all classes, all
  returns), from the file header.
- **ground_point_count** -- points classified as ground (Classification=2)
  by this run's SMRF, via a non-destructive filters.stats stage inserted
  right after the ground filter (does not require re-reading the file).
- **ground_pct** -- ground_point_count / point_count * 100.
- **z_min_ft / z_max_ft** -- elevation range of the GROUND-CLASSIFIED
  points only (i.e. the range actually present in the output DEM), not
  the raw tile's full point-cloud Z range, which would include
  vegetation/noise and be less informative about the bare-earth surface.
- **point_density_per_m2** -- ground_point_count / tile area in m^2. This
  is a single tile-wide AVERAGE, not a per-cell raster -- for a full
  per-cell density + void map (a heavier, separate product), see item #6
  in CLAUDE.md and scripts/pipelines/pipe_density.json.
- **void_cell_count / void_cell_pct** -- nodata cells in the tile's own
  output DEM raster, i.e. cells IDW couldn't fill from any ground point
  within the writer's window_size. This is DIFFERENT from item #6's void
  definition (zero first-return points in a dedicated density raster) --
  it's a free-from-the-DEM-already-being-written proxy, not the same
  measurement. Don't conflate the two numbers.
- **runtime_sec** -- wall-clock time for this tile's full pipeline run
  (classification + rasterize + hillshade + QC stats), not counting the
  initial header read used for the CRS check.
- **dem_path** -- output DEM path. Named `dem_<tile_stem>_<tag>.tif` --
  tile identity is included specifically so two different tiles processed
  with matching parameters can't collide (see CLAUDE.md item #10 for why
  this differs from run_dem.py's original tile-name-free convention).
- **error_message** -- see status above.

## catalog.vrt

`output/dem/catalog.vrt` mosaics every tile with status `success` or
`skipped_existing` (i.e. every tile that currently has a valid DEM),
built from an explicit path list, not a directory glob -- output/dem/
also contains many one-off exploratory rasters from manual parameter
tuning that must NOT end up in the mosaic. Named "catalog", not "mosaic",
because the tiles in this project are not spatially adjacent (San Xavier
and Tucson Mountains are ~15 miles apart) -- this is a virtual catalog of
processed tiles, not a seamless surface.
"""


def load_tile_params():
    raw = json.loads(PARAMS_FILE.read_text())
    default = {k: v for k, v in raw["_default"].items() if not k.startswith("_")}
    overrides = {
        tile: {k: v for k, v in params.items() if not k.startswith("_")}
        for tile, params in raw.items()
        if not tile.startswith("_")
    }
    return default, overrides


def get_tile_srs_and_count(tile):
    """Read just the header -- no point decompression needed for this."""
    result = run(["pdal", "info", "--metadata", str(tile)])
    meta = json.loads(result.stdout)["metadata"]
    wkt = meta.get("comp_spatialreference", "")
    m = re.search(r'"([^"]+)"', wkt)  # first quoted string = the CRS's human name
    srs_name = m.group(1) if m else "(CRS not found in header)"
    is_6405 = f'"EPSG","{EXPECTED_EPSG}"' in wkt
    return is_6405, srs_name, meta["count"]


def process_tile(tile_path, params, force):
    row = {f: "" for f in CSV_FIELDS}
    row["tile"] = tile_path.name
    for k in ("window", "slope", "threshold", "scalar", "cell", "res", "last_return_only"):
        row[k] = params[k]

    tag = f"w{params['window']:g}_s{params['slope']:g}_t{params['threshold']:g}"
    if params["last_return_only"]:
        tag += "_lastreturn"
    out_stem = f"{tile_path.stem}_{tag}"
    dem_tif = DEM_DIR / f"dem_{out_stem}.tif"
    hs_tif = HS_DIR / f"hs_{out_stem}.tif"
    pipe_json = PIPE_DIR / f"pipe_{out_stem}.json"
    row["dem_path"] = str(dem_tif)

    if dem_tif.exists() and not force:
        row["status"] = "skipped_existing"
        print(f"  [skip] {tile_path.name}: {dem_tif.name} already exists "
              f"(use --force to reprocess)")
        return row

    t0 = time.time()
    try:
        is_6405, srs_name, point_count = get_tile_srs_and_count(tile_path)
        if not is_6405:
            row["status"] = "skipped_wrong_crs"
            row["error_message"] = f"expected EPSG:6405, found: {srs_name}"
            print(f"  [skip] {tile_path.name}: wrong CRS -- {srs_name}")
            return row

        row["point_count"] = point_count

        pipeline = build_pipeline(
            tile_path, dem_tif,
            params["window"], params["slope"], params["threshold"],
            params["scalar"], params["cell"], params["res"],
            last_return_only=params["last_return_only"],
            stats_dimensions="Z",
        )
        pipe_json.write_text(json.dumps(pipeline, indent=2))

        meta_path = pipe_json.with_suffix(".meta.json")
        run(["pdal", "pipeline", str(pipe_json), "--metadata", str(meta_path)])
        stage_meta = json.loads(meta_path.read_text())["stages"]
        z_stats = stage_meta["filters.stats"]["statistic"][0]
        ground_count = z_stats["count"]
        row["ground_point_count"] = ground_count
        row["ground_pct"] = round(100 * ground_count / point_count, 3) if point_count else ""
        row["z_min_ft"] = round(z_stats["minimum"], 3)
        row["z_max_ft"] = round(z_stats["maximum"], 3)

        run(["gdaldem", "hillshade", str(dem_tif), str(hs_tif), "-az", "315", "-alt", "45"])

        with rasterio.open(dem_tif) as ds:
            band = ds.read(1)
            nodata = ds.nodata
            total_cells = band.size
            void = int((band == nodata).sum())
            width_ft = ds.bounds.right - ds.bounds.left
            height_ft = ds.bounds.top - ds.bounds.bottom

        area_m2 = (width_ft * INTL_FT_TO_M) * (height_ft * INTL_FT_TO_M)
        row["void_cell_count"] = void
        row["void_cell_pct"] = round(100 * void / total_cells, 3)
        row["point_density_per_m2"] = round(ground_count / area_m2, 4) if area_m2 else ""

        row["status"] = "success"
        print(f"  [ok] {tile_path.name}: {ground_count:,}/{point_count:,} ground "
              f"({row['ground_pct']}%), void {row['void_cell_pct']}%, "
              f"{time.time() - t0:.1f}s")

    except Exception as e:
        row["status"] = "error"
        row["error_message"] = str(e).splitlines()[0][:300]
        print(f"  [ERROR] {tile_path.name}: {row['error_message']}")
        traceback.print_exc()

    row["runtime_sec"] = round(time.time() - t0, 2)
    return row


def build_catalog_vrt(dem_paths):
    print(f"\nBuilding catalog VRT from {len(dem_paths)} tile(s)...")
    try:
        run(["gdalbuildvrt", "-overwrite", str(CATALOG_VRT)] + [str(p) for p in dem_paths])
        print(f"  Catalog: {CATALOG_VRT}")
    except RuntimeError as e:
        print(f"  WARNING: catalog VRT build failed, leaving per-tile DEMs as-is:\n{e}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                     help="reprocess tiles even if their DEM already exists")
    args = ap.parse_args()

    for d in (DEM_DIR, HS_DIR, PIPE_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    default_params, overrides = load_tile_params()
    tiles = sorted(RAW_DIR.glob("*.laz"))
    if not tiles:
        print(f"No .laz files found in {RAW_DIR}")
        return

    print(f"Found {len(tiles)} tile(s) in {RAW_DIR}\n")

    rows = []
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        f.flush()

        for tile in tiles:
            params = dict(default_params)
            if tile.name in overrides:
                params.update(overrides[tile.name])
            else:
                print(f"  [warn] {tile.name}: no entry in tile_params.json -- using "
                      f"_default parameters (flat, sparse-vegetation terrain). These "
                      f"are NOT validated for this tile -- inspect the hillshade "
                      f"before trusting the result.")

            row = process_tile(tile, params, args.force)
            rows.append(row)
            writer.writerow(row)
            f.flush()  # every tile's result is on disk before moving to the next

    README_PATH.write_text(README_TEXT)

    mosaic_paths = [Path(r["dem_path"]) for r in rows
                     if r["status"] in ("success", "skipped_existing")
                     and Path(r["dem_path"]).exists()]
    if mosaic_paths:
        build_catalog_vrt(mosaic_paths)
    else:
        print("\nNo tiles with a valid DEM to mosaic.")

    n_ok = sum(1 for r in rows if r["status"] == "success")
    n_skip = sum(1 for r in rows if r["status"].startswith("skipped"))
    n_err = sum(1 for r in rows if r["status"] == "error")
    print(f"\n=== Batch complete: {n_ok} processed, {n_skip} skipped, {n_err} failed ===")
    print(f"QC log:  {CSV_PATH}")
    print(f"README:  {README_PATH}")
    print(f"Catalog: {CATALOG_VRT}")


if __name__ == "__main__":
    main()
