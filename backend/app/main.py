from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DATA_DIR_VALUE = os.getenv("DATA_DIR", "data")
DATA_DIR = Path(DATA_DIR_VALUE)
if not DATA_DIR.is_absolute():
    DATA_DIR = (BASE_DIR / DATA_DIR).resolve()
GEOJSON_PATH = DATA_DIR / "scored_buildings.geojson"
THRESHOLD = float(os.getenv("DEFAULT_THRESHOLD", "3.3"))
EE_PROJECT_ID = os.getenv("EE_PROJECT_ID", "battle-damage-assessment")
EE_EXPORT_FOLDER = os.getenv("EE_EXPORT_FOLDER", "KernelBDA")

DEFAULT_AOI = [37.949421, 48.556181, 38.043834, 48.621584]
DEFAULT_WAR_START = "2022-02-22"
DEFAULT_INFERENCE_START = "2024-07-01"

app = FastAPI(
    title="Kernel Damage Intelligence API",
    version="1.0.0",
    description="Local decision-support API for Sentinel-1 PWTT screening results.",
)

origins = [x.strip() for x in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class AssessmentRequest(BaseModel):
    west: float = DEFAULT_AOI[0]
    south: float = DEFAULT_AOI[1]
    east: float = DEFAULT_AOI[2]
    north: float = DEFAULT_AOI[3]
    war_start: str = DEFAULT_WAR_START
    inference_start: str = DEFAULT_INFERENCE_START
    pre_interval: int = Field(default=12, ge=1, le=36)
    post_interval: int = Field(default=1, ge=1, le=6)
    export_scale: int = Field(default=10, ge=10, le=100)
    export_name: str = "Kernel_Assessment"


def _read_frame() -> gpd.GeoDataFrame:
    if not GEOJSON_PATH.exists():
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs="EPSG:4326")
    try:
        frame = gpd.read_file(GEOJSON_PATH)
        if frame.crs is None:
            frame = frame.set_crs("EPSG:4326")
        else:
            frame = frame.to_crs("EPSG:4326")
        if "mean_t" not in frame.columns:
            raise HTTPException(status_code=422, detail="scored GeoJSON is missing mean_t")
        numeric = pd.to_numeric(frame["mean_t"], errors="coerce")
        calculated_flag = numeric > THRESHOLD
        if "screening_flag" not in frame.columns:
            frame["screening_flag"] = calculated_flag.fillna(False).astype(bool)
        else:
            frame["screening_flag"] = frame["screening_flag"].fillna(False).astype(bool)
        if "screening_status" not in frame.columns:
            frame["screening_status"] = calculated_flag.map(
                lambda v: "Flagged for review" if bool(v) else "Below threshold"
            )
        if "review_status" not in frame.columns:
            frame["review_status"] = "Pending human verification"
        return frame
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read scored GeoJSON: {exc}") from exc


def _feature_collection(frame: gpd.GeoDataFrame) -> dict[str, Any]:
    # GeoPandas handles geometry/CRS conversion; round-trip through JSON also
    # converts numpy scalar values into JSON-safe Python values.
    payload = json.loads(frame.to_json(drop_id=False))
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        if props.get("building_id") is None and feature.get("id") is not None:
            props["building_id"] = feature["id"]
        props.setdefault("review_status", "Pending human verification")
        feature["properties"] = props
    return payload


def _ee_initialize():
    try:
        import ee
    except ImportError as exc:
        raise RuntimeError("earthengine-api is not installed in the active Python environment") from exc
    project = os.getenv("EE_PROJECT_ID", EE_PROJECT_ID)
    ee.Initialize(project=project)
    return ee


def _comparison_layers(war_start: str, inference_start: str, pre_interval: int, post_interval: int):
    """Build visual context composites and PWTT tiles for the selected dates.

    The before/after images are median SAR context composites over the same
    temporal windows used by the PWTT configuration. PWTT itself continues to
    group T-tests by relative orbit and polarization in the published package.
    """
    ee = _ee_initialize()
    try:
        import pwtt
    except ImportError as exc:
        raise RuntimeError("pwtt is not installed in the active Python environment") from exc

    west, south, east, north = DEFAULT_AOI
    aoi = ee.Geometry.Rectangle([west, south, east, north])
    war_date = ee.Date(war_start)
    inference_date = ee.Date(inference_start)

    collection = (
        ee.ImageCollection("COPERNICUS/S1_GRD_FLOAT")
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filterBounds(aoi)
        .map(pwtt.lee_filter)
        .select(["VV", "VH"])
        .map(lambda image: image.log())
    )
    before = collection.filterDate(
        war_date.advance(-pre_interval, "months"), war_date
    ).median().clip(aoi)
    after = collection.filterDate(
        inference_date, inference_date.advance(post_interval, "months")
    ).median().clip(aoi)

    # Run the exact installed PWTT implementation for the damage-change tile.
    result = pwtt.detect_damage(
        aoi=aoi,
        war_start=war_start,
        inference_start=inference_start,
        pre_interval=pre_interval,
        post_interval=post_interval,
        viz=False,
        export=False,
    )

    sar_vis = {
        "bands": ["VV", "VH", "VV"],
        "min": -5.5,
        "max": -0.5,
        "gamma": 1.2,
    }
    damage_vis = {
        "min": 3,
        "max": 7,
        "palette": ["fff176", "ffb74d", "f4511e", "8e24aa"],
    }

    return {
        "before": before.getMapId(sar_vis)["tile_fetcher"].url_format,
        "after": after.getMapId(sar_vis)["tile_fetcher"].url_format,
        "damage": result.select("T_statistic").getMapId(damage_vis)["tile_fetcher"].url_format,
        "dates": {
            "before_start": war_date.advance(-pre_interval, "months").format("YYYY-MM-dd").getInfo(),
            "before_end": war_start,
            "inference_start": inference_start,
            "inference_end": inference_date.advance(post_interval, "months").format("YYYY-MM-dd").getInfo(),
        },
        "note": "Before/after layers are median SAR context composites. The PWTT layer is generated by the installed package, which calculates separate orbit/polarization statistics.",
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "project": "Kernel Damage Intelligence"}


@app.get("/api/config")
def config():
    return {
        "study_area": "Bakhmut, Ukraine",
        "aoi": {"west": DEFAULT_AOI[0], "south": DEFAULT_AOI[1], "east": DEFAULT_AOI[2], "north": DEFAULT_AOI[3]},
        "war_start": DEFAULT_WAR_START,
        "inference_start": DEFAULT_INFERENCE_START,
        "pre_interval_months": 12,
        "post_interval_months": 1,
        "threshold": THRESHOLD,
        "earth_engine_project_configured": bool(EE_PROJECT_ID),
        "data_file": str(GEOJSON_PATH),
    }


@app.get("/api/summary")
def summary():
    frame = _read_frame()
    if frame.empty:
        return {
            "total_buildings": 0,
            "candidate_buildings": 0,
            "below_threshold": 0,
            "candidate_percent": 0,
            "threshold": THRESHOLD,
            "data_available": False,
            "message": f"No scored_buildings.geojson found at {GEOJSON_PATH}. Run the scoring pipeline first.",
        }
    scores = pd.to_numeric(frame["mean_t"], errors="coerce")
    candidate_count = int((scores > THRESHOLD).sum())
    total = int(len(frame))
    return {
        "total_buildings": total,
        "candidate_buildings": candidate_count,
        "below_threshold": total - candidate_count,
        "candidate_percent": round(candidate_count / total * 100, 1) if total else 0,
        "threshold": THRESHOLD,
        "data_available": True,
        "study_area": "Bakhmut, Ukraine",
        "message": "Change indicators are screening outputs and require human verification.",
    }


@app.get("/api/buildings")
def buildings():
    frame = _read_frame()
    if frame.empty:
        return {"type": "FeatureCollection", "features": []}
    return _feature_collection(frame)


@app.get("/api/export.csv")
def export_csv():
    frame = _read_frame()
    if frame.empty:
        raise HTTPException(status_code=404, detail="No scored building data available")
    table = pd.DataFrame(frame.drop(columns="geometry", errors="ignore"))
    buffer = io.StringIO()
    table.to_csv(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=kernel_building_screening.csv"},
    )


@app.get("/api/layers")
def layers():
    try:
        return _comparison_layers(DEFAULT_WAR_START, DEFAULT_INFERENCE_START, 12, 1)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not create Earth Engine comparison layers: {exc}") from exc


@app.post("/api/assessment/run")
def run_assessment(request: AssessmentRequest):
    if not (request.west < request.east and request.south < request.north):
        raise HTTPException(status_code=400, detail="Invalid AOI bounds")
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,60}", request.export_name):
        raise HTTPException(status_code=400, detail="export_name may contain 3–60 letters, numbers, underscores or hyphens")
    try:
        ee = _ee_initialize()
        import pwtt
        aoi = ee.Geometry.Rectangle([request.west, request.south, request.east, request.north])
        pwtt.detect_damage(
            aoi=aoi,
            war_start=request.war_start,
            inference_start=request.inference_start,
            pre_interval=request.pre_interval,
            post_interval=request.post_interval,
            viz=False,
            export=True,
            export_dir=EE_EXPORT_FOLDER,
            export_name=request.export_name,
            export_scale=request.export_scale,
        )
        matching = []
        for task in ee.batch.Task.list():
            status = task.status()
            if status.get("description") == request.export_name:
                matching.append({
                    "id": status.get("id"),
                    "description": status.get("description"),
                    "state": status.get("state"),
                })
        return {
            "submitted": True,
            "message": f"Earth Engine export submitted to Google Drive folder {EE_EXPORT_FOLDER}. Check the Earth Engine Tasks tab for completion.",
            "tasks": matching,
            "parameters": request.model_dump(),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not submit PWTT assessment: {exc}") from exc


@app.get("/api/tasks")
def tasks():
    try:
        ee = _ee_initialize()
        output = []
        for task in ee.batch.Task.list()[:25]:
            status = task.status()
            output.append({
                "id": status.get("id"),
                "description": status.get("description"),
                "state": status.get("state"),
                "error_message": status.get("error_message"),
            })
        return {"tasks": output}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not retrieve Earth Engine tasks: {exc}") from exc
