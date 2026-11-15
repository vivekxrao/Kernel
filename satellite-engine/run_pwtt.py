#!/usr/bin/env python3
"""Run the published PWTT package and download small-area rasters locally.

Uses the exact installed pwtt.detect_damage signature. No unsupported
`threshold` argument is passed. If direct downloads exceed Earth Engine's
interactive-download limits, the script falls back to Google Drive exports.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import zipfile
from pathlib import Path

import ee
import requests
import rasterio
import pwtt

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_AOI = [37.949421, 48.556181, 38.043834, 48.621584]


def parse_args():
    p = argparse.ArgumentParser(description="Run Sentinel-1 PWTT for a configured AOI")
    p.add_argument("--project", default=None, help="Google Cloud / Earth Engine project ID (defaults to EE_PROJECT_ID in .env)")
    p.add_argument("--west", type=float, default=DEFAULT_AOI[0])
    p.add_argument("--south", type=float, default=DEFAULT_AOI[1])
    p.add_argument("--east", type=float, default=DEFAULT_AOI[2])
    p.add_argument("--north", type=float, default=DEFAULT_AOI[3])
    p.add_argument("--war-start", default="2022-02-22")
    p.add_argument("--inference-start", default="2024-07-01")
    p.add_argument("--pre-interval", type=int, default=12)
    p.add_argument("--post-interval", type=int, default=1)
    p.add_argument("--scale", type=int, default=10)
    p.add_argument("--drive-fallback", action="store_true", help="Submit Drive exports if direct download fails")
    return p.parse_args()


def download_image(image, aoi, output: Path, band: str, scale: int):
    params = {
        "name": output.stem,
        "scale": scale,
        "region": aoi,
        "format": "GEO_TIFF",
        "filePerBand": False,
    }
    url = image.select(band).clip(aoi).getDownloadURL(params)
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    content = response.content
    # Earth Engine may return a ZIP container for multi-file responses.
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            tif_names = [n for n in archive.namelist() if n.lower().endswith((".tif", ".tiff"))]
            if not tif_names:
                raise RuntimeError(f"No GeoTIFF found in Earth Engine response for {band}")
            content = archive.read(tif_names[0])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    with rasterio.open(output) as dataset:
        if dataset.count < 1 or dataset.width < 1 or dataset.height < 1:
            raise RuntimeError(f"Downloaded raster {output} is empty")
        print(f"Downloaded {output.name}: {dataset.width} x {dataset.height}, CRS={dataset.crs}, nodata={dataset.nodata}")


def submit_drive_exports(result, aoi, args):
    print("Direct download was not available. Submitting Drive export tasks instead...")
    tasks = []
    for band, description in [("T_statistic", "Kernel_T_Statistic"), ("damage", "Kernel_Damage_Mask")]:
        task = ee.batch.Export.image.toDrive(
            image=result.select(band).clip(aoi),
            description=description,
            folder="KernelBDA",
            region=aoi,
            scale=args.scale,
            maxPixels=1e13,
            fileFormat="GeoTIFF",
        )
        task.start()
        tasks.append(task)
        print(f"Submitted {description}: task {task.id}")
    print("Track these tasks in the Earth Engine Code Editor Tasks panel; then download both files into the project's data/ folder.")


def main():
    args = parse_args()
    if not (args.west < args.east and args.south < args.north):
        raise SystemExit("Invalid AOI bounds")

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    project = args.project or os.getenv("EE_PROJECT_ID", "battle-damage-assessment")
    print(f"Authenticating Earth Engine project: {project}")
    ee.Initialize(project=project)

    aoi = ee.Geometry.Rectangle([args.west, args.south, args.east, args.north])
    print("Building PWTT image using published package...")
    print(f"Reference: {args.pre_interval} months before {args.war_start}")
    print(f"Inference: {args.post_interval} months from {args.inference_start}")
    result = pwtt.detect_damage(
        aoi=aoi,
        war_start=args.war_start,
        inference_start=args.inference_start,
        pre_interval=args.pre_interval,
        post_interval=args.post_interval,
        viz=False,
        export=False,
    )
    print("PWTT image constructed. Bands:", result.bandNames().getInfo())

    try:
        download_image(result, aoi, DATA_DIR / "Kernel_T_Statistic.tif", "T_statistic", args.scale)
        download_image(result, aoi, DATA_DIR / "Kernel_Damage_Mask.tif", "damage", args.scale)
        print("Both GeoTIFFs downloaded locally into data/.")
    except Exception as exc:
        print(f"Direct download failed: {exc}", file=sys.stderr)
        if args.drive_fallback:
            submit_drive_exports(result, aoi, args)
        else:
            raise SystemExit("Retry with --drive-fallback to submit Google Drive export tasks.")


if __name__ == "__main__":
    main()
