from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterstats import zonal_stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate PWTT raster scores to building footprints")
    parser.add_argument("--buildings", required=True, help="Input building footprints GeoJSON/shapefile")
    parser.add_argument("--raster", required=True, help="Single-band PWTT T-statistic GeoTIFF")
    parser.add_argument("--output", required=True, help="Output scored GeoJSON")
    parser.add_argument("--threshold", type=float, default=3.3)
    args = parser.parse_args()

    buildings = gpd.read_file(args.buildings)
    if buildings.empty:
        raise SystemExit("No building geometries found")
    if buildings.crs is None:
        raise SystemExit("Building footprints have no CRS; assign the correct CRS before continuing")

    with rasterio.open(args.raster) as src:
        if src.count < 1:
            raise SystemExit("Raster has no bands")
        raster_crs = src.crs
        nodata = src.nodata

    projected = buildings.to_crs(raster_crs)
    stats = zonal_stats(
        projected,
        args.raster,
        stats=["mean", "max", "count"],
        nodata=nodata,
        all_touched=True,
    )

    buildings["mean_t"] = [s.get("mean") for s in stats]
    buildings["max_t"] = [s.get("max") for s in stats]
    buildings["pixel_count"] = [int(s.get("count") or 0) for s in stats]
    buildings["threshold"] = args.threshold
    buildings["screening_flag"] = [
        bool(v is not None and np.isfinite(v) and v > args.threshold)
        for v in buildings["mean_t"]
    ]
    buildings["review_status"] = "pending"
    buildings["indicator_type"] = "PWTT_change_statistic_not_damage_probability"

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    buildings.to_crs("EPSG:4326").to_file(output, driver="GeoJSON")
    print(f"Saved {len(buildings)} scored footprints to {output}")
    print(f"Candidates above T>{args.threshold}: {int(buildings['screening_flag'].sum())}")


if __name__ == "__main__":
    main()
