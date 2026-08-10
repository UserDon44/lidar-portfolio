# LiDAR Processing Portfolio — Eastern Pima County, AZ

**Standalone project summary.** This document assumes no prior context. If
every other file in this repository were lost, this is the one that should
survive and still explain what the project is, what was done, what was
found, and what its limits are. (For live technical detail — exact
parameters, file paths, script behavior — see `CLAUDE.md`, which is
maintained as the project's working memory. For a dated chronological
account of individual work sessions, see `session-log.md`.)

---

## 1. What this project is

A portfolio piece built to demonstrate professional-grade LiDAR processing
skills to survey and geospatial engineering firms in the Southwest US
(the kind of firms named as targets during this project: Cooper Aerial,
NV5, Woolpert, and similar). The deliverable is a defensible bare-earth
Digital Elevation Model (DEM) produced from raw, unclassified LiDAR
returns — not a tutorial exercise, and not simply accepting a vendor's
delivered classification at face value. The work includes independent
ground classification, multiple independent accuracy checks (against the
vendor's own classification, against internal repeatability, against
flight-line consistency, and against the collection's own official
accuracy report), a written QC memorandum in the style a real firm would
produce for a client, a second tile processed under deliberately harder
terrain conditions to demonstrate parameter adaptation, a batch-processing
tool for scaling to many tiles, and a full hydrologic analysis (drainage
network and watershed delineation) derived from the finished DEM.

The person directing this work is new to the terminal and to Python;
all processing was done through an AI assistant (Claude Code) that wrote
and ran the actual scripts, with the person reviewing visual outputs
(hillshades, overlays) and making judgment calls the assistant flagged
for human review — matching how a junior processor would actually work
under a supervising licensed surveyor in a real firm.

## 2. The data

Two LiDAR tiles were processed, from two different USGS 3DEP collections,
chosen specifically to contrast flat/sparse-vegetation desert against
steep/vegetated mountain terrain.

### 2.1 Primary tile: San Xavier, Eastern Pima County (2015)

- **File**: `USGS_LPC_Eastern_Pima_County_Lidar_980398.laz`
- **Size**: 8,692,808 points, 33 MB compressed, LAS 1.4 point format 6
- **Extent**: 5,000 × 5,000 ft (X 980112.76–985112.75, Y 398427.81–403427.80),
  ≈574 acres
- **Elevation range**: 2,490.75–2,654.69 ft (164 ft relief)
- **Point density**: ~3.7 points/m² average (QL2 — USGS Quality Level 2)
- **Location**: San Xavier district, Tohono O'odham Nation, immediately
  south of Tucson, Arizona. Mixed land use: irrigated agriculture (east),
  low residential development and two small hills (west), an ephemeral
  wash running roughly north–south through the tile center, and one
  center-pivot irrigation field (laser-leveled, ~540 ft radius).
- **Coordinate system**: NAD83(2011) / Arizona Central, EPSG:6405.
  Horizontal units are **International Feet** (1 ft = 0.3048 m exactly,
  EPSG:9002) — **not** US survey feet (1 ft = 0.3048006096 m, EPSG:9003).
  This distinction is numerically tiny (~2 parts per million, ~0.06 ft
  over this tile) but was confirmed explicitly, verbatim, in the
  collection's own project documentation, and stating it correctly
  matters to the surveyor audience this deliverable targets.
- **Vertical datum**: **NAVD88**, orthometric heights derived via the
  **Geoid12A** model. This is *not* declared in the delivered LAS file's
  own header (`"vertical": ""` — blank) — it was independently confirmed
  from two signed, primary-source project documents, described in
  section 3 below.
- **Sensor and acquisition**: Leica ALS70 HP airborne laser scanner, flown
  from a Sanborn Map Co. twin-engine Aero-Commander 500-B, **February
  20–26, 2015** (14 flight missions in about one week). The LAS file's
  own internal creation date reads day 307 of 2015 (November 3) — that is
  when USGS/Sanborn finalized and repackaged the tile for delivery,
  months after the actual flights, not a second acquisition.
- **Vendor classification**: present but ground-only (classes 1–7; no
  separate vegetation or building classes). Class 2 (ground) is
  approximately 70% of all points. Average `NumberOfReturns` is 1.023 —
  i.e., almost every laser pulse produced only one return, meaning
  vegetation here is extremely sparse with essentially no canopy.

### 2.2 Second tile: Tucson Mountains (Wasson Peak vicinity, 2021)

Chosen deliberately to test the processing pipeline against terrain the
first tile could not: real slope and real vegetation canopy.

- **Original file**: `USGS_LPC_AZ_PimaCounty_2021_B21_484572.laz`,
  87.9 MB, from the 2021 Pima County 3DEP collection (project
  `AZ_PimaCounty_2021_B21`).
- **Original CRS**: NAD83(2011) / UTM Zone 12N (EPSG:6341) horizontal +
  NAVD88 height–Geoid18 (EPSG:5703) vertical, **entirely in meters** —
  a different projection and different units than the primary tile.
  Reprojected to this project's standard EPSG:6405 (International Feet)
  and saved as `tucson_mtns_484572_epsg6405.laz`. The reprojection step
  itself surfaced a real, easy-to-miss bug: because the target CRS has no
  vertical component, PDAL's `filters.reprojection` correctly converted
  X/Y to feet but silently left Z unconverted in meters — caught by
  checking the output header's magnitude against what was physically
  expected, not by assuming the reprojection worked. Fixed with an
  explicit vertical scale transform (factor 3.280839895, the
  International Feet conversion, not 3.280833333 which would be the US
  survey foot conversion).
- **Extent after reprojection**: 3,309 × 3,310 ft (~251 acres)
- **Point count**: 27,722,077 (~27.7 points/m² — QL1-class, roughly 7.5x
  denser than the primary tile's QL2 density)
- **Elevation range**: 2,727.4–3,055.8 ft after excluding sensor noise
  points (the raw header showed an implausible 5,144 ft of "relief,"
  traced to a single high-noise-classified point) — **328.4 ft of real
  relief** over a much smaller area than the primary tile, i.e.
  meaningfully steeper per unit area, exactly as intended.
- **Vegetation**: 35.16% of points are multi-return (mean
  `NumberOfReturns` 1.4137), vs. the primary tile's 1.023 — real canopy
  penetration from cacti (saguaro, cholla), palo verde, and ironwood,
  not the near-absent vegetation of the first tile.
- **Vertical datum**: NAVD88/Geoid18, explicitly declared in this tile's
  own header (unlike the primary tile) — indirect supporting evidence
  for the primary tile's now-independently-confirmed NAVD88/Geoid12A.

## 3. How the ground classification was done

Both tiles were classified from scratch from raw returns — the vendor's
delivered classification was used only as a comparison baseline, never as
an input to this project's own DEM.

**Pipeline** (PDAL): strip existing classification → ELM (extended local
minimum, removes low-elevation noise) → statistical outlier removal →
SMRF (Simple Morphological Filter, the actual ground/non-ground
classifier) → keep ground-classified points only → rasterize via inverse-
distance weighting (IDW) → generate a hillshade for visual QC.

**Primary tile parameters** (flat desert, sparse vegetation): SMRF window
120 ft, slope tolerance 0.15 (15%), threshold 1.6 ft, scalar 1.25, cell
3.3 ft; output raster 3 ft resolution. These were tuned once (a first
pass at window 60 ft, then doubled to 120 ft with near-identical results)
and used for all subsequent QC analysis.

**Second tile parameters** (steep, vegetated): derived through five
iterations, described in full in section 6 below, arriving at window
33 ft, slope 0.6 (60%), threshold 1.3 ft, scalar 0.75, cell 1.6 ft, plus
a last/single-return-only pre-filter — a substantially different
parameter set, each change independently justified by measured
properties of that terrain, not copied from the first tile.

## 4. Primary-tile findings, with numbers

### 4.1 Roof vs. pad (were the residential rectangles unremoved roofs?)

Crisp rectangular features appeared in the western residential block, in
**both** the vendor's classification and this project's own — meaning
they were either real ground features or a shared blind spot. Sampled DEM
elevation at one structure's interior center (980339.26, 400067.31 ft:
2,548.050 ft) against adjacent open yard ~45 ft away (980357.26,
400019.31 ft: 2,545.204 ft) — a difference of **+2.85 ft**. A genuine
unremoved roof would show 8–15 ft of relief with a sharp vertical wall;
2.85 ft is consistent with a graded, built-up foundation pad, not roof
height. **Confirmed directly by the project owner against ground truth:
these are concrete pads leading to driveways and the road.** Widening the
SMRF window from 60 to 240 ft did not remove the feature, because the pad
footprint (~70–100 ft across) is comparable to the window sizes tested —
a known SMRF limitation (the morphological-opening surface model gets
pulled upward within a window comparable to the feature's own size), not
a pipeline defect.

### 4.2 Agreement with the vendor's own classification

After fixing a grid-alignment bug (PDAL's `writers.gdal` computes each
run's raster extent from that run's own point-cloud bounding box, so two
runs with slightly different point populations rounded to different pixel
grids — 1667×1667 vs. 1668×1668 — and wouldn't difference directly; fixed
by forcing both onto one fixed grid via `gdalwarp` before comparison),
this project's DEM was differenced against the vendor's delivered
ground surface:

- Valid compared cells: 2,777,225 of 2,778,889 (99.9%)
- **RMSE: 0.162 ft** — comfortably inside the ASPRS QL2 non-vegetated
  accuracy standard (RMSEz ≤ 0.328 ft / 10 cm)
- Mean −0.047 ft, median −0.014 ft, standard deviation 0.155 ft
- Only 0.23% of cells disagree by more than 1 ft, and those cluster not
  in the residential area (as initially expected) but along the wash
  channel and at one road/wash crossing — both sides show the same
  culvert feature, just disagreeing by about a foot on its exact edge,
  an interpolation artifact at a sharp linear break rather than a
  genuine classification error.

### 4.3 Internal precision (repeatability floor)

Using the laser-leveled center-pivot field as a known-flat reference
(chosen because it is genuinely engineered flat, not because it was
assumed to be — this avoided needing external imagery, which could not
be loaded in-session): sampled raw ground-classified points directly
(not the smoothed DEM raster, which would mask real point noise) in a
100×100 ft box, fit and removed the field's own real 0.50% design
drainage grade, and examined the residual scatter.

- 2,123 ground points in the sample box
- **Residual RMSE: 0.104 ft** (~1.25 inches) — the internal precision
  floor of this dataset, tighter than the 0.162 ft vendor-comparison
  RMSE, exactly as expected (two independent classifications disagreeing
  with each other should exceed either one's own internal noise)
- The residual spatial pattern showed diagonal banding rather than pure
  random noise — this turned out to be real, and is explained in the
  next finding.

### 4.4 Flight-line (swath) consistency

The point cloud was split by its `PointSourceId` attribute, revealing 4
distinct flight lines, two of which dominate: line 519 (4,129,283 points,
covering the eastern ~70% of the tile) and line 600 (3,679,198 points,
covering the western ~70%), overlapping in a shared 1,848 ft-wide band.
Each line's ground surface was rebuilt independently with identical
parameters and differenced within that shared overlap:

- 972,708 valid overlap cells (94.7% coverage)
- **Mean offset: +0.124 ft** (line 600 higher than line 519), median
  +0.120 ft, RMSE 0.222 ft
- This is a **systematic, one-directional bias**, not noise — visible as
  a near-uniform tint across nearly the entire overlap band. It is
  consistent with a mild vertical calibration/boresight discrepancy
  between flight lines **in the original data collection itself**, not
  an artifact of this project's own processing.
- This directly explains the diagonal banding found in section 4.3: that
  sample box sits right at the edge of this same overlap zone, so the
  finished DEM's per-cell blend of both flight lines produces exactly
  that banding pattern.

### 4.5 External vertical control

Queried NGS's published survey monument database for the tile's exact
footprint: **zero monuments fall inside the tile.** The search was
widened and the four nearest candidate monuments were individually
checked against their full official datasheets — every one was
independently disqualified for a different reason: two have no published
elevation at all (horizontal position only); one is recorded as
physically not found in the field since 2009, with only a scaled
(imprecise) position on record; and the closest one in good, recently
re-confirmed condition is about 0.45 miles outside the tile with its
published height derived by datum-conversion software (VERTCON3) rather
than direct survey observation. **Conclusion: no usable external vertical
control exists in or near this tile**, and a true external accuracy
check would require new fieldwork (e.g., commissioning a static GPS
occupation). This is stated as a scope limitation, not a data quality
failure — and it made the discovery described in section 5 below (the
collection's own official accuracy report) especially valuable, since it
supplied exactly the external, authoritative accuracy figure that
couldn't be produced from monuments alone.

### 4.6 Point density and coverage voids

A true non-overlapping per-cell density raster was built from first
returns only (catching and fixing a real bug along the way: PDAL's
default counting method uses a radius-based search around each cell,
inflating the first attempt's density by roughly 6x — 23.2 pts/m² vs. the
tile's documented ~3.7 pts/m², which was the tell; fixed with PDAL's
`binmode: true` option for true non-overlapping histogram binning).

- Mean density 3.697 pts/m² — matches the documented tile-wide average
- Median density only 2.392 pts/m² (mean and median diverging is itself
  informative — the distribution is uneven)
- **2.33% of the tile has zero returns** (true coverage voids)
- **19.4% of the tile falls locally below the QL2 minimum density**
  (2 pts/m²) once voids are included — despite the tile-wide average
  comfortably clearing that same minimum. This is exactly why a
  per-cell check matters over a single tile-wide average: nearly 1 cell
  in 5 would fail a local density requirement that the average alone
  would hide.
- Spatially, this lines up precisely with the flight-line geometry from
  section 4.4: the overlap band between lines 519 and 600 is
  higher-density and nearly void-free, while the single-coverage strips
  on either side run at or below the QL2 floor. The voids themselves
  follow the scanner's oscillating scan-line pattern (gaps between
  individual sweeps, healed wherever a second flight line overlaps), not
  the wash or any other terrain feature — a water-related dropout
  pattern was specifically checked for and ruled out.

### 4.7 Contours, DSM, and CHM

Two-foot contours were generated (12,258 features spanning 2,492–2,650
ft) and visually checked against the hillshade — hills, the wash, and the
pivot field's grade all track cleanly; dense contour clutter visible in
the northeast and southeast agricultural fields is real 2 ft-scale
micro-terrain (crop rows) at this fine an interval, not a defect.

A Digital Surface Model (DSM, the height of the first solid surface
including vegetation and structures) and Canopy/structure Height Model
(CHM = DSM − DEM) were built. CHM statistics: mean 0.92 ft, median
0.09 ft (matching the tile's documented near-absent canopy), standard
deviation 3.20 ft, range −8.36 to +72.87 ft. Visual inspection confirmed
dark rectangular CHM outlines line up exactly with the residential
building footprints that show as voids in the ground-only hillshade —
confirming those really are roofs, distinct from the graded pad
investigated in section 4.1. A strong CHM line follows the wash
(riparian vegetation), and the agricultural fields show almost nothing.

The CHM's maximum value (72.87 ft) was specifically investigated rather
than left as an unexplained outlier: its raw returns, at (981146.26,
400792.30 ft), form a small coherent cluster of only 13 points (not
hundreds, as an actual building roof would produce), narrow in one
direction (~3 ft) but spread over ~17 ft in the other, and nearly all
are the first return of a 2-3-return pulse — the signature of a laser
mostly passing *through* a thin, open structure and also registering the
ground behind it. **Conclusion: a utility pole or small
transmission/communications tower**, correctly retained as a real
feature, not sensor noise and not a building.

### 4.8 Official project accuracy report (external, authoritative)

The tile's real project documentation — not the thin, largely
content-free XML metadata stub that ships alongside the LAZ file itself,
but a full separate report package — was located on USGS's public
distribution server, in a metadata/reports path parallel to (but distinct
from) the actual tile-download path. Two independent, signed documents
were found and read directly:

- *"2015 PAG LiDAR Data Absolute Vertical Accuracy Assessment"* — Psomas,
  Project No. 7PIM130303, February 9, 2015, **signed and sealed** by
  Patrick McGarrity, Arizona Registered Land Surveyor #49459.
- *"LiDAR Campaign for the PAG Tucson, Report of Survey"* — Sanborn Map
  Co. (the acquisition contractor), August 2015.

These independently confirm each other on every overlapping fact (datum,
units, sensor, dates — see section 2.1) and additionally supply the
collection's own official accuracy figures, based on 134 ASPRS-compliant
check points (all in non-vegetated terrain, per that standard's
methodology):

- **NVA, raw LAS: RMSEz = 10.3 cm** (±20.2 cm at 95% confidence) —
  marginally over the project's own ≤10 cm QL2 target, not flagged as a
  failure by the certifying surveyor
- **NVA, bare-earth DEM: RMSEz = 8.8 cm** (±17.2 cm at 95% confidence) —
  clears the QL2 target
- Vegetated Vertical Accuracy (VVA) was **not assessed** by the original
  project — its check points were deliberately all placed in
  non-vegetated, open terrain
- A signed, sealed professional survey document is treated in this
  project as a stronger citation than unsigned metadata, precisely
  because it carries the preparer's professional license and legal
  responsibility for the stated facts — the same standard this
  project's own deliverable should be held to.

## 5. Second tile: adapting the pipeline to steep, vegetated terrain

The point of processing a second tile was not to produce a second DEM for
its own sake, but to demonstrate that the pipeline's parameters are the
product of measurement and judgment, not a fixed recipe. Full detail is
in `CLAUDE.md`; the essential story:

Terrain slope was **measured directly** from a probe DEM built off the
vendor's own ground points (median 28% grade, 90th percentile 91.5%, far
exceeding anything in the flat primary tile) rather than guessed. Five
parameter iterations followed:

1. A first attempt (window 33 ft, slope 1.0, threshold 3.3 ft) produced
   plausible ridge/gully structure but a dense fine speckle the project
   owner identified as vegetation.
2. Tightening the threshold alone produced **no visible change** — a
   useful negative result that ruled threshold out as the controlling
   parameter.
3. Backing slope off toward the measured median, plus a slower scalar,
   **also produced no visible change** — both threshold and slope ruled
   out as the controlling lever, with window held constant across all
   three attempts.
4. A widened-window attempt was originally believed to show a real,
   subtle tradeoff (per-cell change up to 8.08 ft, a marginal speckle
   reduction against a loss of shadow/relief detail). **This was later
   found to be wrong**: the output file is byte-identical to attempt 3's
   (checksum-verified, including an independent from-scratch re-run),
   so widening the window changed nothing on this tile, and neither
   observation reflected a real effect. Full correction, including the
   PDAL-source-level mechanism, is in `CLAUDE.md` under item #10 — in
   short, SMRF's progressive window-opening algorithm converges once the
   structuring element exceeds the largest real non-ground feature in
   the data, so beyond that scale a wider window is a no-op by
   construction. Window was therefore never actually validated as the
   controlling parameter on this tile.
5. The real fix was recognizing that 35.16% of this tile's points are
   multi-return (vs. 1.023 mean on the primary tile) — genuine physical
   evidence of canopy penetration. Filtering to last/single returns only
   before classification (removing near-certain canopy hits by their
   actual return geometry, not by guessing at geometry-only slope
   parameters), with window kept at 33 ft throughout (never actually
   moved, per the correction above). The remaining fine texture was
   confirmed to be a mix of real rock and solid single-return vegetation
   (e.g., a cactus) that are genuinely indistinguishable by return count
   or SMRF geometry alone — accepted as a permanent, documented
   limitation of this data rather than something to keep chasing.

Final parameters: last/single-return filter → SMRF window 33 ft, slope
0.6, threshold 1.3 ft, scalar 0.75, cell 1.6 ft.

## 6. Batch processing tool

`scripts/batch_process.py` runs any `.laz` tile placed in `data/raw/`
through the same classification pipeline, using per-tile parameters from
a small configuration file rather than one-size-fits-all defaults (since
this project directly demonstrated that defaults tuned for one terrain
can silently misclassify another). It is idempotent (skips a tile whose
output already exists, unless forced to reprocess), fault-tolerant (a
failure on one tile is logged and does not stop the batch), and — this
matters given everything found in section 5 — it checks each tile's
coordinate system before processing and skips (with a clear warning
naming the actual CRS found) anything not already in this project's
standard EPSG:6405, rather than silently reprojecting it unattended.
Verified end-to-end against the three real files present in `data/raw/`,
correctly processing the two valid tiles and correctly flagging the
un-reprojected Tucson download by its wrong CRS.

## 7. Hydrologic analysis

Derived from the primary tile's finished DEM using WhiteboxTools (neither
QGIS nor GRASS turned out to be actually installed in the working
environment, correcting an earlier assumption).

**Depression handling**: a least-cost breach algorithm was applied first
(carves a minimal path through a topographic barrier rather than flooding
the whole depression — chosen specifically to avoid destroying real
incised terrain, such as the wash itself, or real closed depressions),
with standard flood-filling applied only to whatever the breach step
could not resolve. All 101,466 detected pits were fully resolved by
breaching alone; nothing required the more aggressive fallback. Impact
was quantified by directly differencing the corrected DEM against the
original (not by trusting a tool's own summary output), and classified
spatially into three categories: natural terrain west of the wash, the
agricultural area east of it (split using the actual DEM-derived wash
centerline, not a hand-drawn line), and a zone within 150 ft of the tile
boundary. The real (non-edge) terrain in both regions came out
**breach-dominated — a net cut**, not fill — which is reassuring given
the project owner's specific concern about destroying real incised
terrain. Nearly all of the net *fill* volume instead concentrated at the
tile boundary; one specific case (a 9.27 ft fill near the tile's
northeast corner) was traced directly and found to be genuine steep
terrain rather than a data void, consistent with a real depression whose
natural drainage outlet simply lies outside the tile's finite extent.

**Flow routing**: standard D8 flow direction and accumulation.

**Stream network threshold**: derived, not assumed. A slope-area
break-point analysis (the standard geomorphological method for finding
where diffusive hillslope processes give way to channelized flow) gave
no sharp, unambiguous answer even after restricting the analysis to
natural terrain only — a genuinely honest negative result, reported as
such rather than forced into false precision. The deciding method ended
up being a direct visual comparison of candidate networks (extracted at
thresholds spanning 50 to 40,000 cells) against the hillshade, which
surfaced a finding more significant than simple threshold tuning: the
center-pivot field's physical wheel-track rut is a real, continuous
linear depression that is **geometrically indistinguishable from a
natural channel to D8 flow routing at any threshold tested up to several
acres** — raising the threshold enough to fully suppress it would have
first destroyed real tributary detail in the natural terrain. The final
threshold (5,000 cells, ~1.03 acres) was chosen for a clean result in
the natural terrain, with the agricultural-area portion of the network
explicitly flagged in the deliverable as not representing real drainage,
rather than pursued to a number that doesn't exist.

**Watershed delineation**: a boundary-crossing scan across all four tile
edges found the wash's dominant crossing on the north edge (258.4 acres
of accumulated contributing area — the main outlet) and, critically, a
smaller but real crossing on the south edge (3.9 acres) — confirming this
is a **through-flowing system**, not one that originates inside the
tile. (This also resolved the flow direction: the tile's lowest ground
sits near its northeast corner, so drainage here runs south-to-north,
consistent with the regional Santa Cruz River system.) The delineated
watershed from the main outlet covers 258.40 acres (45% of the tile) —
matching the outlet's own flow-accumulation value exactly, a built-in
consistency check. Because the tile is isolated with no adjacent tiles
available, **this watershed is explicitly a lower bound on the true
catchment**, not the complete drainage area — stated directly on the
deliverable figure itself, not only in supporting text, specifically so
the caveat cannot be missed by a reader who only looks at the map.

## 8. Limitations (comprehensive)

- **Tile-boundary edge effects are not corrected for anywhere in this
  project.** SMRF's ground classification, PDAL's flow-accumulation
  truncation, and the hydrologic fill/stream/watershed analysis all
  degrade near a tile's edge, because points or upstream contributing
  area just outside the tile simply do not exist in an isolated,
  single-tile pipeline run. The correct fix — buffering in a margin of
  points or flow from adjacent tiles before processing, then cropping
  back — is not implemented, because this project currently has zero
  pairs of spatially-adjacent tiles to buffer from or test the logic
  against (the two tiles processed are ~15 miles apart). Writing
  speculative, untested buffering code was judged worse than being
  direct about this gap.
- **Rock vs. solid-return vegetation on the Tucson tile cannot be
  separated with this data.** A solid single-return cactus hit and a
  solid rock hit are geometrically identical to SMRF and to return-count
  filtering alike. Resolving this would require intensity-based
  classification or co-registered NDVI/multispectral imagery, neither of
  which this project has. Confirmed with the project owner as a
  permanent limitation, not something to keep pursuing.
- **No external vertical control point falls inside the primary tile**
  (section 4.5). The project's own official NVA figures (section 4.8)
  are real and authoritative but describe the ~2,203 sq mi collection as
  a whole, not a check specific to this exact tile.
- **The hydrologic watershed is a lower bound**, not the true catchment,
  because the wash is confirmed to flow through the tile rather than
  originate inside it (section 7).
- **Vegetated Vertical Accuracy (VVA) was never assessed**, by this
  project or by the original 2015 collection — all official accuracy
  check points were deliberately placed in non-vegetated terrain, per
  the ASPRS methodology used at the time.

## 9. Where things are

- `CLAUDE.md` — living technical memory: exact commands, parameters,
  file paths, and reasoning behind every decision. The primary reference
  for continuing this work.
- `docs/session-log.md` — dated, chronological summary of work sessions.
- `docs/PROJECT_SUMMARY.md` — this document.
- `output/reports/qc_memo.md` — the client-facing QC memorandum (tracked
  in git, unlike most of `output/`, since it is hand-authored prose, not
  a regenerable raster).
- `output/reports/batch_qc.csv` (+ README) — the batch processor's
  per-tile QC log.
- `scripts/` — all processing code: `run_dem.py` and `compare_vendor.py`
  (single-tile primary pipeline), `batch_process.py` +
  `tile_params.json` (multi-tile batch pipeline), `hydrology_0[1-8]_*.py`
  (hydrologic analysis pipeline).
- `scripts/pipelines/` — every PDAL pipeline actually run, as JSON, kept
  as a permanent audit trail.
- `data/raw/` — the three source LAZ tiles. Never modified.
- `output/dem/`, `output/hillshade/`, `output/contours/`,
  `output/hydrology/` — all regenerable outputs. Not stored in git;
  regenerate from the scripts above.
