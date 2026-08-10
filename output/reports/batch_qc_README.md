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
  POINTS, from PDAL's stats filter on Z; not the raw tile's full
  point-cloud Z range (which would include vegetation/noise and be less
  informative about the bare-earth surface). Note this is *not* the same
  as the output DEM's own min/max: IDW interpolation smooths extremes,
  so the raster range is slightly narrower (San Xavier: points
  2490.75-2650.69, raster 2491.03-2650.34). An earlier version of this
  file glossed the column as "the range actually present in the output
  DEM," which the rasters contradict; corrected 2026-08-10.
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
