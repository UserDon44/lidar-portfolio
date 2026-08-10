#!/usr/bin/env python3
"""
Re-derives the two feature measurements cited in qc_memo.md §4 and §3.6.

Why this script exists: both numbers were originally produced by one-off
interactive analysis whose *method parameters* were never recorded --
only the results. A 2026-08-10 audit found §4's "~70-100 ft" footprint
and §3.6's "13 points / ~3 ft / ~17 ft" could not be reproduced, because
nothing stated the threshold, search radius, or ground reference used.
The results here are now defined by executable code, so the memo's
numbers are checkable rather than merely asserted.

Run:  python scripts/measure_features.py
"""
import numpy as np
import rasterio
import laspy
from pathlib import Path

ROOT = Path(r"C:\Users\ryans\lidar-portfolio")
DEM = ROOT / "output" / "dem" / "dem_w120_s0.15_t1.6.tif"
CHM = ROOT / "output" / "dem" / "chm.tif"
LAZ = ROOT / "data" / "raw" / "USGS_LPC_Eastern_Pima_County_Lidar_980398.laz"

# --- §4 parameters -------------------------------------------------------
PAD_X, PAD_Y = 980339.26, 400067.31   # sample point, QC memo §4
PAD_STEP = 2.85                        # measured pad height above open ground
PLATEAU_R = 12.0                       # radius defining the pad-top elevation
RAY_STEP_DEG = 15                      # radial sampling increment
RAY_MAX = 150.0                        # give up beyond this distance

# --- §3.6 parameters -----------------------------------------------------
TALL_R = 20.0        # circular search radius about the CHM maximum
TALL_MIN_HAG = 10.0  # height above ground qualifying as a "tall" return


def pad_footprint():
    """Radial-profile extent of the raised built surface around the §4 pad.

    Connected-component labelling does NOT work here: at any threshold low
    enough to reach the pad edge, the pad is contiguous with the driveway
    and loop-road embankment, so the blob runs off to the road network
    (this reproduces the failure already documented in CLAUDE.md). Radial
    profiles avoid that -- each bearing is measured independently, so a
    single connected direction can't contaminate the others.

    Edge criterion: the first cell along a bearing lying more than half the
    measured pad step (2.85/2 = 1.43 ft) below the pad-top elevation. Half
    the step is the physically motivated cut -- a point that far below the
    pad top is unambiguously off the built surface rather than on its
    graded crown or shoulder.
    """
    ds = rasterio.open(DEM)
    A = ds.read(1).astype(np.float64)
    A = np.where(A == ds.nodata, np.nan, A)

    def z(px, py):
        r, c = ds.index(px, py)
        return A[r, c]

    plateau = [z(PAD_X + dx, PAD_Y + dy)
               for dx in np.arange(-PLATEAU_R, PLATEAU_R + 3, 3)
               for dy in np.arange(-PLATEAU_R, PLATEAU_R + 3, 3)
               if np.hypot(dx, dy) <= PLATEAU_R]
    top = np.nanmedian(plateau)
    drop = PAD_STEP / 2.0

    edges = {}
    for ang in range(0, 360, RAY_STEP_DEG):
        a = np.radians(ang)
        edges[ang] = None
        for r in np.arange(3, RAY_MAX, 3):
            v = z(PAD_X + r * np.sin(a), PAD_Y + r * np.cos(a))
            if not np.isfinite(v):
                break
            if v < top - drop:
                edges[ang] = r
                break

    closed = [v for v in edges.values() if v is not None]
    spans = []
    for a in range(0, 180, RAY_STEP_DEG):
        p, q = edges[a], edges[(a + 180) % 360]
        if p is not None and q is not None:
            spans.append(p + q)

    print("=== QC memo §4: pad footprint ===")
    print(f"  pad-top elevation (median within {PLATEAU_R:.0f} ft): {top:.2f} ft")
    print(f"  edge criterion: first cell > {drop:.2f} ft below pad top")
    print(f"  rays closing within {RAY_MAX:.0f} ft: {len(closed)}/{len(edges)}")
    print(f"  edge radius: min {min(closed):.0f} / median {np.median(closed):.0f} "
          f"/ max {max(closed):.0f} ft")
    print(f"  characteristic width (2x median radius): {2*np.median(closed):.0f} ft")
    print(f"  closed-axis spans: {min(spans):.0f}-{max(spans):.0f} ft")
    open_dirs = [a for a, v in edges.items() if v is None]
    if open_dirs:
        print(f"  OPEN (no edge found) at bearings: {open_dirs} "
              f"-- merges with driveway/road embankment")
    return 2 * np.median(closed)


def tall_point_cluster():
    """Return geometry of the cluster producing the CHM maximum (§3.6).

    Ground reference is the delivered bare-earth DEM (not a local minimum),
    and the search is a circular radius about the CHM's argmax cell. Both
    were unrecorded in the original analysis, which is why its point count
    could not be reproduced.
    """
    cds = rasterio.open(CHM)
    C = cds.read(1).astype(np.float64)
    C = np.where((C == cds.nodata) | ~np.isfinite(C), -9e9, C)
    r, c = np.unravel_index(np.argmax(C), C.shape)
    mx, my = cds.xy(r, c)
    cmax = C[r, c]

    las = laspy.open(LAZ).read()
    x, y, zz = np.array(las.x), np.array(las.y), np.array(las.z)
    rn, nr = np.array(las.return_number), np.array(las.number_of_returns)
    sel = np.hypot(x - mx, y - my) <= TALL_R
    xs, ys, zs, rns, nrs = x[sel], y[sel], zz[sel], rn[sel], nr[sel]

    dem = rasterio.open(DEM)
    D = dem.read(1)
    gz = np.array([D[dem.index(a, b)] for a, b in zip(xs, ys)])
    hag = zs - gz
    t = hag > TALL_MIN_HAG

    print("\n=== QC memo §3.6: CHM tall-point cluster ===")
    print(f"  CHM maximum {cmax:.2f} ft at ({mx:.2f}, {my:.2f})")
    print(f"  search: circular r={TALL_R:.0f} ft, ground = delivered bare-earth DEM")
    print(f"  returns > {TALL_MIN_HAG:.0f} ft above ground: {int(t.sum())}")
    if t.sum():
        tx, ty = xs[t], ys[t]
        fom = int(((nrs[t] >= 2) & (rns[t] == 1)).sum())
        print(f"  horizontal extent: {tx.max()-tx.min():.1f} ft (E-W) x "
              f"{ty.max()-ty.min():.1f} ft (N-S)")
        print(f"  first-return-of-a-multi-return pulse: {fom}/{int(t.sum())}")
        print(f"  NumberOfReturns values present: {sorted(set(nrs[t].tolist()))}")


if __name__ == "__main__":
    pad_footprint()
    tall_point_cluster()
