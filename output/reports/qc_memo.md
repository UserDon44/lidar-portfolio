# LiDAR Bare-Earth DEM — Quality Control Memorandum

**Tile:** USGS_LPC_Eastern_Pima_County_Lidar_980398.laz
**Location:** San Xavier District, Tohono O'odham Nation, Pima County, AZ
**Horizontal datum/CRS:** NAD83(2011) / Arizona Central, International Feet (EPSG:6405)
**Vertical datum:** NAVD88, Geoid12A — confirmed against project documentation (Psomas
2015 Vertical Accuracy Assessment; Sanborn Report of Survey, Aug 2015). Not declared in
the delivered LAZ header itself, but sourced independently from both the accuracy
assessment and the acquisition vendor's own report. See §7.
**Sensor / acquisition:** Leica ALS70 HP, flown by Sanborn Map Co., Feb 20–26, 2015.
Data classified QL2. Tile file itself finalized/repackaged later (LAS header shows a Nov 3,
2015 creation date — normal lag for QC and final delivery, not a second acquisition).
**Source collection:** ~3.7 pts/m² average
**Date of this analysis:** 2026-08-09

---

## Executive Summary

This memo documents a bare-earth DEM produced from raw LiDAR returns — not
the vendor's delivered classification — for a 574-acre tile in the San
Xavier District, Pima County, AZ. The resulting surface agrees with the
vendor's own delivered ground classification to **0.162 ft RMSE**,
comfortably clearing the ASPRS Positional Accuracy Standards QL2
non-vegetated threshold (≤0.328 ft). Three findings are worth flagging
up front: a systematic **~0.12 ft vertical offset between two
overlapping flight lines** in the source collection (§3.3); a tile-wide
point density that meets the QL2 average but leaves **19.4% of cells
locally below the minimum** (§3.5); and a set of crisp rectangular
features in the residential block, investigated and resolved as
**graded concrete pads, not unremoved roof returns** (§4). Full method,
accuracy assessment, and limitations follow below.

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

Parameters were converted from PDAL/SMRF metric defaults to this tile's
International Feet units (EPSG:9002, not US survey feet — see the CRS line
above; e.g., an 18 m default window becomes 60 ft; 60 ft, 120 ft, 180 ft,
and 240 ft were all tested — see §4). All pipeline JSON is retained per run
in `scripts/pipelines/` as an audit trail. The resulting bare-earth surface
is shown in Figure 1.

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
error. Spatial pattern in Figure 2.

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
*project's own* authoritative NVA is now available (see header and §7) —
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
rather than clustering on the wash or any single feature. See Figure 4.

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
out by height and point density). Real feature, correctly retained. See
Figure 5.

## 4. Feature Investigation: Roof vs. Pad

Crisp rectangular features present in **both** the vendor and project ground
surfaces, in the western residential block, were investigated to determine
whether they were unremoved roof returns or real graded ground features.

Sampled DEM elevation at a structure's interior center vs. open ground ~45 ft
away: **+2.85 ft** difference. A roof would present an 8–15 ft plateau with a
sharp vertical wall; 2.85 ft is consistent with a graded, built-up
foundation pad, not roof height.

Cross-checked against current orthoimagery (Esri World Imagery, fetched
directly for these coordinates — 32.096637°N, 111.011371°W): a roofed
residential structure now occupies essentially the same footprint. This
does not contradict the pad interpretation; it corroborates it. The Feb
2015 acquisition measured a graded, sub-roof-height platform, not an
existing building — a house built on that same pad sometime in the
intervening decade is exactly what the 2015 measurement would predict.
Present-day imagery cannot directly confirm ground conditions at
acquisition time (see §7), so this is corroborating, not primary,
evidence; the elevation-plateau argument above remains the direct
evidence from the dataset itself.

Widening the SMRF `window` from 60 to 240 ft did not remove these features.
Cause: the pad footprints (~70–100 ft across) approach the SMRF window size
being tested, so the morphological-opening surface model is pulled upward
within the window and treats the pad top as terrain — a known SMRF
limitation at this scale, not a pipeline defect.

## 5. Hydrologic Derivatives (Beyond Original Scope)

As an extension beyond the original nine-item QC plan, the bare-earth DEM was
carried through a full hydrologic-conditioning and stream/watershed workflow
using WhiteboxTools (neither QGIS nor GRASS was actually available in this
environment, correcting an earlier assumption).

### 5.1 Depression handling

`BreachDepressionsLeastCost` was run first (minimal terrain modification),
then `FillDepressions` on whatever remained. All 101,466 detected pits were
resolved by the breach step alone — fill was genuinely a backstop, not the
primary correction. Impact was quantified by direct DEM differencing (not a
tool summary line), so it is independently verifiable:

| Step | Cells changed | % of tile | Volume (cu ft) | Max raise | Max cut |
|---|---|---|---|---|---|
| Breach only | 170,297 | 6.13% | −116,457 (net cut) | +1.39 ft | −15.31 ft |
| Residual fill | 53,815 | 1.94% | +179,471 (net fill) | +9.27 ft | 0.00 ft |
| Total | 213,602 | 7.69% | +63,065 (net fill) | +9.31 ft | −15.31 ft |

Re-classified by region — natural terrain west of the main wash, engineered
ag surfaces east, and cells within 150 ft of any tile edge — using a
|change| > 0.05 ft threshold:

| Region | Changed cells | % of all changed | Volume (cu ft) |
|---|---|---|---|
| Natural terrain, west (not edge-adjacent) | 23,663 | 22.3% | −24,002 (net cut) |
| Ag area, east (not edge-adjacent) | 64,678 | 61.0% | −29,351 (net cut) |
| Tile-boundary-adjacent (either side) | 17,771 | 16.7% | +115,726 (net fill) |

Real terrain, on both sides of the wash, is breach-dominated — a net cut,
consistent with removing small pits rather than building up ground. Nearly
all net *fill* volume instead concentrates within 150 ft of the tile edge,
the same zone flagged in §7 for SMRF edge effects — both the ground
classifier and the flow-routing algorithm lose neighborhood context at the
same boundary. Most of what `FillDepressions` is correcting there is edge
truncation artifact, not real terrain (Figure 6).

### 5.2 Flow routing and stream network

D8 flow direction and accumulation were computed on the conditioned DEM. A
stream-extraction threshold was derived empirically via slope-area analysis
— no clean break point was found in the data, a genuine negative result
rather than a tuning failure — and cross-checked visually. The center-pivot
irrigation field's circular wheel-track ring turned out to be geometrically
indistinguishable from a real drainage channel to D8 routing at any
threshold tested (Figure 7): tightening the threshold enough to erase the ring
also erases real tributaries elsewhere in the tile, and no single number
satisfies both. Rather than threshold-tune the artifact away, the delivered
network (threshold = 5,000 cells / 1.03 ac) flags ag-area segments
explicitly as "do not interpret as real drainage" (orange, Figure 8), separate
from natural-terrain segments trusted as real (red).

Final network: 323 vectorized segments, 108,068 ft (~20.5 mi) total length —
`output/hydrology/streams_final_t5000.gpkg`.

### 5.3 Watershed delineation

The main wash's watershed was delineated from a pour point at the tile's
north edge: **258.4 acres** within this tile. A boundary-crossing scan
(checking every high-accumulation cell against all four tile edges)
confirmed the system is through-flowing — it enters at the south edge (a
minor 3.9-acre tributary) and exits at the north (the 258-acre main wash).
The delineated watershed is therefore stated directly on the deliverable
figure as a **lower bound** on the true catchment, not the complete
drainage area (Figure 8) — the same tile-isolation caveat as §7's edge-effects
limitation, applied to a drainage area instead of a ground surface.

## 6. Deliverables

| File | Description |
|---|---|
| `output/dem/dem_w120_s0.15_t1.6.tif` | Bare-earth DEM, 3 ft, IDW |
| `output/hillshade/hs_w120_s0.15_t1.6.tif` | Hillshade |
| `output/dem/dsm.tif` | Digital surface model (first surface, all non-noise returns) |
| `output/dem/chm.tif` | Canopy/structure height model (DSM − DEM) |
| `output/contours/contours_2ft_w120_s0.15_t1.6.gpkg` | 2 ft contours |
| `output/dem/diff_VENDOR_minus_w120_s0.15_t1.6.tif` | Vendor comparison raster |
| `output/dem/density_count_3ft_aligned.tif` | Per-cell point density |
| `output/reports/batch_qc.csv` | Per-tile QC log (point counts, ground %, density, void %, runtime) |
| `output/hydrology/streams_final_t5000.gpkg` | Derived stream network, ag-area segments flagged (§5.2) |
| `output/hydrology/watershed_main_wash.gpkg` | Main wash watershed, 258.4 ac lower bound (§5.3) |

## 7. Limitations & Recommendations

- **Vertical datum: confirmed, not presumed.** NAVD88 via Geoid12A,
  sourced from the project's own accuracy assessment (Psomas, Feb 2015)
  and the acquisition vendor's report of survey (Sanborn, Aug 2015) — not
  from the delivered LAZ's own header, which declares no vertical CRS.
  Sensor was a Leica ALS70 HP, flown Feb 20–26, 2015. Project NVA:
  RMSEz = 10.3 cm (raw LAS) / 8.8 cm (bare-earth DEM), against a QL2
  target of ≤10 cm — the raw-LAS figure marginally exceeds the 10 cm
  target; the assessment does not comment on this. VVA was not
  assessed by the vendor (project area classified entirely non-vegetated
  for accuracy-testing purposes). Full source citation, including why it's
  treated as authoritative, in §9.
- **No external vertical control falls inside this specific tile** (§3.4)
  — the project's 134 check points are spread across the full ~2,203 sq
  mi collection area and none happen to land in this 574-acre tile. The
  project-wide NVA above is real and sourced, but an in-tile check would
  require new fieldwork.
- **The orthoimagery cross-check in §4 uses present-day imagery, not
  imagery contemporaneous with the Feb 2015 acquisition.** It shows a
  roofed structure now standing on the footprint identified as a graded
  pad in the LiDAR — consistent with construction sometime in the
  intervening decade, not a contradiction of the elevation-based
  finding, but not a same-epoch verification either.
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
- **The derived stream network cannot separate a real channel from the
  center-pivot field's wheel-track ring by geometry alone** (§5.2). This is
  disclosed on the deliverable figure itself (ag-area segments flagged
  orange) rather than resolved by threshold-tuning, since no threshold
  clears the artifact without also losing real tributaries.
- **The delineated watershed (258.4 ac) is a lower bound**, not the true
  catchment (§5.3) — the same tile-isolation constraint as the SMRF
  edge-effects limitation above, applied to flow routing instead of ground
  classification.

## 8. Batch processing (multi-tile)

A second tile (Tucson Mountains, steeper vegetated terrain) was also run
through this pipeline with its own tuned SMRF parameters; its results
are documented separately, not in this single-tile memo.

## 9. Sources (project documentation, external to this analysis)

The vertical datum, sensor, acquisition dates, and project NVA cited
throughout this memo (§3.4, §7) are not derived from this project's own
processing — they come from the original 2015 collection's project
documentation, located on USGS's public distribution server in a path
separate from the LAZ tile downloads themselves
(`Elevation/metadata/Eastern_Pima_County_Lidar/AZ_Eastern-PimaCO_2015/reports/`).
The per-tile XML metadata shipped alongside the LAZ file is a thin,
auto-generated stub with no real content (vertical accuracy listed as
"N/A," process steps "unknown") and was not relied on for any of this.

- **"2015 PAG LiDAR Data Absolute Vertical Accuracy Assessment,"**
  Psomas, Project No. 7PIM130303, February 9, 2015. **Signed and sealed**
  by Patrick McGarrity, AZ RLS #49459, ASPRS Certified Photogrammetrist
  #R1245. Source of: vertical datum (NAVD88/Geoid12A), horizontal datum
  and units, and the project NVA figures (RMSEz 10.3 cm raw LAS / 8.8 cm
  DEM, 134 ASPRS-compliant check points).
- **"LiDAR Campaign for the PAG Tucson, Report of Survey,"** Sanborn Map
  Co. (the acquisition contractor), August 2015. Source of: sensor model
  (Leica ALS70 HP), aircraft, flight mission dates and count, and an
  independent confirmation of the datum/units above.

A signed and sealed professional survey document is a stronger citation
than unsigned metadata or a generic project webpage — it carries the
preparer's professional license and legal responsibility for the stated
facts, which is precisely the standard this deliverable's own accuracy
claims should be held to. That is why these two documents, not the
tile's own header, are cited as the authoritative source for the datum
and NVA claims in this memo.
