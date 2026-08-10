#!/usr/bin/env python3
"""
Stage 7: final deliverable figures.
  A) fill/breach impact classified by region (natural-west / ag-east / edge-adjacent)
  B) hillshade + stream network (ag-area segments flagged) + watershed +
     pour point + boundary crossings, with the lower-bound caveat printed
     directly on the figure.
"""
import rasterio
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

ROOT = r"C:\Users\ryans\lidar-portfolio"
HYDRO = f"{ROOT}/output/hydrology"

hs_ds = rasterio.open(f"{ROOT}/output/hillshade/hs_w120_s0.15_t1.6.tif")
hs = hs_ds.read(1)
extent = [hs_ds.bounds.left, hs_ds.bounds.right, hs_ds.bounds.bottom, hs_ds.bounds.top]
minx, miny, maxx, maxy = hs_ds.bounds

# ============ FIGURE A: classified fill impact ============
fill_ds = rasterio.open(f"{HYDRO}/fill_impact_total.tif")
fill = fill_ds.read(1)
transform = fill_ds.transform
h, w = fill.shape
changed = (fill != fill_ds.nodata) & (np.abs(fill) > 0.05)

rows_idx, cols_idx = np.indices(fill.shape)
xs, ys = rasterio.transform.xy(transform, rows_idx, cols_idx)
xs = np.array(xs).reshape(fill.shape)
ys = np.array(ys).reshape(fill.shape)

region_gdf = gpd.read_file(f"{HYDRO}/region_split_west_east.gpkg")
west_piece = region_gdf[region_gdf.region == "natural_west"].geometry.iloc[0]
import shapely
west_mask = shapely.contains_xy(west_piece, xs, ys)
edge_dist = 150
near_edge = ((xs - minx) < edge_dist) | ((maxx - xs) < edge_dist) | \
            ((ys - miny) < edge_dist) | ((maxy - ys) < edge_dist)

fig, ax = plt.subplots(figsize=(11, 11), dpi=130)
ax.imshow(hs, cmap="gray", extent=extent, origin="upper")

cls_natural = changed & west_mask & ~near_edge
cls_ag = changed & ~west_mask & ~near_edge
cls_edge = changed & near_edge

overlay = np.zeros((*fill.shape, 4))
overlay[cls_natural] = [0.85, 0.1, 0.1, 1]     # red = natural west, the real concern
overlay[cls_ag] = [1.0, 0.75, 0.0, 0.85]        # amber = ag east, expected artifact
overlay[cls_edge] = [0.1, 0.4, 1.0, 1]          # blue = edge-adjacent, likely truncation artifact
ax.imshow(overlay, extent=extent, origin="upper")

region_gdf.boundary.plot(ax=ax, color="lime", linewidth=1.2, linestyle="--")

legend_elems = [
    Patch(facecolor=[0.85, 0.1, 0.1, 1], label="Natural terrain, west of wash (the real concern)"),
    Patch(facecolor=[1.0, 0.75, 0.0, 0.85], label="Ag area, east of wash (engineered surface, expected)"),
    Patch(facecolor=[0.1, 0.4, 1.0, 1], label="Within 150 ft of tile boundary (likely truncation artifact)"),
    Line2D([0], [0], color="lime", linestyle="--", label="Wash-derived west/east divider"),
]
ax.legend(handles=legend_elems, loc="lower left", fontsize=8, framealpha=0.9)
ax.set_title("Fill/breach impact by region (|change| > 0.05 ft)")
ax.set_xlabel("Easting (ft)")
ax.set_ylabel("Northing (ft)")
plt.tight_layout()
plt.savefig(f"{HYDRO}/fill_impact_classified.png")
print("saved fill_impact_classified.png")
plt.close()

# ============ FIGURE B: final hydrology overlay ============
streams_gdf = gpd.read_file(f"{HYDRO}/streams_final_t5000.gpkg")
watershed_gdf = gpd.read_file(f"{HYDRO}/watershed_main_wash.gpkg")
pour_pt = gpd.read_file(f"{HYDRO}/pour_point_snapped.shp")
if pour_pt.crs is None:
    pour_pt = pour_pt.set_crs("EPSG:6405")

streams_west = streams_gdf[streams_gdf.intersects(west_piece)]
# a stream segment is "ag-flagged" if it's NOT within the west (natural) piece
streams_ag = streams_gdf[~streams_gdf.index.isin(streams_west.index)]

fig, ax = plt.subplots(figsize=(12, 12), dpi=140)
ax.imshow(hs, cmap="gray", extent=extent, origin="upper")

watershed_gdf.boundary.plot(ax=ax, color="cyan", linewidth=2, label="Main wash watershed (see caveat)")
streams_west.plot(ax=ax, color="red", linewidth=0.9)
streams_ag.plot(ax=ax, color="orange", linewidth=0.7, linestyle="-")
pour_pt.plot(ax=ax, color="lime", markersize=60, marker="*", zorder=5)

# mark the south-edge entry crossing too (secondary, smaller)
ax.plot([984053.26], [398429.31], marker="v", color="yellow", markersize=10, zorder=5)

legend_elems = [
    Line2D([0], [0], color="red", linewidth=1.5, label="Stream network, natural terrain (trust as drainage)"),
    Line2D([0], [0], color="orange", linewidth=1.5, label="Stream network, ag area (DO NOT interpret as real drainage --\nsee pivot-field wheel-track finding)"),
    Line2D([0], [0], color="cyan", linewidth=2, label="Main wash watershed, delineated within this tile"),
    Line2D([0], [0], marker="*", color="lime", linewidth=0, markersize=14, label="Main wash outlet (pour point), north edge, 258 ac"),
    Line2D([0], [0], marker="v", color="yellow", linewidth=0, markersize=8, label="Minor tributary entry, south edge, 3.9 ac"),
]
ax.legend(handles=legend_elems, loc="lower left", fontsize=8, framealpha=0.9)

caveat = (
    "CAVEAT: this tile is isolated (no adjacent tiles). The wash enters at the south\n"
    "edge (3.9 ac) and exits at the north edge (258 ac) -- a through-flowing system.\n"
    "The watershed shown is therefore a LOWER BOUND on the true catchment, not the\n"
    "complete drainage area. Flow accumulation and the stream network are both\n"
    "systematically undercounted within ~1 flow-path of every tile edge."
)
ax.text(0.02, 0.98, caveat, transform=ax.transAxes, fontsize=9, va="top", ha="left",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="black"))

ax.set_title("Derived hydrology: streams, watershed, and tile-boundary caveats")
ax.set_xlabel("Easting (ft)")
ax.set_ylabel("Northing (ft)")
plt.tight_layout()
plt.savefig(f"{HYDRO}/hydrology_final_overlay.png")
print("saved hydrology_final_overlay.png")
