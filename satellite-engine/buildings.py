#!/usr/bin/env python3
"""Download available OpenStreetMap building footprints for the Bakhmut AOI."""
from pathlib import Path
import argparse
import geopandas as gpd
import osmnx as ox
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOUNDS = (37.949421, 48.556181, 38.043834, 48.621584)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--west", type=float, default=DEFAULT_BOUNDS[0])
    parser.add_argument("--south", type=float, default=DEFAULT_BOUNDS[1])
    parser.add_argument("--east", type=float, default=DEFAULT_BOUNDS[2])
    parser.add_argument("--north", type=float, default=DEFAULT_BOUNDS[3])
    parser.add_argument("--output", default="data/buildings.geojson")
    args = parser.parse_args()
    polygon = box(args.west, args.south, args.east, args.north)
    print("Downloading available OSM building polygons for Bakhmut...")
    try:
        frame = ox.features.features_from_polygon(polygon, tags={"building": True})
    except AttributeError:
        frame = ox.features_from_polygon(polygon, tags={"building": True})
    frame = frame[frame.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    if frame.empty:
        raise SystemExit("No building footprints returned. Check connectivity or try another AOI.")
    frame = frame.reset_index(drop=True)
    frame["building_id"] = range(1, len(frame) + 1)
    # Use only the stable fields needed by the assessment pipeline.
    frame = frame[["building_id", "geometry"]]
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_file(output, driver="GeoJSON")
    print(f"Saved {len(frame):,} building footprints to {output}")
    print("OSM footprint coverage may be incomplete; missing footprints are not evidence of no damage.")


if __name__ == "__main__":
    main()
