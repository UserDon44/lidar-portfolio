#!/usr/bin/env python3
"""
Stage 6: classify the fill/breach impact map into:
  - natural terrain west of the main wash (the user's actual concern)
  - ag area east of the wash (engineered surfaces, expected artifacts)
  - tile-boundary-adjacent (within 150 ft of any edge, regardless of
    side -- flagged separately since edge proximity itself is a red flag,
    per the NE-corner check earlier)

The dividing line is the actual derived main-trunk wash centerline (high
flow-accumulation cells, >50,000), not a guessed/hand-drawn boundary.
"""
import rasterio
import numpy as np
import geopandas as gpd
import shapely
from shapely.geometry import LineString, box
from shapely.ops import split

HYDRO = r"C:\Users\ryans\lidar-portfolio\output\hydrology"

accum_ds = rasterio.open(f"{HYDRO}/d8_flow_accum_cells.tif")
accum = accum_ds.read(1)
h, w = accum.shape
res = accum_ds.res[0]
transform = accum_ds.transform

# main trunk: high-accumulation cells: >50,000 (well above all the ag-edge
# crossings seen in the boundary scan, which topped out ~121,000 for a
# minor secondary channel but the true trunk is consistently >250,000
# through most of its length -- 50,000 is a safe inclusive floor that
# still excludes ag-field artifacts).
# The wash braids into two channels near the north edge (two large
# crossings, 982406 and 983465) -- isolate the single connected component
# that contains the main outlet (982406, 403427.31) rather than averaging
# across both braids, which produced a self-intersecting zigzag line.
from scipy import ndimage
trunk_mask = accum > 50000
lbl, n = ndimage.label(trunk_mask, structure=np.ones((3, 3)))
outlet_row, outlet_col = accum_ds.index(982406.26, 403427.31)
main_component_id = lbl[outlet_row, outlet_col]
print(f"trunk connected components: {n}, main outlet is in component {main_component_id}")
main_trunk_mask = lbl == main_component_id

rows_with_trunk = np.where(main_trunk_mask.any(axis=1))[0]
centerline_pts = []
for r in rows_with_trunk:
    cols = np.where(main_trunk_mask[r, :])[0]
    # max-accumulation cell in this row (not mean), stays on a single braid
    best_col = cols[np.argmax(accum[r, cols])]
    x, y = rasterio.transform.xy(transform, r, best_col)
    centerline_pts.append((x, y))

centerline_pts.sort(key=lambda p: -p[1])  # north to south
trunk_line = LineString(centerline_pts)
print(f"Trunk centerline: {len(centerline_pts)} points, "
      f"from y={centerline_pts[0][1]:.0f} to y={centerline_pts[-1][1]:.0f}")

# extend the line well past the tile bounds at both ends so it fully
# splits the bounding box (shapely split needs the splitter to cross
# the polygon completely)
minx, miny, maxx, maxy = accum_ds.bounds
buffer_pts = [(centerline_pts[0][0], maxy + 1000)] + centerline_pts + [(centerline_pts[-1][0], miny - 1000)]
trunk_line_ext = LineString(buffer_pts)

tile_box = box(minx, miny, maxx, maxy)
pieces = list(split(tile_box, trunk_line_ext).geoms)
print(f"Split into {len(pieces)} pieces")

# label: the piece containing the residential block (980339, 400067) is "west_natural"
from shapely.geometry import Point
residential_pt = Point(980339, 400067)
west_piece = None
east_piece = None
for p in pieces:
    if p.contains(residential_pt):
        west_piece = p
    else:
        east_piece = p if east_piece is None else east_piece.union(p)

gdf = gpd.GeoDataFrame({"region": ["natural_west", "ag_east"]},
                        geometry=[west_piece, east_piece], crs="EPSG:6405")
gdf.to_file(f"{HYDRO}/region_split_west_east.gpkg", driver="GPKG")
print("saved region split")

# --- classify fill impact ---
fill_ds = rasterio.open(f"{HYDRO}/fill_impact_total.tif")
fill = fill_ds.read(1)
fill_nodata = fill_ds.nodata
changed = (fill != fill_nodata) & (np.abs(fill) > 0.05)

rows_idx, cols_idx = np.indices(fill.shape)
xs, ys = rasterio.transform.xy(transform, rows_idx, cols_idx)
xs = np.array(xs).reshape(fill.shape)
ys = np.array(ys).reshape(fill.shape)

# rasterize the west polygon to a boolean mask (cheap: use the trunk split
# via a simple per-cell point-in-polygon over the small set of changed cells)
west_mask = shapely.contains_xy(west_piece, xs, ys).reshape(fill.shape)

# edge-adjacent flag: within 150 ft of any tile boundary
edge_dist = 150
near_edge = ((xs - minx) < edge_dist) | ((maxx - xs) < edge_dist) | \
            ((ys - miny) < edge_dist) | ((maxy - ys) < edge_dist)

cell_area = res ** 2
def summarize(name, sel):
    m = changed & sel
    n = m.sum()
    vol = np.sum(np.where(m, fill, 0)) * cell_area
    print(f"{name}: {n:,} cells ({100*n/changed.sum():.1f}% of all changed cells), "
          f"volume={vol:,.0f} cu ft, max={np.max(np.where(m,fill,0)):.2f}ft, "
          f"min={np.min(np.where(m,fill,0)):.2f}ft")

print("\n=== Fill/breach impact by region ===")
summarize("Natural terrain, west of wash (NOT edge-adjacent)", west_mask & ~near_edge)
summarize("Ag area, east of wash (NOT edge-adjacent)", ~west_mask & ~near_edge)
summarize("Tile-boundary-adjacent (<150ft of edge, either side)", near_edge)
summarize("TOTAL", np.ones_like(changed, dtype=bool))
