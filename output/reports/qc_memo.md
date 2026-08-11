# LiDAR Bare-Earth DEM — Quality Control Memorandum

**Tile:** USGS_LPC_Eastern_Pima_County_Lidar_980398.laz
**Location:** San Xavier District, Tohono O'odham Nation, Pima County, AZ
**Horizontal datum/CRS:** NAD83(2011) / Arizona Central, International Feet (EPSG:6405)
**Vertical datum:** NAVD88, Geoid12A — confirmed against project documentation (Psomas
2015 Vertical Accuracy Assessment; Sanborn Report of Survey, Aug 2015). Not declared in
the delivered LAZ header itself, but sourced independently from both the accuracy
assessment and the acquisition vendor's own report. See §8.
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
*project's own* authoritative NVA is now available (see header and §8) —
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
(EPSG:6405), western residential block. Measured within a **20 ft
circular radius** of that cell, against the delivered bare-earth DEM as
the ground reference (both stated because the result depends on them):
**11 returns** exceed 10 ft above ground — vs. hundreds across a
footprint for an actual building, per §4 — spanning just **3.7 ft in
easting but 16.8 ft in northing**, and **10 of the 11 are the first
return of a multi-return pulse**, with every pulse involved having
exactly 2 or 3 returns. That is a laser mostly passing through a thin,
open structure and registering ground behind it. **Conclusion: a utility
pole or small transmission/communications tower**, not sensor noise or a
bird strike (which would show as a single isolated point, not a narrow
coherent cluster) and not a building or vegetation (both ruled out by
height and by point density). Real feature, correctly retained.
Re-derive with `python scripts/measure_features.py`. See Figure 5.

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
acquisition time (see §8), so this is corroborating, not primary,
evidence; the elevation-plateau argument above remains the direct
evidence from the dataset itself.

Four SMRF `window` values were tested — 60, 120, 180, and 240 ft — but
they produced only **two distinct results**, not four: `dem_w60_t16.tif`
differs from the other three, while `dem_w120_s0.15_t1.6.tif`,
`dem_w180_s0.15_t1.6.tif`, and `dem_w240_s0.15_t1.6.tif` are
byte-identical to each other (checksum-verified). That convergence is
itself the more useful result.

`window` is a linear-unit distance, converted internally to a pixel
radius via `ceil(window / cell)` (PDAL 2.10.0, `filters/SMRFilter.cpp`).
At this run's cell size (3.3 ft), the four tested windows map to radii
19, 37, 55, and 73 px. SMRF progressively opens the surface from radius
1 up to that maximum, flagging non-ground cells against a threshold that
grows with radius too — so once the structuring element exceeds the
largest real non-ground feature actually present in the data, further
radius growth stops changing the classification. The observed
convergence therefore falls somewhere between 60 ft (radius 19) and
120 ft (radius 37).

*Footprint measurement (method stated so the comparison is checkable):*
the raised built surface was measured by radial profiles from the sample
point at 15° increments, with the edge along each bearing taken as the
first cell lying more than **half the measured 2.85 ft pad step** below
the pad-top elevation — half the step being the physically motivated
cut, since a point that far below the pad top is unambiguously off the
built surface rather than on its graded crown or shoulder.
Connected-component labelling was tried first and rejected: at any
threshold low
enough to reach the pad edge, the pad is contiguous with the driveway
and loop-road embankment, so the labelled region runs away into the road
network. Radial profiles avoid this, since each bearing is measured
independently. Result: 23 of 24 bearings close within 150 ft, at edge
radii of 15–63 ft (median 48), giving a characteristic width of **96 ft**
and closed-axis spans of **66–114 ft**. The single open bearing is due
west, where the pad merges with the driveway. Re-derive with
`python scripts/measure_features.py`.

The convergence between 60 and 120 ft thus brackets the measured
footprint scale (66–114 ft): once the structuring element reaches
roughly the size of the pad, the algorithm has already "seen" the whole
feature and widening further adds nothing. That the convergence point
and the independently measured footprint agree is a stronger piece of
evidence for the pad interpretation than a bare "widening didn't help" —
though the agreement is a bracket, not a coincidence to be read too
precisely.

*(No pipeline JSON was retained for the `w60` run — it predates this
project's audit-trail convention of saving one per run, see §2 — so its
parameters beyond `window=60` aren't independently verifiable from a
saved artifact, only from this record.)*

## 5. Hydrologic Derivatives (Beyond Original Scope)

As an extension beyond the original nine-item QC plan, the bare-earth DEM was
carried through a full hydrologic-conditioning and stream/watershed workflow
using WhiteboxTools (neither QGIS nor GRASS was actually available in this
environment, correcting an earlier assumption).

### 5.1 Depression handling

`BreachDepressionsLeastCost` was run first (minimal terrain modification),
then `FillDepressions` on whatever remained. The breach step alone
resolved every depression it detected, leaving nothing for fill to
resolve as a pit — fill was genuinely a backstop, not the primary
correction. *(WhiteboxTools reported 101,466 detected pits in that run's
console output; that log was not retained, so the figure is quoted here
as tool output rather than as a measurement re-derivable from the saved
rasters. The impact volumes below are independently verifiable and do
not depend on it.)* Impact was quantified by direct DEM differencing,
not a tool summary line:

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
the same zone flagged in §8 for SMRF edge effects — both the ground
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
drainage area (Figure 8) — the same tile-isolation caveat as §8's edge-effects
limitation, applied to a drainage area instead of a ground surface.

## 6. Tile-Boundary Buffering (Multi-Tile)

SMRF classifies each tile in isolation, so points near a tile edge have no
neighbourhood context — whatever lies just beyond the boundary is not in
that pipeline run at all. Two independently classified tiles therefore
disagree where they meet. This section measures that disagreement and
what buffering does to it.

### 6.1 Method

The four tiles edge-sharing with 980398 were obtained and processed with
**parameters identical to the centre tile** — a requirement, not a
convenience, since any seam step must be attributable to missing
cross-tile context rather than to a parameter difference between
adjacent runs.

Adjacent tiles abut rather than overlap, so there is no shared area to
difference. The discontinuity is measured as the **elevation step across
the boundary**: each tile is sampled 1.5 ft inside its own edge, so the
two samples lie 3 ft apart and straddle the seam, along the full 5,000 ft
at 3 ft spacing. Because real terrain also changes over 3 ft, every seam
is compared against **pseudo-seams inside the centre tile** — the same
3 ft straddle with no boundary involved — which measure natural terrain
roughness.

That baseline is computed **per side**. Pooled across the tile it is
misleading: the eastern half is flat irrigated agriculture and the west
has hills, and against a tile-averaged baseline the E seam appeared to
show no artifact at all (0.99×) when against terrain adjacent and
parallel to it the figure is 1.60×. Re-derive with
`python scripts/measure_seams.py --tag <variant>`.

Buffering itself (`scripts/batch_process.py --buffer-ft 150`) reads a
margin 150 ft into every adjacent tile and classifies with the margin
included. 150 ft was chosen to exceed SMRF's own reach,
`ceil(window/cell)` = 37 cells ≈ 122 ft at this tile's parameters.

**The buffer is removed as a raster operation, not a point crop, and the
distinction matters.** The DEM is rasterized over a grid deliberately
extended by the buffer, then clipped back to the tile with
`gdal_translate -srcwin`. Cropping the *points* to the tile before
rasterizing — the obvious implementation — fixes the classification edge
effect but leaves an interpolation one: IDW's fallback search reaches
`window_size` × resolution = 18 ft, so cells within 18 ft of the boundary
would still be interpolated from a one-sided neighbourhood, and that is
precisely the zone where seam discontinuity is measured (samples sit
1.5 ft either side). Clipping the raster instead means every output cell,
edge cells included, is interpolated from a complete neighbourhood. The
buffer distance is required to be a whole number of cells so the clip is
an integer window; the clipped raster is bit-identical in grid, bounds
and CRS to the unbuffered one, so before/after differences cannot be a
gridding artifact.

### 6.2 Result

| Seam | Unbuffered RMS | Buffered RMS | Change | Local natural step | Ratio before → after |
|---|---|---|---|---|---|
| N | 0.608 ft | 0.237 ft | **−61.0%** | 0.225 ft | 2.71× → 1.06× |
| S | 0.642 ft | 0.289 ft | **−55.0%** | 0.199 ft | 3.23× → 1.45× |
| E | 0.219 ft | 0.119 ft | **−45.7%** | 0.137 ft | 1.61× → 0.87× |
| W | 0.411 ft | 0.213 ft | **−48.1%** | 0.293 ft | 1.40× → 0.73× |

Buffering reduces seam discontinuity by **46–61%**, and the improvement
is broadly uniform across all four seams rather than depending on seam
orientation relative to the flight lines. Systematic offsets fall on
every seam as well: N −98%, S −77%, E −68%, W −45%, leaving residuals of
−0.001 to +0.024 ft on three seams and −0.034 ft on the fourth.

**Three of the four seams fall to at or below the natural terrain step
measured beside them** (N 1.06×, E 0.87×, W 0.73×). A ratio below 1.0
should not be read as accuracy exceeding real terrain. It is the expected
signature of the two sides no longer being independent: with a buffer,
the cells either side of a boundary are interpolated from overlapping
point neighbourhoods, so they are correlated in a way that two
independent samples 3 ft apart in open terrain are not. The comparison
baseline is deliberately built from independent terrain samples, so once
the seam stops being a discontinuity at all, the ratio falling under 1.0
is what the metric does — not evidence of a better-than-reality surface.

**The S seam is the exception**, remaining at 1.45× with a small but
statistically significant systematic offset (+0.024 ft, t = +3.4). It is
the only seam where a residual discontinuity survives buffering, and this
memo does not claim a cause for it. Candidates include flight-line
calibration (§3.3 measured a +0.124 ft inter-swath offset in this
collection, an order consistent with the residual) and genuine terrain at
that boundary, but nothing here distinguishes them.

Deliverables carry the `_buf150` tag; the unbuffered baseline is retained
alongside them so the comparison stays checkable (Figure 9, Figure 10).

## 7. Deliverables

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

## 8. Limitations & Recommendations

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
  treated as authoritative, in §10.
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
- **One seam retains a residual discontinuity after buffering** (§6.2).
  Three of four fall to at or below the natural terrain step beside them,
  but the S seam remains at 1.45× with a small significant systematic
  offset (+0.024 ft). No cause is claimed; flight-line calibration (§3.3)
  and genuine terrain are both consistent with it and this work does not
  distinguish them.
- **The buffer distance has not been optimised.** 150 ft was chosen to
  exceed SMRF's ~122 ft reach at these parameters. Whether a larger
  buffer further reduces the S residual is untested.
- **Buffered results depend on the buffer being removed as a raster
  clip rather than a point crop** (§6.1). Cropping points before
  rasterizing leaves IDW interpolating edge cells from a one-sided
  neighbourhood, within 18 ft of the boundary — the zone the seam metric
  samples. Any reimplementation must preserve that ordering or the
  measured improvement will be substantially understated.
- **The derived stream network cannot separate a real channel from the
  center-pivot field's wheel-track ring by geometry alone** (§5.2). This is
  disclosed on the deliverable figure itself (ag-area segments flagged
  orange) rather than resolved by threshold-tuning, since no threshold
  clears the artifact without also losing real tributaries.
- **The delineated watershed (258.4 ac) is a lower bound**, not the true
  catchment (§5.3) — the same tile-isolation constraint as the SMRF
  edge-effects limitation above, applied to flow routing instead of ground
  classification.

## 9. Batch processing (multi-tile)

A second tile (Tucson Mountains, steeper vegetated terrain) was also run
through this pipeline with its own tuned SMRF parameters; its results
are documented separately, not in this single-tile memo.

## 10. Sources (project documentation, external to this analysis)

The vertical datum, sensor, acquisition dates, and project NVA cited
throughout this memo (§3.4, §8) are not derived from this project's own
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
