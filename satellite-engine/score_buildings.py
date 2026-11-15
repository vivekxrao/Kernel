#!/usr/bin/env python3
"""Aggregate the PWTT T-statistic raster to individual building footprints."""
from pathlib import Path
import argparse
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--buildings", default="data/buildings.geojson")
    parser.add_argument("--raster", default="data/Kernel_T_Statistic.tif")
    parser.add_argument("--output", default="data/scored_buildings.geojson")
    parser.add_argument("--threshold", type=float, default=3.3)
    args = parser.parse_args()
    buildings_path = ROOT / args.buildings
    raster_path = ROOT / args.raster
    output_path = ROOT / args.output
    for path in (buildings_path, raster_path):
        if not path.exists():
            raise SystemExit(f"Required input not found: {path}")

    print(f"Reading building footprints: {buildings_path}")
    buildings = gpd.read_file(buildings_path)
    if buildings.empty:
        raise SystemExit("Building footprint file is empty")

    print(f"Reading raster metadata: {raster_path}")
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
        nodata = src.nodata
        if raster_crs is None:
            raise SystemExit("Raster has no CRS; cannot safely perform spatial aggregation")
        if src.count < 1:
            raise SystemExit("Raster has no bands")

    if buildings.crs is None:
        raise SystemExit("Building footprints have no CRS; cannot safely perform spatial aggregation")
    buildings = buildings.to_crs(raster_crs)

    print(f"Computing zonal mean/max/count (screening threshold T > {args.threshold})...")
    records = zonal_stats(
        buildings.geometry,
        str(raster_path),
        stats=["mean", "max", "count"],
        nodata=nodata,
        band=1,
        all_touched=False,
    )
    means = [item.get("mean") for item in records]
    maxima = [item.get("max") for item in records]
    counts = [int(item.get("count") or 0) for item in records]
    buildings["mean_t"] = means
    buildings["max_t"] = maxima
    buildings["valid_pixels"] = counts
    buildings["screening_flag"] = [m is not None and float(m) > args.threshold for m in means]
    buildings["screening_status"] = [
        "No raster data" if m is None or c == 0 else
        "Flagged for review" if float(m) > args.threshold else
        "Below threshold"
        for m, c in zip(means, counts)
    ]
    buildings["review_status"] = "Pending human verification"
    buildings["screening_threshold"] = args.threshold

    # Export in WGS84 so web-map consumers receive standard GeoJSON coordinates.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    buildings.to_crs("EPSG:4326").to_file(output_path, driver="GeoJSON")
    valid = sum(m is not None and c > 0 for m, c in zip(means, counts))
    flagged = sum(m is not None and float(m) > args.threshold and c > 0 for m, c in zip(means, counts))
    print("\nBuilding scoring complete")
    print(f"Total footprints: {len(buildings):,}")
    print(f"With valid raster pixels: {valid:,}")
    print(f"Flagged for review: {flagged:,}")
    print(f"Below threshold / other: {len(buildings) - flagged:,}")
    print(f"Output: {output_path}")
    print("These are statistical change indicators, not verified damage labels.")


if __name__ == "__main__":
    main()
