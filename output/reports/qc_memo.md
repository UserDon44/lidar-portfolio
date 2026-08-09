# LiDAR Bare-Earth DEM — Quality Control Memorandum

**Tile:** USGS_LPC_Eastern_Pima_County_Lidar_980398.laz
**Location:** San Xavier District, Tohono O'odham Nation, Pima County, AZ
**Horizontal datum/CRS:** NAD83(2011) / Arizona Central, International Feet (EPSG:6405)
**Vertical datum:** NAVD88, Geoid12A — confirmed against project documentation (Psomas
2015 Vertical Accuracy Assessment; Sanborn Report of Survey, Aug 2015). Not declared in
the delivered LAZ header itself, but sourced independently from both the accuracy
assessment and the acquisition vendor's own report. See §6.
**Sensor / acquisition:** Leica ALS70 HP, flown by Sanborn Map Co., Feb 20–26, 2015.
Data classified QL2. Tile file itself finalized/repackaged later (LAS header shows a Nov 3,
2015 creation date — normal lag for QC and final delivery, not a second acquisition).
**Source collection:** ~3.7 pts/m² average
**Date of this analysis:** 2026-08-09

---

## 1. Source Data

8,692,808 points, LAS 1.4 point format 6, covering a 5,000 × 5,000 ft (≈574-acre)
tile. Elevation range 2,490.75–2,654.69 ft (164 ft relief). Mixed land use:
irrigated agriculture (east), residential development and two low hills (west), a
north–south ephemeral wash through the tile center, and one center-pivot
irrigation field. Vendor classification present but ground-only (classes 1–7; no
vegetation or building breakout). NumberOfReturns averages 1.023 — sparse
vegetation, negligible canopy.

## 2. Processing Method

Ground classification performed from scratch on raw returns (vendor
classification not used as an input, only as a comparison baseline):

1. **ELM** (extended local minimum) — cell 33 ft, threshold 3.3 ft — removes
   low outliers before classification.
2. **Statistical outlier removal** — mean_k 8, multiplier 3.0.
3. **SMRF** ground classification — window 120 ft, slope 0.15, threshold
   1.6 ft, scalar 1.25.
4. Ground points (class 2) rasterized at 3 ft cells, IDW, window_size 6.

Parameters were converted from PDAL/SMRF metric defaults to this tile's US
survey feet units (e.g., an 18 m default window becomes 60 ft; 60 ft, 120 ft,
180 ft, and 240 ft were all tested — see §4). All pipeline JSON is retained
per run in `scripts/pipelines/` as an audit trail.

## 3. Accuracy Assessment

### 3.1 Vendor comparison

Vendor's delivered class-2 ground surface and this project's SMRF output were
each rasterized, aligned to a common fixed grid (see note below), and
differenced.

| Stat | Value |
|---|---|
| Valid cells compared | 2,777,225 (99.9% of tile) |
| RMSE | **0.162 ft** |
| Mean / median | −0.047 / −0.014 ft |
| \|diff\| > 1 ft | 0.23% of cells |

RMSE of 0.162 ft clears the ASPRS Positional Accuracy Standards QL2
non-vegetated-terrain threshold (RMSEz ≤ 0.328 ft / 10 cm) with margin. The
0.23% of cells that disagree by more than 1 ft are not concentrated in the
residential area as expected going in — they hug the wash channel and cluster
at one road/wash crossing, where both surfaces show the same feature (a
culvert) and simply disagree by about a foot on the exact edge location — an
IDW interpolation artifact at a sharp linear break, not a classification
error.

*Grid-alignment note:* PDAL's `writers.gdal` derives each run's raster extent
from that run's own point-cloud bounding box, so two runs with different
point populations can round to different pixel grids (this tile: 1667×1667
vs. 1668×1668) and fail to difference directly. Both surfaces were forced
onto one fixed grid via `gdalwarp -te <tile bounds> -tr 3 3` before
comparison; `scripts/compare_vendor.py` now does this automatically for all
future runs.

### 3.2 Internal precision (repeatability)

Sampled raw class-2 points (not the gridded/smoothed DEM) inside the
center-pivot field, a surface that is laser-leveled by design. A plane was
fit by least squares to remove the field's genuine 0.50% drainage grade
before evaluating scatter.

| Stat | Value |
|---|---|
| Points sampled | 2,123 (100×100 ft box) |
| Residual RMSE | **0.104 ft** (~1.25 in) |
| Residual 5th/95th pct | −0.167 / +0.159 ft |

This is tighter than the vendor-comparison RMSE, as expected — disagreement
between two independent classifications should exceed one dataset's own
point-to-point noise. The residual spatial pattern showed diagonal banding
rather than pure random scatter, which led directly to §3.3.

### 3.3 Flight-line (swath) consistency

Points were split by `PointSourceId` (4 flight lines; two dominant: 519 and
600) and independently reclassified with identical parameters. The two
lines' DEMs were differenced in their shared overlap band (X 981,587–983,435
ft).

| Stat | Value |
|---|---|
| Overlap cells compared | 972,708 (94.7%) |
| **Mean offset (line 600 − line 519)** | **+0.124 ft** |
| RMSE | 0.222 ft |
| \|diff\| > 0.26 ft | 10.1% of cells |

This is a systematic, one-directional offset — not noise — visible as a
near-uniform bias across almost the entire overlap band. It is consistent
with a mild vertical calibration/boresight discrepancy between flight lines
**in the source collection**, not an artifact of this project's processing.
It also explains the diagonal banding noted in §3.2: that sample box sits at
the edge of this same overlap zone, so the combined DEM's per-cell blend of
the two lines produces exactly this pattern.

### 3.4 External control

Queried NGS's published survey monument database (Data Explorer API) for the
tile bounds: **zero marks fall inside the tile.** The four nearest marks,
individually checked against their full datasheets, are each independently
disqualifying: two (San Xavier Mission, San Xavier Mission Cross) have no
published elevation at all; one (X 349) is recorded as not found in the
field since 2009 and has only a scaled (imprecise) horizontal position; one
(PA 2) is in good, GPS-confirmed condition but is ~0.45 mi outside the tile
and its published height was derived by datum-conversion (VERTCON3) rather
than direct observation, with no published vertical order.

**Update**: no control point-in-tile check is possible, as above, but the
*project's own* authoritative NVA is now available (see header and §6) —
Psomas's 2015 vertical accuracy assessment for this exact collection,
using 134 ASPRS-compliant check points across the ~2,203 sq mi project
area (none of which happen to fall inside this specific 574-acre tile,
consistent with the NGS search above). Reported: **RMSEz = 10.3 cm on raw
LAS, 8.8 cm on the bare-earth DEM**, both against the QL2 ≤10 cm target.
This is the vendor's project-wide figure, not a check specific to this
tile, but it is a real, sourced, external NVA — stronger evidence than
"no external control was found," even though it doesn't replace an
in-tile check point.

**No true external NVA (per ASPRS Positional Accuracy Standards) is possible
for this tile without new fieldwork** — e.g., a static GPS occupation on a
nearby stable mark such as PA 2. This is stated here as a scope limitation,
not a data quality failure.

### 3.5 Point density and coverage

A true per-cell first-return density raster (3 ft cells, non-overlapping
bins) was built to check for voids that a tile-wide average would hide.

| Stat | Value |
|---|---|
| Mean density | 3.70 pts/m² (matches vendor-documented average) |
| Median density | 2.39 pts/m² |
| Zero-return void cells | 2.33% of tile |
| Cells below QL2 minimum (2 pts/m²) | 19.4% of tile (combined with voids) |

The tile-wide average meets the QL2 minimum, but nearly one cell in five
falls locally below it. The pattern matches flight-line geometry directly:
the higher-density band is the same 519/600 overlap zone from §3.3, and is
almost void-free; the single-coverage strips on either side run at or below
the QL2 floor. Voids follow the scanner's oscillating scan-line geometry
(fine gaps between sweeps, healed wherever a second flight line overlaps)
rather than clustering on the wash or any single feature.

### 3.6 DSM/CHM tall-point check

The canopy/structure height model's maximum value (72.87 ft) was checked
rather than left unexplained. Location: 981146.26, 400792.30 ft
(EPSG:6405), western residential block. Raw returns there: only 13 points
exceed 10 ft above local ground (vs. hundreds across a footprint for an
actual building, per §4 below), clustered narrowly in one axis (~3 ft)
but spread ~17 ft in the other, and nearly all are the first return of a
2-3 return pulse — consistent with a laser mostly passing through a thin,
open structure and also registering ground behind it. **Conclusion: a
utility pole or small transmission/communications tower**, not sensor
noise or a bird strike (which would show as a single isolated point, not
a small coherent cluster) and not a building or vegetation (both ruled
out by height and point density). Real feature, correctly retained.

## 4. Feature Investigation: Roof vs. Pad

Crisp rectangular features present in **both** the vendor and project ground
surfaces, in the western residential block, were investigated to determine
whether they were unremoved roof returns or real graded ground features.

Sampled DEM elevation at a structure's interior center vs. open ground ~45 ft
away: **+2.85 ft** difference. A roof would present an 8–15 ft plateau with a
sharp vertical wall; 2.85 ft is consistent with a graded, built-up
foundation pad, not roof height — confirmed on the ground by the client as
concrete pads leading to driveways and the road.

Widening the SMRF `window` from 60 to 240 ft did not remove these features.
Cause: the pad footprints (~70–100 ft across) approach the SMRF window size
being tested, so the morphological-opening surface model is pulled upward
within the window and treats the pad top as terrain — a known SMRF
limitation at this scale, not a pipeline defect.

## 5. Deliverables

| File | Description |
|---|---|
| `output/dem/dem_w120_s0.15_t1.6.tif` | Bare-earth DEM, 3 ft, IDW |
| `output/hillshade/hs_w120_s0.15_t1.6.tif` | Hillshade |
| `output/dem/dsm.tif` | Digital surface model (first surface, all non-noise returns) |
| `output/dem/chm.tif` | Canopy/structure height model (DSM − DEM) |
| `output/contours/contours_2ft_w120_s0.15_t1.6.gpkg` | 2 ft contours |
| `output/dem/diff_VENDOR_minus_w120_s0.15_t1.6.tif` | Vendor comparison raster |
| `output/dem/density_count_3ft_aligned.tif` | Per-cell point density |
| `output/dem/catalog.vrt` | Virtual mosaic of all batch-processed tiles (see §7) |
| `output/reports/batch_qc.csv` | Per-tile QC log (point counts, ground %, density, void %, runtime) |

## 6. Limitations & Recommendations

- **Vertical datum: confirmed, not presumed.** NAVD88 via Geoid12A,
  sourced from the project's own accuracy assessment (Psomas, Feb 2015)
  and the acquisition vendor's report of survey (Sanborn, Aug 2015) — not
  from the delivered LAZ's own header, which declares no vertical CRS.
  Sensor was a Leica ALS70 HP, flown Feb 20–26, 2015. Project NVA:
  RMSEz = 10.3 cm (raw LAS) / 8.8 cm (bare-earth DEM), against a QL2
  target of ≤10 cm — the raw-LAS figure is marginally over that target,
  not flagged as a failure by the certifying surveyor. VVA was not
  assessed by the vendor (project area classified entirely non-vegetated
  for accuracy-testing purposes).
- **No external vertical control falls inside this specific tile** (§3.4)
  — the project's 134 check points are spread across the full ~2,203 sq
  mi collection area and none happen to land in this 574-acre tile. The
  project-wide NVA above is real and sourced, but an in-tile check would
  require new fieldwork.
- **A systematic ~0.12 ft flight-line offset exists in the source
  collection** (§3.3) and should be disclosed to any downstream user relying
  on precision better than that in the affected area.
- Point coverage, while meeting the QL2 average, is uneven at the cell level
  (§3.5); users needing guaranteed local density should consult the density
  raster before relying on any single-coverage area for precision work.
- **Tile-boundary edge effects are not corrected for.** SMRF's ground
  classification degrades near a tile's edge, within roughly one `window`
  of the boundary, because points there lack full neighborhood context —
  whatever's just outside the tile simply doesn't exist in that pipeline
  run. The correct fix is buffering: pull in a margin of points from
  adjacent tiles, classify with the margin included, then crop back to the
  true tile boundary before writing output. This is not implemented in the
  current batch pipeline — this project currently has zero pairs of
  spatially-adjacent tiles (San Xavier and Tucson Mountains don't touch),
  so there is nothing to buffer from and no way to test the logic against
  real data. This should be revisited before processing any contiguous
  multi-tile project area.

## 7. Batch processing (multi-tile)

`scripts/batch_process.py` processes every tile in `data/raw/` using
tile-specific SMRF parameters (`scripts/tile_params.json`), is idempotent
(`--force` to reprocess), skips tiles in the wrong CRS rather than
guessing, and logs per-tile QC to `output/reports/batch_qc.csv` (column
definitions in `output/reports/batch_qc_README.md`). All currently
processed tiles are cataloged in `output/dem/catalog.vrt`. See CLAUDE.md
for the full design rationale.
