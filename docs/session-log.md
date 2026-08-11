# Session Log

Chronological record of work sessions on this project, newest last. For
current technical state, exact numbers, and parameter reasoning, see
`CLAUDE.md` — it's the living working memory and is kept current every
session. For a standalone narrative that assumes no prior context, see
`PROJECT_SUMMARY.md`. This log is a diary, not a duplicate of either.

---

## 2026-08-09

Major working session covering essentially the full original project plan
plus everything added beyond it. In rough chronological order:

**Original tile, items #1–9 (QC plan)**
- **#1 Roof vs. pad**: sampled DEM elevation at a residential structure's
  center vs. adjacent yard (+2.85 ft difference) — concrete foundation
  pad, not an unremoved roof. Confirmed by the user against ground truth.
- **#2 Grid alignment + vendor RMSE**: found and fixed a PDAL
  `writers.gdal` extent-rounding bug (1667×1667 vs. 1668×1668 grids
  wouldn't difference); vendor-vs-mine RMSE = 0.162 ft, clears QL2.
- **#3 Internal precision**: sampled raw points in the laser-leveled
  pivot field, fit and removed the real 0.50% design grade, residual
  RMSE = 0.104 ft. Spotted diagonal banding in the residual map, flagged
  for later.
- **#4 Swath overlap**: split by flight line, found a systematic +0.124 ft
  offset between the two dominant lines (519, 600) in their overlap band
  — a real boresight-type discrepancy in the source collection. Explained
  the item-3 banding (that sample sits right at the overlap edge).
- **#5 NGS control**: zero monuments fall inside the tile; the four
  nearest candidates are each individually disqualified (no published
  height, mark not found since 2009, or too far away with a
  datum-converted rather than observed height). Concluded no usable
  external control exists for this tile.
- **#6 Point density + void map**: caught a 6x density-inflation bug in
  PDAL's default radius-based counting (fixed with `binmode: true`).
  Corrected mean density 3.697 pts/m² matches spec, but 19.4% of cells
  fall locally below the QL2 minimum despite the passing average.
- **#7 Contours**: 2 ft interval, 12,258 features, visually clean.
- **#8 DSM/CHM**: built both; CHM's 72.87 ft max value investigated later
  in this same session (see below) rather than left unexplained.
- **#9 QC memo**: written to `output/reports/qc_memo.md`.

**Second tile — Tucson Mountains, item #10**
Found and downloaded a 2021 QL1 tile near Wasson Peak via the TNM API,
reprojected it from its native UTM12N/meters CRS to this project's
EPSG:6405 ft (catching a real bug along the way: the reprojection
silently left Z in meters while X/Y converted correctly, since the
target CRS has no vertical component for `filters.reprojection` to act
on). Measured real terrain slope directly (median 28%, p90 91.5%) rather
than guessing SMRF parameters, then iterated through 5 parameter sets —
two of which (threshold, then slope) produced no visible change at all,
correctly ruling both out. A later attempt to widen the SMRF `window`
was believed at the time to show a real, if subtle, tradeoff (detail
lost for a marginal speckle reduction) but was found in a later session
to be a no-op — that output file is byte-identical to the previous
attempt, confirmed by an independent re-run — so `window` was never
actually validated as the controlling lever here; see CLAUDE.md's
correction note under item #10. The real fix ended up being a
fundamentally different approach (last/single-return prefiltering) than
the flat original tile, not a window change. Landed on a final,
user-confirmed defensible parameter set and stopped deliberately rather
than continuing to chase a rock-vs-cactus ambiguity that this data can't
resolve.

**Batch processor**
Built `scripts/batch_process.py` to run any tile in `data/raw/` through
the pipeline with per-tile parameters, idempotently and fault-tolerantly,
verified end-to-end against all three real files in `data/raw/` at the
time (including correctly catching and skipping the un-reprojected
Tucson download by its wrong CRS).

**Vertical datum, sensor, and NVA — confirmed, not presumed**
Found the original tile's real project documentation on USGS's rockyweb
server (a separate `Elevation/metadata/.../reports/` path from the LPC
tile downloads — the per-tile XML is a content-free stub). Two signed,
independent primary sources (Psomas's accuracy assessment, sealed by a
licensed AZ surveyor; Sanborn's report of survey) confirm NAVD88/Geoid12A,
a Leica ALS70 HP sensor, Feb 20–26 2015 acquisition, and a project NVA of
10.3 cm (raw LAS) / 8.8 cm (DEM). This resolved what had been the
project's single biggest open unknown.

**CHM outlier resolved**
Traced the CHM's 72.87 ft max value to a real utility pole or small
transmission tower (a coherent 5-cell cluster with a thin, mostly
first-of-multi-return signature — the laser passing through a mostly-open
structure — not a building, not noise).

**Units correction**
Found and fixed "US survey feet" mislabeled as such in multiple places;
this project's tile is actually International Feet (EPSG:9002), now
independently confirmed by the primary source documents above.

**Hydrologic analysis, item #11 (beyond the original plan)**
Installed WhiteboxTools (neither QGIS nor GRASS was actually available in
this environment, correcting an earlier assumption in `CLAUDE.md`).
Breach-then-fill depression handling (101,466 pits, all resolved by the
gentler breach step alone), with impact quantified by direct differencing
and classified by region — found the real terrain is breach-dominated
(net cut) while almost all net *fill* volume concentrates at the tile
boundary, tying the fill-impact and edge-truncation concerns together.
Derived the stream threshold empirically (slope-area analysis, no clean
break found) and cross-checked visually — discovered along the way that
the center-pivot field's wheel-track ring is geometrically
indistinguishable from a real channel to D8 flow routing at any
reasonable threshold, so the ag-area network is flagged rather than
threshold-tuned away. Delineated the main wash's watershed (258.4 acres)
from a boundary-crossing scan that also confirmed the system is
through-flowing (enters south, exits north) — stated as a lower bound
directly on the deliverable figure, not just in prose.

**Documentation preservation**
Brought `CLAUDE.md` current (it had drifted stale in several places — a
false "QGIS installed" note, an outdated tile collection-date note, a
Layout section describing several finished items as "todo," a commit
list three commits behind), and created this log and
`docs/PROJECT_SUMMARY.md` as durable, standalone project memory.

**PDF deliverable (this entry)**
Reviewed all 9 rendered QC figures (`scripts/render_figures.py`) for
layout defects (legend/scale-bar/caveat-box collisions) before using
them — all clean, including the two hydrology figures re-rendered
earlier to the same scale-bar/north-arrow standard as the rest. Wrote
the fill/breach-impact map as a tenth standardized figure (it existed
only in an unstandardized form under `output/hydrology/`). Added a new
§5 "Hydrologic Derivatives" section to `qc_memo.md` — item #11's actual
numeric findings (pit/fill volumes by region, stream-network length,
watershed acreage) had never been written into the memo text itself,
only produced as figures — recomputing the region-classified impact
stats fresh from the saved rasters rather than trusting a session-log
summary number for anything that could be independently verified.
Renumbered memo sections 5–9 and fixed every internal `§N` cross-
reference. Built `scripts/build_report.py` (reportlab) to assemble the
memo and all 10 figures into `output/reports/qc_report.pdf`. Hit and
fixed three real bugs along the way: reportlab's ordered-list numbering
came out as "1, 1, 2, 1" instead of "1, 2, 3, 4"; markdown table rows
using an escaped `\|` for absolute-value bars split into the wrong
column count and bled off the page edge; and a table's header row was
left orphaned alone at the bottom of one page with its data stranded,
unrepeated, on the next. Root-caused the list/table-adjacent paragraph
mangling to a line-by-line parser not rejoining markdown's soft-wrapped
continuation lines, and rewrote it as a block-based parser. Also caught
that embedding all figures at their native 300 DPI produced a 94.7 MB
PDF; re-encoding a downsampled (170 DPI) copy per figure before
embedding cut it to 18.4 MB with no visible loss at normal zoom.
Verified the final 18-page PDF page-by-page via `pymupdf` (installed
this session for local PDF-to-PNG QC rendering, since no system PDF
renderer was available) rather than trusting the build succeeding
without errors.

## 2026-08-10

**Second-tile scoping, and a real correction to the record**
Started scoping a standalone Tucson Mountains deliverable (parameter
adaptation across terrain, distinct from the San Xavier QC report).
Verified San Xavier vs. Tucson tile characteristics fresh against the
actual point clouds rather than quoting `CLAUDE.md` from memory (point
counts, density, classification breakdown, relief excluding noise
classes, NumberOfReturns distribution) — all matched documented values.
Ran the batch processor for Tucson; it correctly skipped (output already
current for the configured parameters).

Built a first figure set for the case study — terrain-slope context, a
three-panel "no visible change" comparison, and a three-panel
"window-tradeoff" comparison reusing the five already-existing iteration
DEMs. Caught, before shipping any of it, that the window-tradeoff
figure's caption claimed a "less speckle" effect that wasn't actually
visible in the hillshade at print size — the exact measurement-artifact
mistake `CLAUDE.md` already documented once for this same comparison.
Checking the underlying data instead of the caption's claim found
something bigger: `dem_tucson_w65_s0.6_t1.3.tif` (window=65) is
byte-identical to `dem_tucson_w33_s0.6_t1.3.tif` (window=33) — confirmed
via checksum and an independent from-scratch pipeline re-run, ruling out
a stale file. The originally-documented "8.08 ft diff" for this step was
real, but measured against the wrong baseline (attempt 1, which had
already diverged via the threshold and slope changes in attempts 2–3),
so it was re-detecting an earlier change, not a window effect. Corrected
`CLAUDE.md`, this log, and `PROJECT_SUMMARY.md` — a wrong record left
uncorrected is a hazard to every future session, not just the current
deliverable.

Checked whether the same issue affects the San Xavier report's own
window sweep (60/120/180/240 ft, cited in §4 as evidence for the
roof/pad finding): `w120`, `w180`, and `w240` are all byte-identical to
each other; only `w60` differs. So that claim is directionally true but
overstated — two genuinely distinct configurations were tested, not
four; the top three of four attempted values happened to converge.

Found the actual mechanism in PDAL's source rather than speculating
(`filters/SMRFilter.cpp`, `progressiveFilter()`, PDAL 2.10.0, fetched
from the PDAL GitHub repo at the installed version's tag): `window` is a
genuine linear-unit distance, correctly converted to a pixel radius via
`ceil(window / cell)` — not a units bug, not extent clamping. The
algorithm progressively opens the surface up to that radius with a
threshold that grows alongside it, so once the structuring element
exceeds the largest real non-ground feature actually present in the
data, further radius growth is a no-op by construction. San Xavier's own
window sweep corroborates this exactly: convergence somewhere between 60
and 120 ft there, consistent with the pad features (~70–100 ft) sitting
inside that range, while Tucson's vegetation/rock texture apparently
converges well below its tested range (33–65 ft), so neither tested
value mattered.

**San Xavier §4 rewritten with the stronger version of the finding**
The original sentence ("widening the SMRF window from 60 to 240 ft did
not remove these features") read as four independent tests all failing,
when only two configurations were genuinely distinct. Rather than just
softening it, rewrote §4 around what the data actually supports, which
turned out to be a better argument than the original: the tested windows
map to pixel radii 19/37/55/73 at this tile's 3.3 ft cell size, and the
observed convergence between 60 and 120 ft lines up quantitatively with
the pad footprints independently measured at ~70–100 ft across. The
convergence point is *where the measured footprint size predicts it
should be* — evidence for the pad interpretation, not merely an absence
of counter-evidence. Also noted that no pipeline JSON survives for the
`w60` run (predates the audit-trail convention), so its parameters
aren't independently verifiable from a saved artifact. Report rebuilt to
19 pages (from 17 — the more precise explanation runs longer than the
sentence it replaced), re-verified page by page, and a stale sentence in
the appendix intro that `build_report.py` hardcodes separately from
`qc_memo.md` was fixed to match. The one-pager needed no change (its
"window 120 ft" reference is the production DEM parameter, unrelated to
the diagnostic sweep).

Caught an unrelated regression while staging: running `batch_process.py`
earlier purely for orientation had overwritten two rows of real per-tile
QC stats in the tracked `batch_qc.csv` with blank `skipped_existing`
rows. Reverted before committing and documented the gotcha in
`CLAUDE.md`'s Housekeeping section.

**Tucson figure set rebuilt around the corrected story**
The two figures built on the retracted window claim were rebuilt rather
than patched — the premise itself was gone, not just the caption. The
replacement for the window-tradeoff panel is a bar chart of what the
final step *actually* changed: last-return prefiltering keeps 22,568,593
of 27,722,077 points (81.4%) and drops 5,153,484 (18.6%) as likely
canopy hits — a real, verifiable number, shown as a number because it
isn't something a rendered surface can display. The before/after panel
became an explicitly-captioned "visually near-identical, and that's
expected" comparison, since the honest outcome of that step is recovered
confidence in the method, not a visible reduction in speckle (which
persists by design, a disclosed limitation). Terrain-context and
negative-results figures were unchanged — both had already been checked
against what they actually demonstrate.

The SMRF `window` mechanism was promoted from a correction footnote to
its own `## RESOLVED:` section in `CLAUDE.md`, since it's reusable
knowledge rather than a one-tile incident: it predicts, for any future
tile, that a window sweep only reveals a difference if the tested range
spans the transition between "smaller than the largest real non-ground
feature" and "larger than it," and that a convergence point is itself a
rough measurement of that feature scale. Two new working rules were
added to "How I want to work" — captions may not claim more than the
figure demonstrates, and "did this parameter change anything?" is
answered by checksum, never by eye or by whole-tile summary statistics
(both of which failed on exactly this question).

**Tucson case study status**: figure set complete and verified; written
narrative and assembled PDF not started.

**A second audit, this time of CLAUDE.md's own numbers**
The first audit covered the four deliverables; this one covered what
`CLAUDE.md` carries that they don't, on the reasoning that a wrong number
there propagates further than one in a report. Everything checkable
verified exactly — the full vendor-diff outlier breakdown (6,510 cells;
715/5,795 split; 3,879 west / 2,631 east; percentiles and extremes), swath
percentiles and coverage, all 23 boundary crossings, class-2 shares, the
NGS bounds lat/lon conversion to five decimals, Tucson's raw-header
pseudo-relief, watershed acreage in square miles, every declared
environment version including the WhiteboxTools binary, and both
`batch_qc.csv` void counts. One real defect: `batch_qc_README` defined
`z_min_ft`/`z_max_ft` as "the range actually present in the output DEM"
when it is actually PDAL's stats on the ground-classified *points* — the
raster range is narrower because IDW smooths extremes. Corrected. Two
non-errors flagged for the record: the two raw-file sizes use different
conventions (33 MB decimal, 83.8 MB binary), and the centre-pivot circle's
centre/radius is approximate landscape description that nothing depends on.

**A false constraint, discovered by being challenged**
The project had recorded, in three documents, that multi-tile seam
buffering could not be implemented because "this project currently has
zero pairs of spatially-adjacent tiles… so there's nothing to buffer from
and no way to test the logic." That was never a property of the data — it
was a property of what had already been downloaded. The entire Eastern
Pima County collection is public; all eight tiles adjacent to `980398`
sit on the same rockyweb path the original came from, 29.9–35.5 MB each,
and one TNM API bbox query returns the whole 3x3 ring. Nobody ran that
query. The constraint was inherited from the initial download scope and
then restated as though it were a finding. Same shape as the other
verification failures this project has hit: an assumption nobody tested,
surviving because it was written down confidently.

**Multi-tile seam baseline (item #12)**
Downloaded the four edge-sharing neighbours (corners skipped — they share
a single point and contribute almost nothing to a seam test at equal
cost). Verified CRS from LAZ headers *before* processing, given the Tucson
tile's silent metres-in-Z precedent: all five are EPSG:6405 feet and each
shares a full 5,000 ft edge. Added all four to `tile_params.json` with
parameters identical to the centre tile, listed explicitly rather than
left to `_default`, because identical parameters are a requirement of the
experiment rather than a convenience.

Wrote `scripts/measure_seams.py` (takes `--tag`, so the same code measures
the buffered rerun). Adjacent tiles abut rather than overlap, so there is
nothing to difference; the discontinuity is measured as the elevation step
across the boundary, sampled the full 5,000 ft at 3 ft spacing, and
compared against "pseudo-seams" inside the centre tile that measure
natural terrain roughness with no boundary involved.

The first run pooled that baseline across the whole tile and reported the
E seam at 0.99x — apparently no artifact at all. That was wrong for a
familiar reason: the east half is flat irrigated agriculture and the west
has hills, so a tile-averaged baseline is the wrong reference. Recomputed
per side, the E seam is 1.60x. All four seams show real excess: N 2.71x,
S 3.23x, E 1.60x, W 1.40x, against local baselines of 0.14–0.29 ft RMS.
The character is predominantly noise — systematic offsets are significant
on three of four seams but small (0.016–0.103 ft) against spreads of
0.219–0.642 ft, so this is per-cell disagreement rather than a datum-like
shift. Two things flagged rather than asserted: the systematic components
are the same order as the documented +0.124 ft flight-line offset and this
measurement can't separate them, and the N/S seams being ~2x worse than
E/W is consistent with flight lines running N–S but that's untested.

**3D perspective rendering**
Installed PyVista; confirmed off-screen rendering works here before
building anything, since that was the main risk. `scripts/render_3d.py`
drapes the hillshade as a real VTK texture (so detail survives mesh
decimation) with camera bearing, elevation, exaggeration, distance and
decimation all on the CLI. Vertical exaggeration goes in both the filename
and an on-image caption — neither alone survives, since filenames are lost
on paste and captions on rename — along with true vs apparent slope so a
viewer can calibrate. Two bugs caught while iterating: caption relief was
computed from the decimated array (under-reports, and would drift with
`--decimate`), and the first renders showed vertical "curtain" cliffs at
the tile edge. The initial diagnosis was wrong — ordinary voids, fixed
with `hide_cells`, which worked correctly and changed nothing. Mapping the
void mask found the real cause: the reprojected tile carries a *tapering*
nodata wedge from the UTM→State Plane rotation, ~1,175 void cells in row 0
decaying to 11 by row 10, plus an 11-cell sliver down both sides. Fixed by
auto-trimming to the smallest inset with zero voids.

**Global preferences file**
Created `~/.claude/CLAUDE.md` with cross-project working practices, kept
to ~60 lines with project specifics deliberately excluded. Each rule
carries the failure that produced it rather than standing as generic best
practice, since the failure is what makes the rule persuasive later.

**Session state**: item #12 baseline complete and committed; `--buffer-ft`
not started. That is the next task and the deliverable is the before/after
seam number.

**Item #12 completed: buffered tile-edge classification**
Implemented `--buffer-ft` in `batch_process.py` -- a header-bounds spatial
index (deliberately not the `<easting>_<northing>` filename convention,
which is one vendor's delivery scheme rather than a property of LAZ),
neighbour selection by expanded-box intersection, then a pipeline that
merges target + neighbours, crops to the expanded box, classifies, and
crops back to the true tile bounds before rasterizing. Verified two things
before trusting any result: that `--buffer-ft 0` reproduces the committed
baseline pipeline byte-for-byte, and that the buffer does not leak into
the output (buffered rasters occupy the identical grid, origin and
dimensions as the unbuffered ones, so the comparison isn't confounded by
a grid change). Caught one flaw in my own first version -- the `_buf150`
tag was appended even for tiles with no neighbours, which would have
asserted in the filename that an isolated tile was buffered when it
wasn't; neighbours are now resolved before the output is named.

The result is more interesting than "buffering helps". All four seams
improved on RMS, but the improvement splits sharply by orientation:
N -32.3%, S -40.8% (these cut across the N-S flight lines) against
E -3.6%, W -6.3% (these run parallel to them). That split had been
predicted from the unbuffered baseline alone, before the buffered run
existed, on the reasoning that buffering cannot correct flight-line
calibration error -- so the buffered run tested a standing prediction
rather than being mined for a pattern afterwards, which is the stronger
form of evidence and is stated that way in the memo.

Deliberately kept two things out of a tidy "uniform improvement" story.
First, one component of one seam regressed: the W seam's systematic
offset grew -0.0623 -> -0.0656 ft, with its t strengthening from -6.3 to
-7.1 -- and that t moved for two separable reasons, the bias growing
slightly *and* the noise falling (sd -6.6%), which are worth not
conflating. Second, buffering eliminated the discontinuity nowhere: all
four seams remain at 1.32-1.91x the natural terrain step beside them,
which is the honest ceiling of the technique on this data.

Checked the obvious way this measurement could have flattered itself: the
60/120 ft baseline insets sit inside SMRF's ~122 ft reach, so buffering
could have moved the reference. It didn't (per-side baselines shifted
-1.4% to +5.6%), and the numbers were reported against the fixed
unbuffered baselines regardless.

Also fixed a reproducibility defect from the previous session: the seam
baseline figure had been rendered from a throwaway inline script and
could not be rebuilt. Both seam figures now live in
`scripts/render_seam_figures.py`, which calls `measure_seams.main()` for
both variants rather than hardcoding values, so a figure cannot drift
from the measurement it depicts.

QC memo gained §6 "Tile-Boundary Buffering", sections renumbered 6-10 with
cross-references updated, and the stale "edge effects are not corrected
for / no adjacent tiles exist" limitation replaced by what was actually
measured. Report rebuilt to 23 pages.

**Open from this work**: buffer distance was never optimised. 150 ft was
chosen to exceed SMRF's ~122 ft reach; whether a larger buffer improves
the crossing seams further is untested and is the obvious next experiment.
