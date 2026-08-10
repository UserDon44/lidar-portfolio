# LiDAR Processing Portfolio — Eastern Pima County, AZ

## What this project is
A portfolio piece for applying to survey/geospatial firms in the Southwest
(Cooper Aerial, NV5, Woolpert and similar). The goal is a defensible
bare-earth DEM deliverable produced from raw returns, with a QC memo and
quantified accuracy — not a tutorial exercise.

I am new to the terminal and to Python. Explain what you are doing as you
go. Write files directly rather than asking me to paste into an editor.

## CRITICAL: units are FEET
CRS is **EPSG:6405** — NAD83(2011) / Arizona Central (ft). Horizontal units
are **International Feet** (EPSG:9002, 1 ft = 0.3048 m exactly) — **NOT**
US survey feet (EPSG:9003, 1 ft = 0.3048006096 m) and NOT meters. The
International/US-survey distinction is only ~2 ppm (~0.06 ft over this
5,000 ft tile) — numerically negligible, but stating the wrong one in a
deliverable aimed at surveyors is exactly the kind of small error that
audience notices. Confirmed explicitly in the original tile's own project
documentation (see item on vertical datum/NVA below) — both the Psomas
accuracy report and the Sanborn report of survey state "International
Feet" verbatim. Every distance parameter must still be converted from
metric defaults:

| metric default | feet equivalent |
|---|---|
| SMRF window 18 m | ~60 ft |
| SMRF threshold 0.5 m | ~1.6 ft |
| SMRF cell 1.0 m | ~3.3 ft |
| ELM cell 10 m | ~33 ft |

Getting this wrong silently produces garbage that still looks plausible.

**Vertical datum is NOT declared in the file header** (`"vertical": ""`),
but is now **CONFIRMED** against authoritative project documentation (see
"RESOLVED: vertical datum, sensor, and NVA" below): **NAVD88, Geoid12A**.

## The tile
`data/raw/USGS_LPC_Eastern_Pima_County_Lidar_980398.laz`
- 8,692,808 points, 33 MB compressed, LAS 1.4 point format 6
- Bounds: X 980112.76–985112.75, Y 398427.81–403427.80 (5000 x 5000 ft)
- Elevation range 2490.75–2654.69 ft (164 ft relief)
- Point density ~3.7 pts/m² → QL2
- Collected **Feb 20–26, 2015** (confirmed, see "RESOLVED: vertical datum,
  sensor, and NVA" below — 14 flight missions in ~1 week). The LAS header's
  file-creation date is day 307 (Nov 3, 2015) — that's when USGS/Sanborn
  finalized and repackaged the tile, months after acquisition, not a
  second flight. Sensor: Leica ALS70 HP (Sanborn Aero-Commander 500-B).
  Processed with LAStools.
- Location: San Xavier district, Tohono O'odham Nation, south of Tucson.
  Mixed use — irrigated agriculture east, residential and two small hills
  west, a wash running roughly N–S through the middle, one center-pivot
  irrigation circle (center ~983420, 400420 ft; radius ~540 ft).

**Vendor classification is present but ground-only**: classes 1–7, no
vegetation (3/4/5) or building (6) breakout. Class 2 ground is ~70% of
points. NumberOfReturns averages 1.023 — very sparse vegetation, almost
no canopy.

## Environment
conda env `lidar` (miniforge), installed at
`C:\Users\ryans\miniforge3\envs\lidar\`. Must run `conda activate lidar` in
each new Miniforge Prompt session.

PDAL 2.10.0 · GDAL 3.12.3 · laspy 2.7.0 + lazrs · numpy · rasterio ·
geopandas · matplotlib · scipy 1.17.1 · whitebox 2.3.6 (WhiteboxTools
2.4.0 binary, auto-downloaded on first use — added for the hydrologic
analysis, item #11; see below).

**Correction**: earlier notes in this file said "QGIS installed
separately." Checked directly when setting up the hydrology analysis —
**neither QGIS nor GRASS is actually installed** in this environment (no
`qgis_process`, no `grass` CLI, no install directory found). That's why
item #11 uses WhiteboxTools instead. If QGIS is genuinely needed later,
it will need to be installed fresh, not assumed present.

**Gotcha discovered this session**: running the env's `python.exe` or GDAL
CLI tools *without* an activated shell (e.g. from a script or a tool that
can't run `conda activate`) fails in confusing ways:
- GDAL command-line tools live in `Library\bin` under the env, not the env
  root — e.g. `C:\Users\ryans\miniforge3\envs\lidar\Library\bin\gdalinfo.exe`.
- Importing `matplotlib`/`rasterio` with an unpatched `PATH` crashes with
  **exit code 127 and no Python traceback** (DLL resolution failure, not a
  normal exception) — very confusing to debug.
- Fix: add both the env root and `Library\bin` and `Scripts` to `PATH`, and
  set `GDAL_DATA` to `...\envs\lidar\Library\share\gdal` and `PROJ_LIB` to
  `...\envs\lidar\Library\share\proj` before invoking anything.
- Without `GDAL_DATA` set, `gdalinfo` prints a harmless-but-noisy warning:
  `Cannot find gdalvrt.xsd (GDAL_DATA is not defined)`.

## Layout

```
lidar-portfolio/
  data/raw/            3 source tiles — NEVER modify. Gitignored.
  data/control/        NGS control points — empty; investigated via API
                        instead (item #5), concluded no usable in-tile
                        control exists. Left empty deliberately, not todo.
  scripts/             run_dem.py, compare_vendor.py, batch_process.py,
                        tile_params.json, hydrology_0[1-8]_*.py,
                        render_figures.py
  scripts/pipelines/   auto-generated PDAL JSON, one per run (audit trail)
  output/dem/          DEMs, named by parameter. Gitignored (regenerated).
  output/hillshade/    hillshades, named by parameter. Gitignored.
  output/contours/     2 ft contours (item #7). Gitignored.
  output/hydrology/    fill/flow/streams/watershed (item #11). Gitignored.
  output/figures/      presentation-quality PNGs for the report (scale
                        bar, north arrow, unit-labeled legends) — see
                        "How I want to work" below. Gitignored, same as
                        other output/ subfolders (regenerable from
                        render_figures.py + the source rasters).
  output/reports/      QC memo, batch QC CSV — TRACKED (see Housekeeping;
                        this is the one output/ subfolder not gitignored).
  qgis/                project files (not actively used — see QGIS
                        correction above)
  docs/                session-log.md (chronological), PROJECT_SUMMARY.md
                        (standalone narrative, no context assumed)
```

Convention: output filenames encode their parameters
(`dem_w120_s0.15_t1.6.tif`); batch-processed files additionally encode
tile identity (`dem_<tile_stem>_<tag>.tif`, see item on batch_process.py)
to avoid collisions across tiles with matching parameters. Never use
"final" or "v2" in a filename.
`data/raw/`, `output/*` (except `output/reports/`), and `.claude/` are
gitignored — most outputs are regenerated from the pipeline scripts, not
versioned directly; `output/reports/` is the deliberate exception because
it holds hand-authored prose, not regenerable rasters (see Housekeeping).

## What has been done

**`scripts/run_dem.py`** — parameterized DEM builder. Strips vendor
classification, runs ELM + statistical outlier removal, SMRF ground
classification, rasterizes ground-only at 3 ft IDW, generates hillshade.
Writes its pipeline JSON to `scripts/pipelines/` for every run.

**`scripts/compare_vendor.py`** — builds a DEM from the vendor's delivered
class-2 points, builds mine, and differences them. Includes the
grid-alignment fix (`TILE_EXTENT` + `align()`, both DEMs warped to a fixed
grid via `gdalwarp` before differencing). Committed.

Runs completed, original tile:
- `w60_t1.6` — first attempt
- `w120_s0.15_t1.6` — doubled window, near-identical result. **This is the
  DEM used for all QC analysis below.**
- `w180_s0.15_t1.6`, `w240_s0.15_t1.6` — window doubled/quadrupled again to
  test whether window size was suppressing the residential rectangles. It
  wasn't (see Roof/pad finding).
- `VENDOR` — USGS delivered classification baseline
- `dsm` / `chm` — surface model and canopy/structure height model
- `density_count_3ft` — per-cell point density + void map

Runs completed, Tucson Mountains tile (item #10, see below): five SMRF
parameter iterations, final is `dem_tucson_lastreturn_w33_s0.6_t1.3`.

**`scripts/batch_process.py`** — batch-processes every `.laz` tile in
`data/raw/` into a DEM + hillshade, reusing `build_pipeline()`/`run()`
from `run_dem.py` (extended, not duplicated — `build_pipeline()` gained
an optional `last_return_only` flag and a `stats_dimensions` hook;
`run()` now raises instead of calling `sys.exit`, so a batch loop can
catch per-tile failures and continue). Per-tile SMRF parameters come from
`scripts/tile_params.json`, keyed by filename, with a loud warning for
any tile not listed (falls back to the flat-desert `_default`, which we
know from item #10 can silently produce a bad DEM on different terrain).
Skips tiles whose header CRS isn't EPSG:6405 (logs the actual CRS found,
does not auto-reproject — reprojection needs a human sanity check, see
item #10's Z-stayed-in-meters bug). Idempotent by default (skips a tile
if `dem_<tile_stem>_<tag>.tif` already exists; `--force` overrides).
Writes per-tile QC to `output/reports/batch_qc.csv`, with column
definitions in `output/reports/batch_qc_README.md`. Mosaics all
successfully-processed DEMs into `output/dem/catalog.vrt` (named
"catalog," not "mosaic" — the tiles aren't spatially adjacent).

**`scripts/hydrology_01..08_*.py`** — hydrologic analysis pipeline (item
#11, full detail in its own section below): depression fill/breach, D8
flow direction/accumulation, slope-area threshold analysis, stream
extraction/vectorization, watershed delineation, and the final figures.
Built on WhiteboxTools rather than reusing `run_dem.py`'s PDAL-based
logic — a different toolkit for a different problem (surface hydrology,
not point-cloud classification).

**`scripts/render_figures.py`** — presentation-quality figure renderer for
the report, writing to `output/figures/`. Shared `add_scalebar()` /
`add_north_arrow()` helpers so every figure looks consistent; every plot
states units explicitly (International Feet for linear quantities;
pts/m² for density, since forcing an areal density into feet wouldn't
make sense — cell size in ft is stated in the caption instead). Currently
renders 7 figures: vendor-diff, swath-offset, density/QL2, CHM, and three
hillshades (vendor / w120 / w60). Add new figures here, not as one-off
scratchpad scripts — see "How I want to work" below for why.

## RESOLVED: roof vs. pad question

**Answer: concrete foundation pads leading to driveways and the road — not
unremoved roof points. Confirmed by user.**

Method: picked one isolated rectangular feature in the western residential
block (from the `w120_s0.15_t1.6` DEM/hillshade), sampled DEM elevation at
its center vs. a point in clearly open ground nearby (excluding contamination
from both the adjacent hillslope and the loop road, which biased earlier
automated attempts — see below).

| Point | Location (ft, EPSG:6405) | Elevation (ft) |
|---|---|---|
| CENTER (structure interior) | 980339.26, 400067.31 | 2548.050 |
| YARD (open ground, ~45 ft south) | 980357.26, 400019.31 | 2545.204 |
| **Difference** | | **+2.85 ft** |

A roof would show an 8–15 ft plateau with a sharp vertical wall edge; 2.85 ft
is consistent with a graded/built-up pad, not roof height. Site context
supports it: this block sits near the N–S wash, and a pad built up 2–3 ft
above natural grade is normal flood-mitigation practice for structures near
a wash.

**Why SMRF didn't remove it, and why widening `window` didn't help**: the
structure footprint (~70–100 ft across) is comparable to the SMRF `window`
tried (120–240 ft). When a raised, flat feature approaches window size,
SMRF's morphological-opening surface model gets pulled upward *within* that
window and starts treating the pad top as part of the terrain — a known
SMRF limitation, not a pipeline bug. This is worth citing by name in the QC
memo's vendor-comparison section.

**Method note for future structure checks**: automated blob detection
(threshold above a "background" elevation + connected-components) kept
failing — it merged the structure with the adjacent hillslope on one side
and the loop road on the other, since natural terrain relief was the same
order of magnitude as the structure's step. Had to fall back to reading the
raw elevation grid by hand (ASCII-art dump of relative elevation) and
picking reference points explicitly clear of both contaminating features.
If checking more structures, expect this same failure mode and go straight
to manual grid inspection rather than re-attempting automated segmentation.

Images (currently in the session scratchpad only — not yet saved into the
repo; see Open items):
- Sample-location diagram (green box = structure interior, blue box = open
  ground reference, overlaid on hillshade)

## RESOLVED: grid alignment bug

**Root cause**: `writers.gdal` (PDAL) computes each run's raster extent from
that run's own point cloud bounding box. The vendor run (class-2 points
only) and the `w120_s0.15_t1.6` run have slightly different point
populations, so their extents round to different pixel grids:
- `dem_VENDOR.tif`: 1668×1668, origin (980110.30, 403430.07)
- `dem_w120_s0.15_t1.6.tif`: 1667×1667, origin (980112.76, 403428.81)

`gdal_calc` refuses to difference mismatched grids.

**Fix**: force both through `gdalwarp` onto a fixed grid tied to the tile's
actual bounds (from the LAZ header), not to what any individual run thought
its extent was:

```
gdalwarp -te 980112.76 398427.81 985112.75 403427.80 -tr 3 3 -r bilinear -overwrite <in> <out>
```

Produced this session: `output/dem/dem_VENDOR_aligned.tif` and
`output/dem/dem_w120_s0.15_t1.6_aligned.tif`, both 1667×1667 on the
identical grid.

**`scripts/compare_vendor.py` was patched** to do this automatically for
all future runs: added a `TILE_EXTENT` constant and an `align()` helper,
called on both DEMs before `gdal_calc` in the differencing step. This
change is in the working tree but **not yet committed**.

## RESOLVED: vendor vs. mine difference (item #2 of the original plan)

`output/dem/diff_VENDOR_minus_w120_s0.15_t1.6.tif` = vendor DEM − mine.

| Stat | Value |
|---|---|
| Valid cells | 2,777,225 / 2,778,889 (99.9%) |
| Mean | −0.047 ft |
| Std dev | 0.155 ft |
| **RMSE** | **0.162 ft** |
| Median | −0.014 ft |
| 16th / 84th pct | −0.090 / +0.016 ft |
| Min / max | −7.538 / +11.425 ft |
| \|diff\| > 1 ft | 0.23% of cells (6,510 cells) |
| \|diff\| > 5 ft | 0.01% of cells |

RMSE 0.162 ft comfortably clears the ASPRS QL2 non-vegetated-terrain
threshold (RMSEz ≤ 0.328 ft / 10 cm) — cite this directly in the memo's
accuracy statement.

**Outlier spatial pattern** (the 6,510 cells with \|diff\| > 1 ft):
- 715 cells vendor-higher (I removed something they kept), 5,795 cells
  mine-higher (I kept something they removed) — my SMRF run is somewhat
  more permissive about calling elevated points "ground" than USGS's
  delivered classification, at this magnitude not concerning.
- West half (x < 982,613): 3,879 outlier cells. East half: 2,631. **Not**
  concentrated in the residential block as expected going in — instead they
  hug the N–S wash channel and cluster hardest at one road/wash crossing
  near (982,600, 402,400).
- Zoomed into that crossing in both vendor and mine hillshades: both show
  the same feature (a culvert or low-water crossing), just disagreeing by
  about a foot on the exact edge location — an IDW interpolation artifact
  at a sharp linear break, not a real classification error.

## RESOLVED: internal consistency / precision floor (item #3 of the original plan)

**Surface used**: interior of the center-pivot irrigation field (laser-
leveled by design — legitimate flat reference without needing external
imagery; satellite imagery was attempted via the browser pane but
screenshots failed to render this session, so this was a deliberate
substitution, confirmed with the user).

Sample box: 983370–983470 ft (E) × 400570–400670 ft (N), 100×100 ft,
picked well clear of the pivot pole and the field edge (radius ~540 ft).

**Method**: raw class-2 points pulled directly from the LAZ (not the
gridded/IDW-smoothed DEM, which would mask real point noise), fit a plane
by least squares to remove the field's genuine drainage grade, then looked
at residual scatter.

| Stat | Value |
|---|---|
| Points in box (total / ground) | 2,369 / 2,123 |
| Fitted grade | 0.50% (0.0012 ft/ft E, −0.0049 ft/ft N) — real design slope |
| **Residual RMSE** | **0.104 ft** (~1.25 in) |
| Residual std dev | 0.104 ft |
| Residual min / max | −0.666 / +0.325 ft |
| Residual 5th / 95th pct | −0.167 / +0.159 ft |
| Raw Z range in box | 1.000 ft |

0.104 ft is tighter than the 0.162 ft vendor-diff RMSE, as expected —
disagreement between two independent classifications should exceed one
dataset's own internal point noise.

**Not yet acted on**: the spatial map of residuals shows visible diagonal
banding (alternating slightly-high/slightly-low strips), not uniform random
noise. This looks like flight-line structure and is a strong lead-in to
the next planned check (swath overlap, below) — flagged to the user, not
yet investigated further.

Images (currently in session scratchpad only, not yet saved into repo):
- Vendor-diff residual histogram
- Outlier spatial map (hillshade + red/blue outlier overlay)
- Wash-crossing zoom, vendor vs. mine, side by side
- Pivot-field residual histogram + spatial scatter (the banding plot)

## RESOLVED: swath overlap check (item #4 of the original plan)

Split by `PointSourceId`: 4 flight lines. Two dominant, adjacent lines —
**519** (4,129,283 pts, X 981587–985113) and **600** (3,679,198 pts,
X 980113–983435) — overlap in a shared band, X 981587–983435 (1,848 ft
wide, full tile height). Two smaller slivers (518, 601) turned out to be
fully contained within 519's/600's extents, not independent overlaps.
Rebuilt each line's ground surface independently with identical
`w120_s0.15_t1.6` parameters, restricted to the shared band, then
differenced (`output/dem/diff_swath_600_minus_519.tif`).

| Stat | Value |
|---|---|
| Valid overlap cells | 972,708 / 1,026,872 (94.7%) |
| **Mean (600 − 519)** | **+0.124 ft** |
| Median | +0.120 ft |
| Std dev | 0.184 ft |
| RMSE | 0.222 ft |
| 16th/84th pct | +0.037 / +0.210 ft |
| \|diff\| > 0.26 ft | 10.1% of cells |

This is a systematic, one-directional offset, not noise — the spatial map
shows a near-uniform bias across almost the entire overlap band (heavier
disagreement along the wash is a separate, expected breakline effect).
Consistent with a mild vertical calibration/boresight discrepancy between
flight lines **in the source collection**, not a processing artifact.
**This explains the diagonal banding from item #3**: that sample box
(983370–983470) sits at the eastern edge of this same overlap zone, so the
main DEM's per-cell IDW blend of both lines produces exactly this pattern.

## RESOLVED: NGS control (item #5 of the original plan)

Queried NGS's Data Explorer API (`geodesy.noaa.gov/api/nde/bounds`) for the
tile bounds (converted to lat/lon: 32.09202–32.10588°N,
111.01215–110.99587°W). **Zero marks fall inside the tile.** Widened the
search and checked the four nearest candidates individually via their raw
datasheets (`/api/nde/pid`):

| Mark | Location vs. tile | Why unusable |
|---|---|---|
| SAN XAVIER MISSION (CZ1976) | 430 ft N of tile edge | No published orthometric height |
| SAN XAVIER MISSION CROSS (CZ1975) | 375 ft N of tile edge | No published orthometric height |
| X 349 (CZ0166) | 355 ft E of tile edge | `condition: MARK NOT FOUND` since 2009; horizontal position `SCALED` (imprecise) |
| PA 2 (CZ1835) | ~2,345 ft E, 295 ft N | GOOD condition, but height derived via VERTCON3 (datum-conversion estimate, not direct observation), no published vertical order; also too far away |

**Unit trap caught along the way**: a summarized version of the API
results initially labeled `orthoHt` as feet. Wrong — `geoidHt` values
(~-29.5) only make sense as **meters** (matches the known GEOID18
undulation for southern Arizona, ~-31 m; in feet it'd be far too small).
All `orthoHt` values from this API are meters.

**Conclusion**: no usable external vertical control exists in or near this
tile. A true external NVA (per ASPRS Positional Accuracy Standards) would
require new fieldwork (e.g., a static GPS occupation on PA 2). Stated as a
scope limitation in the memo, not a data quality failure.

## RESOLVED: point density + void map (item #6 of the original plan)

**Bug caught and fixed first**: PDAL's `writers.gdal` with `output_type:
count` defaults to a *radius-based* search around each cell center (default
radius = `resolution * sqrt(2)`), not a clean non-overlapping histogram bin
— this inflated the first attempt's density by ~6x (23.2 pts/m² vs. the
tile's known ~3.7 pts/m², which was the tell). Fix: `"binmode": true`,
which does true per-cell binning. Built from **first returns only**
(`ReturnNumber[1:1]`), 3 ft cells, aligned to the standard tile grid.

| Stat | Value |
|---|---|
| Mean density | 3.697 pts/m² (matches documented ~3.7) |
| Median density | 2.392 pts/m² |
| **Void cells (zero returns)** | **2.33%** of tile |
| Cells below QL2 minimum (2 pts/m²), combined with voids | **19.4%** of tile |

The tile-wide average clears QL2, but nearly 1 in 5 cells locally falls
short — exactly why a per-cell check matters over an average. Spatially,
the density map lines up with the item-4 flight-line geometry: the
519∩600 overlap band is visibly higher-density and almost void-free;
single-coverage strips on either side run at/below the QL2 floor. Voids
follow the scanner's oscillating scan-line geometry (gaps between sweeps,
healed by a second overlapping pass), not the wash or any single feature —
checked and ruled out a water-related dropout pattern.

Files: `output/dem/density_count_3ft.tif` /
`density_count_3ft_aligned.tif`.

## RESOLVED: contours (item #7 of the original plan)

`gdal_contour -a elev_ft -i 2.0` on `dem_w120_s0.15_t1.6.tif` →
`output/contours/contours_2ft_w120_s0.15_t1.6.gpkg`. 12,258 features,
2492–2650 ft. Visual check against hillshade looks right (hills, wash,
pivot-field grade all track cleanly). Dense contour clutter in the NE/SE
ag fields is real 2 ft-scale micro-terrain (crop rows) at this fine
interval, not a defect.

## RESOLVED: DSM and CHM (item #8 of the original plan)

DSM: all non-noise points (`Classification![7:7]`), max elevation per
3 ft cell, **`binmode: true`** (same fix as item #6 — the default
radius search would smear building/vegetation edges into neighboring
cells). CHM = DSM − DEM (`w120_s0.15_t1.6_aligned`), both grids aligned to
the standard tile extent first.

| Stat | Value |
|---|---|
| Mean | 0.92 ft |
| Median | 0.09 ft |
| Std dev | 3.20 ft |
| Min / max | −8.36 / 72.87 ft |
| > 8 ft (roof-scale) | 5.04% of cells |
| < 0 ft | 22.2% (expected — DSM/DEM are independently gridded, minor mismatch at edges, same effect as the item-2 wash-crossing artifact) |

Median near zero matches the tile's documented near-absent canopy. Visual
check: dark rectangular CHM outlines line up exactly with the residential
building footprints that show as voids in the ground hillshade (confirms
those are genuine roofs — distinct from the graded pad investigated in
item #1). A strong CHM line follows the wash (riparian vegetation, as
expected), and the ag fields show almost nothing. Max value (72.87 ft) is
almost certainly a pole or similar point feature, not investigated further.

## DONE: QC memo (item #9 of the original plan)

Written to `output/reports/qc_memo.md`. Covers method/parameters, the
accuracy assessment (items #2–6), the roof/pad investigation (item #1),
deliverables list, and a limitations section (vertical datum, no external
control, the flight-line offset, uneven point coverage). **Note**:
`output/reports/` is inside the gitignored `output/` tree, so this file is
currently untracked and invisible to git — see Open questions.

## RESOLVED: second tile, harder terrain — Tucson Mountains (item #10)

**Tile**: `USGS_LPC_AZ_PimaCounty_2021_B21_484572.laz` (83.8 MB / 2021
collection), covering the Wasson Peak vicinity of Tucson Mountain Park.
Found via the TNM API (`tnmaccess.nationalmap.gov`); picked over a
same-vintage 2015 tile (which turned out to only clip the range's edge,
too weak on relief) and a 2011 legacy tile (196 MB, no real advantage).
Reprojected copy at `data/raw/tucson_mtns_484572_epsg6405.laz`.

**CRS mismatch, caught and fixed**: source tile is NAD83(2011) / UTM Zone
12N (EPSG:6341) horizontal + NAVD88 height–Geoid18 (EPSG:5703) vertical,
**entirely in meters** — not this project's EPSG:6405 ft. Reprojected via
PDAL (`scripts/pipelines/pipe_reproject_484572.json`). First attempt
silently left Z in meters while X/Y correctly converted to feet — because
the target CRS (EPSG:6405) has no vertical component, `filters.reprojection`
had nothing to transform Z against, so it passed through unchanged. Caught
by checking the output header against expected magnitude, not by assuming
it worked. Fixed with an explicit `filters.transformation` scale matrix on
Z. **Second unit subtlety**: EPSG:6405 uses the **international foot**
(0.3048 m exactly, EPSG:9002), not the US survey foot (0.30480061 m,
EPSG:9003) — this project's docs originally (wrongly) called it "US
survey feet" throughout; fixed everywhere after this was independently
confirmed by the original tile's own project documentation too (see the
vertical datum/NVA item below — both source reports state "International
Feet" verbatim). Conversion factor used is `3.280839895`, not
`3.280833333`.

**Tile stats after reprojection**: 3,309 × 3,310 ft (~251 acres),
27,722,077 points (~27.7 pts/m², QL1-class — ~7.5x denser than the original
tile's QL2 3.7 pts/m²). Raw header showed an absurd 5,144 ft "relief"
(781–2349 m) — that max was a single classification-18 (high noise) point.
Excluding noise classes 7/18: real range 2,727.4–3,055.8 ft, **328.4 ft of
relief** over a much smaller area than the original tile (164 ft over 574
acres) — meaningfully steeper per unit area, as intended. Also notable:
this tile's vertical datum **is** explicitly declared (NAVD88, Geoid18) —
unlike the original tile's blank field; indirectly supports the "presumed
NAVD88" assumption made there.

**Parameter derivation — measured, not guessed.** Built a probe DEM from
vendor's own class-2 points and ran `gdaldem slope -p`:

| Percentile | Slope |
|---|---|
| Median | 28.0% |
| p90 | 91.5% |
| p95 | 114.2% |
| p99.9 | 192.5% (near-vertical rock faces) |

**Five iterations to a final parameter set** (all pipelines in
`scripts/pipelines/pipe_tucson_*.json`):

1. `w33_s1.0_t3.3` — window 33 ft (down from 120 ft; no large graded pads
   here, only sparse vegetation, and a big window in steep terrain lets
   the surface cut across real ridges/gullies), slope 1.0 (just under
   measured p90), cell 1.6 ft (down from 3.3 ft, supported by ~7.5x
   higher point density), threshold 3.3 ft, scalar 1.25. Hillshade showed
   plausible ridge/gully/trail structure, but a dense fine speckle texture
   the user identified as **vegetation**.
2. `w33_s1.0_t1.3` — tightened threshold to 1.3 ft (hypothesis: base
   vertical tolerance too loose). **No visible change** — ruled threshold
   out as the controlling lever.
3. `w33_s0.6_t1.3` (+scalar 0.75) — backed slope off from 1.0 toward the
   measured *median* (28%), reasoning that the p90 value used to set
   `slope=1.0` may itself have been inflated by vegetation-on-slope bumps
   already present in vendor's "ground" points. **Also no visible change**
   — with window held constant across all three attempts, this pointed at
   `window` as the actual bottleneck (SMRF's opening can't erode away
   clusters wider than the window).
4. `w65_s0.6_t1.3` — widened window to 65 ft. **This step is retracted;
   see the correction note below.** It was originally recorded as showing
   a real (if subtle) effect — a diff against attempt 1 up to 8.08 ft,
   read as a marginal speckle reduction traded against a loss of real
   shadow/relief detail. Both observations were artifacts of comparing
   against the wrong baseline: `dem_tucson_w65_s0.6_t1.3.tif` is
   byte-identical (checksum-verified, including an independent
   from-scratch re-run of the pipeline) to attempt 3's output. Widening
   `window` from 33 to 65 ft changed nothing on this tile.
5. **`lastreturn_w33_s0.6_t1.3` — final.** Checked `NumberOfReturns` on
   this tile: 35.16% multi-return, mean 1.4137 (vs. the original tile's
   1.023) — real canopy penetration (cacti, palo verde, ironwood), and a
   physically-grounded signal instead of pure geometry. Added
   `filters.returns` (`groups: "last,only"`) before ELM/outlier/SMRF to
   drop first/intermediate returns (near-certain canopy hits). Window
   stayed at 33 ft — not "reverted," since attempt 4 never actually moved
   it anywhere (see above). Result: shadow/detail crispness matches
   attempts 1–3; fine speckle persisted at similar density.
   **User-confirmed conclusion**: this is expected, not a failure — a
   solid single-return cactus hit is physically indistinguishable from a
   solid rock hit by return-count alone. Further separation would need
   intensity-based classification or co-registered NDVI/multispectral
   data, outside this project's scope. **Stopped here as a defensible,
   documented stopping point** ("Matches my read" — user agreed).

**Correction (2026-08-10, later session)**: item 4 above was wrong.
Checksums across all five iteration DEMs show only attempts 3 and 4
(`dem_tucson_w33_s0.6_t1.3.tif` / `dem_tucson_w65_s0.6_t1.3.tif`) are
byte-identical; verified two ways — a direct MD5 comparison, and an
independent from-scratch re-run of `pipe_tucson_w65_s0.6_t1.3.json` to
rule out a stale/corrupted file. The original "8.08 ft diff" was real,
but it was measured against attempt 1, which had already diverged from
attempt 3 via the slope/threshold changes in attempts 2 and 3 — it was
re-detecting that earlier change, not the window change, because it
diffed against the wrong baseline (attempt 1 instead of the immediately
preceding attempt 3). The "loss of shadow/relief detail" read on
attempt 4 was almost certainly the same file as attempt 3 evaluated
twice and perceived differently, not a real effect.
**Consequence: the empirical claim that widening `window` trades detail
for reduced speckle on this tile is unsupported and retracted.** The a
priori design reasoning for keeping `window` narrow here (avoiding a
window wide enough to cut across real ridges/gullies) still stands as
reasoning — it was just never actually tested; only the threshold change
(1→2) and slope change (2→3) are confirmed real by checksum.

**Mechanism, found in PDAL's own source** (`filters/SMRFilter.cpp`,
`progressiveFilter()`, PDAL 2.10.0): `window` is a genuine linear-unit
distance, converted to a pixel radius via `max_radius =
ceil(window / cell)` — for this tile (cell 1.6 ft), window 33 ft → radius
21, window 65 ft → radius 41. Not a units bug, not extent clamping. But
the algorithm progressively opens the surface from radius 1 up to
`max_radius`, flagging non-ground cells against a threshold that grows
with radius too (`threshold = slope * cell * radius`) — so once the
structuring element exceeds the largest real non-ground feature actually
present in the data, further radius growth stops flagging anything new.
For this tile, whatever separates ground from non-ground apparently
converges well before radius 21, so 21 and 41 give identical output.
This is corroborated by the *same* pattern on the original tile's own
window sweep (see item #1 above): `dem_w120_s0.15_t1.6.tif`,
`dem_w180_s0.15_t1.6.tif`, and `dem_w240_s0.15_t1.6.tif` are all
byte-identical to each other (radii 37/55/73 at cell 3.3 ft), while
`dem_w60_t16.tif` (radius 19) differs from all three — convergence
somewhere between window 60 and 120 ft on that tile, exactly the kind of
threshold this mechanism predicts. Window only matters up to the scale
of the largest real feature in the data; beyond that, more window is a
no-op by construction, on both tiles.

**Final parameters**: `filters.returns groups=last,only` →
ELM (cell 33 ft, threshold 3.3 ft) → statistical outlier (mean_k 8,
multiplier 3.0) → SMRF (cell 1.6 ft, window 33 ft, slope 0.6,
threshold 1.3 ft, scalar 0.75) → class-2 filter → IDW raster, 1.6 ft.

| Parameter | Original (flat desert) | Tucson (steep, vegetated) | Why |
|---|---|---|---|
| window | 120 ft | 33 ft | No large pads here; big window cuts across real relief |
| slope | 0.15 | 0.6 | Measured terrain far exceeds flat-desert norms (median 28%, p90 91.5%) |
| threshold | 1.6 ft | 1.3 ft | Tighter, to reject low vegetation given slope already extends reach |
| scalar | 1.25 | 0.75 | Slows tolerance growth, compensating for higher slope |
| cell | 3.3 ft | 1.6 ft | ~7.5x higher point density supports finer resolution |
| pre-filter | none | last/single-return only | 35.16% multi-return vs. 1.023 mean on original — real canopy signal exploited |

Deliverables: `output/dem/dem_tucson_lastreturn_w33_s0.6_t1.3.tif`,
`output/hillshade/hs_tucson_lastreturn_w33_s0.6_t1.3.tif`.

## RESOLVED: vertical datum, sensor, and NVA (original tile)

Found the project's authoritative documentation on USGS's rockyweb server,
in a parallel directory structure to the LPC tile downloads themselves
(`Elevation/metadata/<project>/<subproject>/reports/`, as opposed to
`Elevation/LPC/Projects/<project>/<subproject>/` for the tiles) — the
per-tile XML metadata that ships with the LAZ is a thin auto-generated
stub (vertical accuracy listed as "N/A", process steps "unknown") and
does **not** contain any of this; it lives one level up, in a full report
package. Two independent documents, confirming each other:

- **"2015 LiDAR Vertical Accuracy Assessment.pdf"** — Psomas, signed and
  sealed by Patrick McGarrity (AZ RLS #49459), Feb 9 2015.
- **"Final_2015LiDAR_Report_PAG_Tucson.pdf"** ("LiDAR Campaign for the PAG
  Tucson, Report of Survey") — Sanborn Map Co. (the acquisition
  contractor), August 2015.

| Item | Value | Source |
|---|---|---|
| **Vertical datum** | **NAVD88**, orthometric heights via **Geoid12A** | Both documents, independently |
| Horizontal datum | NAD83(2011), Arizona State Plane Central, **International Feet** | Both documents — independently confirms the EPSG:6405 international-foot finding from item #10 |
| Sensor | **Leica ALS70 HP**, in a Sanborn Aero-Commander 500-B (twin-engine, piston) | Sanborn report §2.2 |
| Acquisition dates | **Feb 20–26, 2015**, 14 flight missions in ~1 week | Sanborn report Table 2, confirmed independently by the per-tile XML's "20150220"–"20150226" |
| Acquisition contractor | Sanborn Map Co. | Sanborn report |
| Accuracy assessment / QA | Psomas (Patrick McGarrity, PLS) | Psomas report |
| **NVA, raw LAS** (134 ASPRS-compliant check points, all non-vegetated) | **RMSEz = 10.3 cm** (±20.2 cm @ 95% CI) | Psomas report — technically a hair over the ≤10 cm QL2 target, not flagged as a failure by the surveyor |
| **NVA, bare-earth DEM** | **RMSEz = 8.8 cm** (±17.2 cm @ 95% CI) | Psomas report — clears the QL2 target |
| Sanborn's own internal pre-classification check (32 points, different from the above) | RMSE 0.179 ft, mean −0.010 ft, std dev 0.181 ft | Sanborn report Table 3 |
| VVA (vegetated vertical accuracy) | **Not assessed** — "All ... areas are classified as Non-vegetated" | Psomas report, stated explicitly |

**Resolves the "day 307" question too**: the LAS header's file-creation
date (day 307 = Nov 3, 2015) is when USGS/Sanborn finalized and
repackaged the tile, months after the actual Feb 2015 flights — normal,
given classification, QC, and final delivery all happen after acquisition.

**Cite in the memo, verbatim where useful**: this fully replaces the
"presumed NAVD88" caveat with a sourced, confirmed fact, and gives the
memo a real, citable NVA figure (8.8 cm bare-earth DEM RMSEz) instead of
just this project's own internal/relative accuracy checks.

## DONE: hydrologic analysis (item #11, beyond the original 10-item plan)

Tooling: **WhiteboxTools** (`pip install whitebox`), not GRASS/QGIS — neither
was installed in this environment, and WBT is a single lightweight package
with purpose-built hydrology tools, no GIS desktop app required. Scripts:
`scripts/hydrology_0[1-8]_*.py`. All outputs in `output/hydrology/`.
Input: `dem_w120_s0.15_t1.6.tif` (the original tile's canonical DEM).

**Depression handling**: `BreachDepressionsLeastCost` (dist=1000, min_dist)
first — minimal terrain modification, carves through barriers rather than
flooding — then `FillDepressions` (fix_flats) on whatever remained
unbreached. All 101,466 pits were fully resolved by breaching alone (0
unresolved). Impact quantified by direct DEM differencing, not a tool
summary line:

| Stage | Cells changed | Volume | Max change |
|---|---|---|---|
| Breach only | 170,297 (6.13%) | −116,457 cu ft (net cut) | −15.31 ft cut |
| Residual fill | 53,815 (1.94%) | +179,471 cu ft (net fill) | +9.27 ft raise |

**Spatial breakdown** (re-classified at a coarser, more meaningful 0.05 ft
change threshold — 106,112 cells total, vs. 213,602 at the stage-1 script's
more permissive 0.01 ft threshold; both numbers are real, they're just
answering slightly different questions): split by the actual derived wash
centerline (not a guessed line) into natural-west / ag-east, plus a
separate tile-boundary-adjacent (<150 ft) flag:

| Region | Cells | Volume | Note |
|---|---|---|---|
| Natural terrain, west of wash | 23,663 (22%) | −24,002 cu ft (net cut) | Breach-dominated — reassuring, see below |
| Ag area, east of wash | 64,678 (61%) | −29,351 cu ft (net cut) | Expected — engineered surfaces |
| Tile-boundary-adjacent (either side) | 17,771 (17%) | **+115,726 cu ft (net fill)** | Dominant fill volume; likely truncation artifacts |

**Key finding**: the real (non-edge) terrain — both natural and ag — is
**breach-dominated (net cut)**, not fill-dominated. The large net *fill*
volume is concentrated almost entirely at the tile boundary. Checked one
specific case directly: a 9.27 ft residual-fill blob at (985047, 403378),
~50 ft from the NE corner — no data void, but genuine steep terrain right
at the edge, consistent with a real depression whose natural outlet lies
outside the tile (so it reads as artificially closed). This ties the
fill-impact and boundary-truncation concerns together: truncation doesn't
only affect flow accumulation/streams, it shows up as artifactual fill
right at the edges too.

**Flow direction/accumulation**: standard D8 (`D8Pointer` +
`D8FlowAccumulation`).

**Stream threshold — no clean statistical answer, so the visual check did
the deciding**: slope-area analysis (log-log bins of local slope vs.
contributing area) restricted to the natural terrain west of the wash
(the full-tile version was contaminated by the ag fields' engineered,
non-natural drainage geometry — a long flat 1.5-1.8% plateau spanning
0.03-10 acres that isn't a real hillslope-to-channel signature). Even
restricted to natural terrain, there was **no sharp break** — a steep
initial decline (microtopographic noise near ridge crests, 0-200 sq ft)
gives way to a *continued, gradually shallowing* decline out to several
acres, then noise from small sample sizes beyond ~5 acres. This gave a
loose prior (order of 0.03-2 acres), not a number.

Extracted candidate networks at 50 to 40,000 cells and checked each
against the hillshade, specifically including the pivot field in frame.
**Important finding, not just a threshold-tuning note**: the pivot
field's concentric wheel-track ring (a real, physically continuous
depression — confirmed by its measured 0.50% design grade in the item-3
internal-precision check) persists strongly through 1-2 acres and only
fully clears around 4-8 acres — by which point real hillslope tributaries
in the natural terrain are lost. **No single threshold satisfies both.**
This isn't fixable by raising the number; a wheel rut is geometrically
indistinguishable from a natural channel to D8 routing. Chose **5,000
cells (45,000 sq ft / 1.033 ac)** — clean tributary structure in natural
terrain — and instead flag/exclude the ag-area portion of the network in
the deliverable rather than chase a bigger number.

**Vectorized** (`RasterStreamsToVector`): 323 segments, ~108,068 ft total
length (includes the flagged ag-area segments).

**Boundary-crossing scan** (all 4 tile edges, cells above threshold):
23 distinct crossings. Dominant ones: **north edge (982406, 403427),
258.4 ac accumulated — the main wash outlet**; a second, smaller braided
channel also exits north (983465, 403427), 152.5 ac; and critically, a
**south edge entry (984053, 398429), 3.9 ac** — confirming the wash is
**through-flowing** (enters south, exits north; tile's lowest elevations
are near the NE corner, so drainage runs south-to-north here, consistent
with the regional Santa Cruz River drainage). An east-edge crossing
(985112, 399266), 25.1 ac, is a separate secondary drainage.

**Watershed**: delineated from the main outlet (pour point snapped via
`JensonSnapPourPoints`) using `Watershed`. **258.40 acres (0.4037 sq mi,
45% of the tile)** — matches the outlet's own accumulation value exactly
(consistency check passed). **Stated explicitly as a lower bound**, both
in this file and directly on the deliverable figure itself: this tile is
isolated (no adjacent tiles, same situation as the SMRF edge-effect
limitation below), and a through-flowing system's true catchment
necessarily extends beyond what a single tile can show.

**Deliverables** (`output/hydrology/`): `dem_02_filled.tif` (corrected
DEM), `d8_pointer.tif`, `d8_flow_accum_cells.tif`, `streams_final_t5000.gpkg`,
`watershed_main_wash.gpkg`, `fill_impact_classified.png` (impact by
region), `hydrology_final_overlay.png` (streams + watershed + caveats,
for satellite comparison), plus the full threshold-comparison and
slope-area figures as audit trail.

## Known Limitations

**Tile-boundary edge effects (SMRF, not buffered).** SMRF's ground
classification degrades near a tile's edge, within roughly one `window` of
the boundary, because points there lack full neighborhood context —
whatever's just outside the tile simply doesn't exist in that pipeline
run. The correct fix is buffering: pull in a margin of points from
adjacent tiles, classify with the margin included, then crop back to the
true tile boundary before writing output. This is not implemented —
this project currently has zero pairs of spatially-adjacent tiles (San
Xavier and Tucson Mountains don't touch), so there's nothing to buffer
from and no way to test the logic. Writing speculative, untestable
buffering code seems worse than being direct about the gap. Documented
here and in the QC memo; the concrete design for later: a spatial index
over available tiles' bounds, read-neighbor-and-crop, activated via an
optional `--buffer-ft` flag once this project actually has adjacent tiles
to test against.

**Rock vs. solid-return vegetation on the Tucson tile is not separable
with this data.** A solid single-return cactus hit and a solid rock hit
are geometrically indistinguishable by SMRF or by return-count alone
(§ item #10). Confirmed with the user as a permanent limitation, not
something to keep chasing — would need intensity-based classification or
co-registered NDVI/multispectral data this project doesn't have.

## Open questions

None currently open. (Vertical datum and the `output/reports/` gitignore
question, previously listed here, are both resolved — see above and
Housekeeping below.)

## Next steps, in order

All ten original items, plus everything added since, are done:

1. ~~Roof vs. pad~~ — **DONE**
2. ~~Grid alignment fix + vendor diff/RMSE~~ — **DONE**
3. ~~Internal consistency (flat surface)~~ — **DONE**
4. ~~Swath overlap check~~ — **DONE**
5. ~~NGS control~~ — **DONE** (concluded: none usable)
6. ~~Point density + void map~~ — **DONE**
7. ~~Contours~~ — **DONE**
8. ~~DSM and CHM~~ — **DONE**
9. ~~QC memo~~ — **DONE**
10. ~~Second tile, harder terrain~~ — **DONE**
11. ~~Hydrologic analysis (fill, flow, streams, watershed)~~ — **DONE**

Also done, beyond the original numbered plan: the batch processor
(`scripts/batch_process.py`), the vertical-datum/sensor/NVA research
(now a sourced, confirmed fact — see below), the CHM tall-point outlier
investigation (§3.6 of the QC memo — a utility pole, not noise), the
International-vs-US-survey-foot correction across every file, and a
polished PDF deliverable (`scripts/build_report.py` →
`output/reports/qc_report.pdf`, 17 pages, ~15.9 MB) that assembles
`qc_memo.md` and all 10 rendered figures (`scripts/render_figures.py`,
including a new `fig10_fill_impact.png`) into one report. `qc_memo.md`
itself grew a new §5 "Hydrologic Derivatives" section this session
(items #11's findings — pit/fill volumes, stream threshold reasoning,
watershed lower-bound — had never been written into the memo text
itself, only into figures/session memory), with sections 5–9 renumbered
accordingly and every cross-reference (`§N`) updated to match.

**`build_report.py` design notes** (for future edits to `qc_memo.md`):
it parses the memo's markdown into reportlab flowables directly rather
than hand-duplicating memo content — so editing `qc_memo.md` and
re-running the script is the normal workflow, not editing the PDF
script. It's a block-based parser (blank-line-separated blocks, not
line-by-line) specifically because markdown soft-wraps continuation
lines without blank lines between them — a line-by-line parser was
tried first and silently fragmented wrapped list items and the
`**Label:**` metadata block on the title page (each wrapped line was
misread as a new, separate item). Figures are placed via `FIGURE_MAP`,
keyed by exact section-heading text, at the end of whichever section's
text first discusses them. Source figures render at 300 DPI in
`render_figures.py` (kept full-res for standalone portfolio use) but
`make_image()` re-encodes a downsampled copy at 170 DPI into
`output/figures/_pdf_cache/` before embedding — skipping this dropped
the PDF from 94.7 MB to 18.4 MB (later 15.9 MB, see below) with no
visible quality loss at normal zoom. Table rows are wrapped in
`KeepTogether` (small tables only, 4-6 rows) rather than left to
reportlab's default mid-table page-splitting, which orphaned a header
row alone at the bottom of a page with its data rows stranded on the
next page, unrepeated.

**Page count, checked against the original "~11 page" estimate**: final
build is 17 pages (`§1–§9` heading positions checked directly against
rendered page numbers, not eyeballed). Two real layout bugs inflated an
early draft to 23 pages and were fixed before delivery: a forced page
break before every top-level section wasted mostly-blank pages (23→20),
and the ordered-list numbering bug above was also fragmenting list text
into extra stray paragraphs (20→18). What's left is legitimately new
content, not residual layout waste: §5 Hydrologic Derivatives (added
this session, ~3 pages including 3 figures) didn't exist in the 11-page
scope at all, and the original §1–§4 content alone already runs ~9
pages once each accuracy-assessment figure gets a full page at
readable size — the 11-page estimate simply predates both the
hydrology section and a realistic figure-size accounting. One genuine
layout tightening was still applied: the two appendix hillshades
(secondary, corroborating evidence for §4, not primary figures) were
moved from one full page each onto a single shared page, side by side
(18→17).

Remaining, purely optional:
- Fold the Tucson tile's findings into a second QC memo/addendum, if the
  portfolio wants that tile written up as a standalone deliverable too.
- Drop the ag-flagged segments from the hydrology stream vector entirely,
  if a cleaner (rather than annotated-and-flagged) deliverable is wanted.

## Housekeeping / repo state

Commits this project, in order: `503a6a2` (initial), `f42b6d8` (remove
data/outputs from version control), `fb7b0cd` (stray junk files removed +
`.gitignore` added), `221a2f5` (grid-alignment fix + first `CLAUDE.md`),
`8013a91` (local permissions allowlist), `4b96512` (swath-overlap
pipelines), `64ec83c` (density/DSM pipelines + Tucson parameter-search
pipelines), `46b2c4e` (batch processor), `eec709f` (`output/reports/`
gitignore exception + QC memo committed), `5d3ebfb` (vertical datum/NVA
confirmed, CHM outlier resolved), `3b3a124` (International vs. US survey
foot fixed everywhere, Geoid12A + sealed-document provenance added),
`5ef9130` (hydrologic analysis, item #11). This `CLAUDE.md` update, plus
`docs/session-log.md` and `docs/PROJECT_SUMMARY.md`, are being committed
together right after this update (see the session log for the date).

- `data/raw/` now holds three files, all gitignored: the original tile,
  the raw downloaded Tucson tile (`USGS_LPC_AZ_PimaCounty_2021_B21_484572.laz`,
  meters/UTM12N, kept as the untouched source), and the reprojected
  working copy (`tucson_mtns_484572_epsg6405.laz`, EPSG:6405 ft).
- `output/` is gitignored except `output/reports/` (`.gitignore` uses
  `output/*` + `!output/reports/`, not a plain `output/` exclude — a
  bare `!output/reports/` does NOT work while the parent is fully
  excluded, git won't traverse into an excluded directory to find
  negation rules inside it; verified with `git check-ignore` before
  committing). `output/reports/qc_memo.md`, `batch_qc.csv`, and
  `batch_qc_README.md` are tracked; all rasters/hillshades stay
  regenerated, not versioned.
- Session PNG figures (hillshades, diff maps, histograms, comparison
  crops) live only in the session scratchpad, not the repo, unless
  explicitly sent to the user as deliverable images.

## How I want to work
- Compute the numbers; I'll judge whether they're plausible. You can't see
  a hillshade and I can — when a check is visual, generate the image and
  hand it to me rather than guessing at what it shows.
- Change one parameter at a time. Keep every run's output.
- Flag anything that looks like systematic error. Internal consistency
  checks pass perfectly on a surface that is uniformly wrong.
- Reference the USGS LiDAR Base Specification and ASPRS Positional Accuracy
  Standards by name where relevant — that language belongs in the memo.
- **Any figure generated for me to look at gets saved to `output/figures/`
  at the same time it's shown, not left in the session scratchpad.** This
  was violated for most of this project's history — the vendor-diff,
  swath-offset, density/void, and CHM figures were all generated, shown,
  and discussed at length, then existed nowhere when it came time to
  build the report. The underlying `.tif` data survived (it's a real
  file); the rendered figure didn't. Scratchpad is temporary by design;
  `output/figures/` is not. `scripts/render_figures.py` is the reusable
  home for this — it has shared scale-bar/north-arrow helpers so every
  figure looks consistent; add new figures to it rather than writing a
  one-off scratchpad script.
- **Any computed result gets written into the memo at the time it's
  computed, not reconstructed later.** Same root cause as the figures
  rule above — treating memory/scratchpad as durable when it isn't —
  and it has now bitten this project twice. First time: the vendor-diff,
  swath-offset, density/void, and CHM figures existed nowhere when it
  came time to build the report (see above). Second time: the entire
  hydrologic-analysis workflow (item #11) was run, figured, and
  captioned, but its actual numbers — pit counts, fill/breach volumes by
  region, stream network length, watershed acreage — were never typed
  into `qc_memo.md` itself, only produced as figures and session memory.
  Writing the PDF report months later meant re-deriving those numbers
  from saved rasters instead of just citing them. When a script prints a
  number worth citing, that number goes into the memo text in the same
  session it's computed — a stat that only exists in a terminal scrollback
  or a chat transcript is one context-compaction away from gone.
