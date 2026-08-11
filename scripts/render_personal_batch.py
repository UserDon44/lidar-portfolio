#!/usr/bin/env python3
"""
Batch driver for the PERSONAL / NON-DELIVERABLE render set.

Multiple looks and camera positions per surface rather than one safe
version each. Runs in a single process so PyVista starts once instead of
once per image.

See render_personal.py's docstring and output/renders_personal/README.md
for why nothing here may be used as evidence.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_personal import render, OUT_DIR  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEM = ROOT / "output" / "dem"
SEAMS = ROOT / "output" / "seams"

TUCSON = DEM / "dem_tucson_lastreturn_w33_s0.6_t1.3.tif"
SANX = DEM / "dem_w120_s0.15_t1.6.tif"
MOSAIC = SEAMS / "mosaic_unbuffered.vrt"

# (dem, look, ve, azimuth, elev, distance, decimate, trim, name)
JOBS = [
    # ---- Tucson Mountains: the strongest surface, 305 ft over 3,277 ft.
    (TUCSON, "golden", 8,  300, 13, 1.75, 2, True,  "tucson_golden_ve8_az300"),
    (TUCSON, "ember",  10, 240,  8, 1.70, 2, True,  "tucson_ember_ve10_az240"),
    (TUCSON, "noir",   12, 265,  5, 1.65, 2, True,  "tucson_noir_ve12_az265"),
    (TUCSON, "magma",  8,   45, 20, 1.80, 2, True,  "tucson_magma_ve8_az45"),
    (TUCSON, "ice",    6,  315, 26, 1.85, 2, True,  "tucson_ice_ve6_az315"),
    (TUCSON, "golden", 14, 190,  7, 1.60, 2, True,  "tucson_golden_ve14_az190"),
    (TUCSON, "verdant",9,  135, 17, 1.75, 2, True,  "tucson_verdant_ve9_az135"),

    # ---- San Xavier: flatter (159 ft over 5,000 ft) so it needs more VE.
    (SANX, "verdant", 12, 110, 18, 1.70, 2, True, "sanxavier_verdant_ve12_az110"),
    (SANX, "golden",  16, 250, 10, 1.65, 2, True, "sanxavier_golden_ve16_az250"),
    (SANX, "ice",     10,  20, 24, 1.80, 2, True, "sanxavier_ice_ve10_az20"),
    (SANX, "ember",   20, 300,  7, 1.60, 2, True, "sanxavier_ember_ve20_az300"),

    # ---- San Xavier 5-tile mosaic: a cross, corners are nodata. No trim
    #      (a symmetric inset cannot clear void corners) -- hidden cells
    #      leave the arms standing, which is its own composition.
    (MOSAIC, "verdant", 5, 135, 22, 1.45, 3, False, "mosaic_verdant_ve5_az135"),
    (MOSAIC, "golden",  6, 300, 14, 1.45, 3, False, "mosaic_golden_ve6_az300"),
    (MOSAIC, "magma",   7,  45, 16, 1.45, 3, False, "mosaic_magma_ve7_az45"),
    (MOSAIC, "noir",    6, 225, 10, 1.45, 3, False, "mosaic_noir_ve6_az225"),
]


def main():
    t0 = time.time()
    ok, fail = 0, 0
    for (dem, look, ve, az, el, dist, dec, trim, name) in JOBS:
        if not Path(dem).exists():
            print(f"  SKIP {name}: missing {Path(dem).name}")
            continue
        out = OUT_DIR / f"{name}.png"
        try:
            render(Path(dem), look, ve, az, el, dist, dec,
                   [2200, 1400], out, trim=trim)
            ok += 1
        except Exception as exc:
            print(f"  FAIL {name}: {type(exc).__name__}: {exc}")
            fail += 1
    print(f"\n{ok} rendered, {fail} failed, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
