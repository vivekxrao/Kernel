
import ee
import pwtt

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache

app = FastAPI(title="Kernel Satellite Comparison API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

PROJECT = "battle-damage-assessment"

WEST = 37.949421
SOUTH = 48.556181
EAST = 38.043834
NORTH = 48.621584

WAR_START = "2022-02-22"
INFERENCE_START = "2024-07-01"

PRE_INTERVAL = 12
POST_INTERVAL = 1

def initialize_ee():
    try:
        ee.Initialize(project=PROJECT)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=PROJECT)


def get_tile_url(image, visualization):
    map_info = image.getMapId(visualization)
    return map_info["tile_fetcher"].url_format


@lru_cache(maxsize=1)
def build_layers():

    initialize_ee()

    aoi = ee.Geometry.Rectangle([
        WEST, SOUTH, EAST, NORTH
    ])

    print("Loading Sentinel-1 imagery...")

    collection = (
        ee.ImageCollection("COPERNICUS/S1_GRD_FLOAT")
        .filter(
            ee.Filter.listContains(
                "transmitterReceiverPolarisation", "VH"
            )
        )
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filterBounds(aoi)
        .map(pwtt.lee_filter)
        .select(["VV", "VH"])
        .map(lambda image: image.log())
    )

    # Exact pre-event period used by PWTT
    before = (
        collection
        .filterDate("2021-02-22", WAR_START)
        .median()
        .clip(aoi)
    )

    # Exact inference period used by PWTT
    after = (
        collection
        .filterDate(INFERENCE_START, "2024-08-01")
        .median()
        .clip(aoi)
    )

    print("Building PWTT damage layer...")

    result = pwtt.detect_damage(
        aoi=aoi,
        war_start=WAR_START,
        inference_start=INFERENCE_START,
        pre_interval=PRE_INTERVAL,
        post_interval=POST_INTERVAL,
        viz=False,
        export=False
    )

    before_visualization = {
        "bands": ["VV", "VH", "VV"],
        "min": -10,
        "max": -1,
        "gamma": 1.3
    }

    after_visualization = {
        "bands": ["VV", "VH", "VV"],
        "min": -10,
        "max": -1,
        "gamma": 1.3
    }

    damage_visualization = {
        "min": 3,
        "max": 8,
        "palette": [
            "ffff00",
            "ff9900",
            "ff3300",
            "9900ff"
        ]
    }

    print("Generating map tiles...")

    return {
        "before": get_tile_url(
            before, before_visualization
        ),
        "after": get_tile_url(
            after, after_visualization
        ),
        "damage": get_tile_url(
            result.select("T_statistic"),
            damage_visualization
        ),
        "dates": {
            "before": "2021-02-22 to 2022-02-22",
            "after": "2024-07-01 to 2024-08-01"
        }
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "satellite-comparison"}


@app.get("/api/layers")
def layers():
    try:
        return build_layers()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
