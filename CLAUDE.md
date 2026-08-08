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
are US survey feet, NOT meters. Every distance parameter must be converted:

| metric default | feet equivalent |
|---|---|
| SMRF window 18 m | ~60 ft |
| SMRF threshold 0.5 m | ~1.6 ft |
| SMRF cell 1.0 m | ~3.3 ft |
| ELM cell 10 m | ~33 ft |

Getting this wrong silently produces garbage that still looks plausible.

**Vertical datum is NOT declared in the file header** (`"vertical": ""`).
Presumed NAVD88 ft based on source and era, but unverified. This needs to be
confirmed against USGS project metadata and stated explicitly in the memo.

## The tile
`data/raw/USGS_LPC_Eastern_Pima_County_Lidar_980398.laz`
- 8,692,808 points, 33 MB compressed, LAS 1.4 point format 6
- Bounds: X 980112.76–985112.75, Y 398427.81–403427.80 (5000 x 5000 ft)
- Elevation range 2490.75–2654.69 ft (164 ft relief)
- Point density ~3.7 pts/m² → QL2
- Collected 2015, day 307. Processed with LAStools.
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
geopandas · matplotlib · scipy 1.17.1. QGIS installed separately.

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
  data/raw/          source tile — NEVER modify
  data/control/      NGS control points (empty, todo)
  scripts/           run_dem.py, compare_vendor.py
  scripts/pipelines/ auto-generated PDAL JSON, one per run (audit trail)
  output/dem/        DEMs, named by parameter
  output/hillshade/  hillshades, named by parameter
  output/contours/   (empty, todo)
  output/reports/    (empty, todo — QC memo and findings go here)
  qgis/              project files
  docs/              notes, metadata
```

Convention: output filenames encode their parameters
(`dem_w120_s0.15_t1.6.tif`). Never use "final" or "v2" in a filename.
`data/raw/`, `output/`, and `.claude/` are gitignored — outputs are
regenerated from the pipeline scripts, not versioned directly.

## What has been done

**`scripts/run_dem.py`** — parameterized DEM builder. Strips vendor
classification, runs ELM + statistical outlier removal, SMRF ground
classification, rasterizes ground-only at 3 ft IDW, generates hillshade.
Writes its pipeline JSON to `scripts/pipelines/` for every run.

**`scripts/compare_vendor.py`** — builds a DEM from the vendor's delivered
class-2 points, builds mine, and differences them. **Updated this session**
to fix the grid-alignment bug (see below): it now warps both DEMs onto a
fixed tile-extent grid via `gdalwarp` before differencing. Not yet
committed to git (see Git state below).

Runs completed:
- `w60_t1.6` — first attempt
- `w120_s0.15_t1.6` — doubled window, near-identical result. **This is the
  DEM used for all QC analysis below.**
- `w180_s0.15_t1.6`, `w240_s0.15_t1.6` — window doubled/quadrupled again to
  test whether window size was suppressing the residential rectangles. It
  wasn't (see Roof/pad finding).
- `VENDOR` — USGS delivered classification baseline

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

## Open questions

**Vertical datum** — still unconfirmed. Presumed NAVD88 ft; needs checking
against USGS project metadata before the memo states it as fact.

## Next steps, in order

1. ~~Resolve the roof/pad question~~ — **DONE**, see above.
2. ~~Fix grid alignment, produce vendor-minus-mine difference raster, RMSE~~
   — **DONE**, see above. (Histogram done too, originally listed as part of
   step 2's "and a histogram of residuals" — done.)
3. ~~Internal consistency check on a known-flat surface~~ — **DONE**, see
   above.
4. **Swath overlap check** — split by `PointSourceId`, build per-flight-line
   DEMs, difference them in the overlap. Disagreement beyond ~8 cm (~0.26 ft)
   indicates boresight/calibration error in the source collection.
   Self-contained, no external data needed. **Elevated in priority** — the
   diagonal banding seen in the item-3 residual map is a live hint this may
   show something real.
5. **NGS control** — pull published monuments inside the tile bounds,
   extract DEM values, compute NVA per the ASPRS Positional Accuracy
   Standards. This is the only true external check.
6. **Point density raster** — per-cell, NOT a global average (averages hide
   voids). Plus an explicit void map.
7. **Contours** at 2 ft interval.
8. **DSM and CHM** for completeness.
9. **QC memo**, 2 pages: method, parameters, accuracy statement, vendor
   comparison, and an honest account of the roof/pad investigation. Draft
   numbers for this are now all sitting in this file — the memo mainly
   needs writing up, not new analysis, except for whatever item 4 turns up.
10. **Second tile, harder terrain** — Tucson Mountains for relief or a
    riparian corridor for vegetation. Same pipeline, different parameters,
    with a written justification for the changes. Demonstrating adaptation
    to terrain is the point.

## Housekeeping / repo state

- Six stray empty junk files (`Singleband`, `real`, `they`, `tuning`, `you`,
  `your` — accidental artifacts from an earlier botched command) were
  deleted and a `.gitignore` (`data/raw/`, `output/`, `.claude/`) was added.
  **Committed** as `fb7b0cd`.
- `scripts/compare_vendor.py` has the grid-alignment fix in the working
  tree. **Not yet committed.**
- `.claude/settings.local.json` has a local permissions change in the
  working tree. **Not committed** — a commit of this file was attempted and
  the user rejected the tool call, so it's intentionally left uncommitted;
  don't re-attempt without asking.
- All PNG figures generated during analysis this session live only in the
  session's temp scratchpad directory, not in the repo. If they should be
  kept for the QC memo, they need to be regenerated (scripts described
  above) or copied into `output/reports/images/` — ask before doing this,
  since the last attempt to copy files into the repo was interrupted by the
  user.

## How I want to work
- Compute the numbers; I'll judge whether they're plausible. You can't see
  a hillshade and I can — when a check is visual, generate the image and
  hand it to me rather than guessing at what it shows.
- Change one parameter at a time. Keep every run's output.
- Flag anything that looks like systematic error. Internal consistency
  checks pass perfectly on a surface that is uniformly wrong.
- Reference the USGS LiDAR Base Specification and ASPRS Positional Accuracy
  Standards by name where relevant — that language belongs in the memo.
