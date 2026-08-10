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
