#!/usr/bin/env python3
"""
Stage 5: delineate the watershed for the main wash's outlet -- the
highest-accumulation boundary crossing (north edge, 258.4 ac). Snap the
pour point to the actual stream raster first (standard practice, avoids
missing the channel by a pixel), then run Watershed.
"""
import whitebox
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path

ROOT = Path(r"C:\Users\ryans\lidar-portfolio")
HYDRO = ROOT / "output" / "hydrology"

wbt = whitebox.WhiteboxTools()
wbt.set_working_dir(str(HYDRO))
wbt.verbose = True

# main wash outlet, from the boundary-crossing scan (north edge, 258.4 ac)
OUTLET = (982406.26, 403427.31)

pour_pts = gpd.GeoDataFrame({"geometry": [Point(OUTLET)]}, crs="EPSG:6405")
pour_pts_path = HYDRO / "pour_point_raw.shp"
pour_pts.to_file(pour_pts_path)

print("=== JensonSnapPourPoints ===")
wbt.jenson_snap_pour_points(
    pour_pts=str(pour_pts_path),
    streams=str(HYDRO / "streams_t5000.tif"),
    output=str(HYDRO / "pour_point_snapped.shp"),
    snap_dist=15.0,
)

print("\n=== Watershed ===")
wbt.watershed(
    d8_pntr=str(HYDRO / "d8_pointer.tif"),
    pour_pts=str(HYDRO / "pour_point_snapped.shp"),
    output=str(HYDRO / "watershed_main_wash.tif"),
)

print("\nDone:", HYDRO / "watershed_main_wash.tif")
