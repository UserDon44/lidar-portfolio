#!/usr/bin/env python3
"""
Measure elevation discontinuity across the four tile seams around
USGS_LPC_Eastern_Pima_County_Lidar_980398.

The question: does SMRF's lack of cross-tile neighbourhood context leave a
visible step in the bare-earth surface where two independently-classified
tiles meet?

Method
------
Adjacent tiles abut rather than overlap, so there is no shared area to
difference. The discontinuity is therefore measured as the elevation STEP
across the boundary: sample each tile's DEM 1.5 ft inside its own edge, so
the two samples are 3 ft apart (one cell) and straddle the seam, then take
the difference. Sampling runs the full 5,000 ft length of each seam at 3 ft
intervals.

A raw step size means nothing on its own -- real terrain also changes over
3 ft. So every seam is compared against a BASELINE built the same way from
the same terrain: "pseudo-seams" at fixed distances inside the centre tile,
parallel to the real seam, sampled with the identical 3 ft straddle. Those
measure natural terrain roughness at 3 ft spacing with no tile boundary
involved. A real edge artifact shows up as a seam step distribution that is
wider (or systematically offset) relative to that baseline.

The baseline is computed PER SIDE, not pooled, because this tile's terrain
is strongly anisotropic: the eastern half is flat irrigated agriculture and
the west has hills, so a tile-averaged baseline would understate the natural
step near the east edge and overstate it near the west. Each seam is judged
only against terrain adjacent and parallel to it.

Systematic vs noise is read from the mean against its own standard error: a
mean step near zero relative to sd/sqrt(n) is noise; a mean many standard
errors from zero is a real systematic offset between the two surfaces. Both
are reported, because they mean different things -- a systematic offset is a
datum-like shift, spread is per-cell disagreement -- and on this data they
have very different magnitudes.

Run:  python scripts/measure_seams.py [--tag SUFFIX]
      --tag selects which DEM variant to measure (default: the unbuffered
      baseline), so the same code measures the buffered rerun later.
"""
import argparse
import numpy as np
import rasterio
from pathlib import Path

# Project root, resolved from this file's own location so these scripts
# run from any checkout rather than one hardcoded directory.
ROOT = Path(__file__).resolve().parent.parent
DEM_DIR = ROOT / "output" / "dem"

CENTRE = "980398"
NEIGHBOURS = {"N": "980403", "S": "980393", "E": "985398", "W": "975398"}

# true tile boundaries from the LAZ headers (not the rasters', which
# writers.gdal rounds outward by up to a cell)
TILE = dict(minx=980112.76, maxx=985112.75, miny=398427.81, maxy=403427.80)

STRADDLE = 1.5      # ft each side of the seam -> 3 ft between samples
STEP = 3.0          # ft between samples along the seam
BASELINE_INSETS = [60.0, 120.0, 240.0, 480.0]   # ft inside the centre tile


def dem_path(tile, tag):
    return DEM_DIR / f"dem_USGS_LPC_Eastern_Pima_County_Lidar_{tile}_{tag}.tif"


def sample(ds, arr, xs, ys):
    """Nearest-cell sample; returns NaN outside the raster or at nodata."""
    out = np.full(len(xs), np.nan)
    for i, (x, y) in enumerate(zip(xs, ys)):
        try:
            r, c = ds.index(x, y)
        except Exception:
            continue
        if 0 <= r < arr.shape[0] and 0 <= c < arr.shape[1]:
            v = arr[r, c]
            if v != ds.nodata and np.isfinite(v):
                out[i] = v
    return out


def describe(name, d, n_possible):
    d = d[np.isfinite(d)]
    if d.size == 0:
        print(f"  {name:<34} no valid samples")
        return None
    rms = float(np.sqrt(np.mean(d ** 2)))
    print(f"  {name:<34} n={d.size:5d}/{n_possible:<5d} "
          f"mean {np.mean(d):+7.4f}  med {np.median(d):+7.4f}  "
          f"sd {np.std(d):6.4f}  RMS {rms:6.4f}  p95|d| {np.percentile(np.abs(d),95):6.4f}")
    return dict(n=int(d.size), mean=float(np.mean(d)), median=float(np.median(d)),
                sd=float(np.std(d)), rms=rms, p95=float(np.percentile(np.abs(d), 95)))


def main(tag):
    print(f"Seam discontinuity, DEM variant: {tag}")
    print(f"Straddle {STRADDLE} ft either side (samples {2*STRADDLE:.0f} ft apart), "
          f"sampled every {STEP:.0f} ft along each seam\n")

    cds = rasterio.open(dem_path(CENTRE, tag))
    carr = cds.read(1)
    results = {}

    for side, ntile in NEIGHBOURS.items():
        p = dem_path(ntile, tag)
        if not p.exists():
            print(f"[{side}] missing {p.name}, skipped")
            continue
        nds = rasterio.open(p)
        narr = nds.read(1)

        if side in ("E", "W"):
            seam = TILE["maxx"] if side == "E" else TILE["minx"]
            ys = np.arange(TILE["miny"] + STEP, TILE["maxy"], STEP)
            inside = np.full(len(ys), seam - STRADDLE if side == "E" else seam + STRADDLE)
            outside = np.full(len(ys), seam + STRADDLE if side == "E" else seam - STRADDLE)
            zi, zo = sample(cds, carr, inside, ys), sample(nds, narr, outside, ys)
            n_possible = len(ys)
        else:
            seam = TILE["maxy"] if side == "N" else TILE["miny"]
            xs = np.arange(TILE["minx"] + STEP, TILE["maxx"], STEP)
            inside = np.full(len(xs), seam - STRADDLE if side == "N" else seam + STRADDLE)
            outside = np.full(len(xs), seam + STRADDLE if side == "N" else seam - STRADDLE)
            zi, zo = sample(cds, carr, xs, inside), sample(nds, narr, xs, outside)
            n_possible = len(xs)

        print(f"[{side}] seam with {ntile} (neighbour minus centre)")
        results[side] = describe("across seam", zo - zi, n_possible)

    # ---- baseline: pseudo-seams inside the centre tile, PER SIDE ----
    print("\nBASELINE -- identical 3 ft straddle, no tile boundary involved")
    base = {}
    for side in ("N", "S", "E", "W"):
        acc = []
        for inset in BASELINE_INSETS:
            if side in ("E", "W"):
                x = (TILE["maxx"] - inset) if side == "E" else (TILE["minx"] + inset)
                ys = np.arange(TILE["miny"] + STEP, TILE["maxy"], STEP)
                a = sample(cds, carr, np.full(len(ys), x - STRADDLE), ys)
                b = sample(cds, carr, np.full(len(ys), x + STRADDLE), ys)
            else:
                y = (TILE["maxy"] - inset) if side == "N" else (TILE["miny"] + inset)
                xs = np.arange(TILE["minx"] + STEP, TILE["maxx"], STEP)
                a = sample(cds, carr, xs, np.full(len(xs), y - STRADDLE))
                b = sample(cds, carr, xs, np.full(len(xs), y + STRADDLE))
            d = b - a
            acc.append(d[np.isfinite(d)])
        acc = np.concatenate(acc)
        base[side] = describe(f"{side} side, natural 3 ft step", acc, acc.size)

    print("\nSUMMARY (each seam vs terrain adjacent and parallel to it)")
    print(f"  {'':4} {'seam RMS':>9} {'baseline':>9} {'ratio':>7}   "
          f"{'mean offset':>12} {'SE':>8} {'t':>7}  verdict")
    for side in ("N", "S", "E", "W"):
        r, b = results.get(side), base[side]
        if r is None:
            continue
        se = r["sd"] / np.sqrt(r["n"])
        t = r["mean"] / se
        ratio = r["rms"] / b["rms"]
        if ratio < 1.15:
            v = "no excess over natural terrain"
        elif abs(t) > 3:
            v = "excess spread + systematic offset"
        else:
            v = "excess spread, offset not significant"
        print(f"  {side:<4} {r['rms']:9.4f} {b['rms']:9.4f} {ratio:6.2f}x   "
              f"{r['mean']:+12.4f} {se:8.4f} {t:+7.1f}  {v}")
    return results, base


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="w120_s0.15_t1.6",
                    help="DEM filename tag identifying the variant to measure")
    main(ap.parse_args().tag)
