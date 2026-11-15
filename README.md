# KERNEL — Damage Intelligence

A local geospatial decision-support prototype for Sentinel-1 battle-damage change screening. The project combines the published Pixel-Wise T-Test (PWTT) package, Google Earth Engine, OpenStreetMap building footprints, Python geospatial aggregation, FastAPI and a React/Leaflet dashboard.

> **Interpretation:** PWTT outputs are statistical change indicators. A building flagged by the screening threshold is a candidate for human review, not a confirmed damaged or destroyed building. The application is not an operational targeting tool and must not be used to make decisions about people or property without qualified independent verification.

## What is included

- SARDrishti-inspired dark geospatial dashboard branded as **KERNEL**.
- Sidebar navigation: Dashboard, New Assessment, Satellite Comparison, Damage Analysis and Intelligence Reports.
- Live building summary and GeoJSON endpoints; CSV export.
- Clickable building footprints with mean/max T-statistic, valid pixel count and screening status.
- Earth Engine before/after reveal slider using two geographically aligned Sentinel-1 context composites, plus the PWTT T-statistic layer.
- New Assessment form that submits a PWTT image export to the configured Google Drive folder and reports Earth Engine tasks.
- Python scripts to run PWTT, download the two raster bands locally when the Earth Engine interactive-download size limit permits, retrieve building footprints, and score buildings.
- A single macOS startup command that prepares dependencies, preserves existing local data, and starts both servers.

## One-time launch on your Mac

Your existing Mac already has Python 3.11, Node.js, npm and an authenticated Earth Engine account. Extract this ZIP **over the same `~/Downloads/kernel-damage-intelligence` folder** you have been using. The ZIP deliberately does not contain `data/*.tif` or `data/*.geojson`; extracting it over the existing directory leaves those local files in place.

From Terminal, run:

```bash
cd ~/Downloads/kernel-damage-intelligence
chmod +x START_MAC.command
./START_MAC.command
```

The first launch:

1. Reuses your existing `.venv-pwtt` environment if it exists (as in the earlier setup steps); otherwise it uses/creates `.venv` with Python 3.11.
2. Installs or updates backend, geospatial and PWTT dependencies in that environment (may take several minutes on first run).
3. Installs frontend dependencies if `frontend/node_modules` is missing.
4. Creates `.env` from `.env.example` if one does not exist.
5. Reuses `data/scored_buildings.geojson` if present; if it is missing but the PWTT raster is present, it runs building aggregation.
6. Starts FastAPI at `http://127.0.0.1:8000` and Vite at `http://localhost:5173`, then opens the dashboard.

Keep the launcher Terminal window open while demonstrating. Press **Ctrl+C** in that window to stop both servers.

### Pages and local addresses

- Dashboard: http://localhost:5173
- API documentation: http://127.0.0.1:8000/docs
- API health: http://127.0.0.1:8000/api/health
- Building summary: http://127.0.0.1:8000/api/summary
- GeoJSON features: http://127.0.0.1:8000/api/buildings
- CSV export: http://127.0.0.1:8000/api/export.csv
- Earth Engine tile metadata: http://127.0.0.1:8000/api/layers

## Data directory

The local project expects these files under `data/`:

| File | Purpose | Required for |
|---|---|---|
| `Kernel_T_Statistic.tif` | PWTT continuous building-change raster | Building scoring; dashboard data creation |
| `Kernel_Damage_Mask.tif` | PWTT package damage-mask band | Additional raster evidence / review |
| `buildings.geojson` | OSM building polygons | Building scoring |
| `scored_buildings.geojson` | Per-building mean/max T, valid pixel count, screening status | Dashboard, map and CSV |

The uploaded ZIP cannot contain your local raster and GeoJSON outputs because those files were generated on your Mac and were not attached as actual files in this chat. The archive includes a `data/.gitkeep` placeholder only. **When extracting over your existing project, do not delete your current `data/` folder.**

## Refresh / rebuild the analysis

After the unified environment has been created by `START_MAC.command`, run:

```bash
./UPDATE_ANALYSIS.command
```

This runs the local pipeline in order:

1. Run the PWTT engine and attempt to download `T_statistic` and `damage` directly into `data/` if the T-statistic raster is missing.
2. If a direct Earth Engine download is too large or unavailable, submit fallback Drive exports.
3. Download available OSM building footprints if `buildings.geojson` is missing.
4. Run zonal statistics and write `data/scored_buildings.geojson`.

To force a fresh PWTT computation even if a T-statistic raster already exists:

```bash
FORCE_PWTT=1 ./scripts/run_pipeline.sh
```

To refresh the OpenStreetMap footprints too:

```bash
REFRESH_BUILDINGS=1 ./scripts/run_pipeline.sh
```

Earth Engine's `Image.getDownloadURL` is intended for small downloads and documents a maximum request size of 32 MB and maximum grid dimension of 10,000. If a local download exceeds that limit, the script uses the Drive-export fallback; wait for the Earth Engine task to complete and put the downloaded GeoTIFFs in `data/` before rerunning the pipeline. See the [Earth Engine download API](https://developers.google.com/earth-engine/apidocs/ee-image-getdownloadurl).

## Configuration

Edit the root `.env` file:

```dotenv
EE_PROJECT_ID=battle-damage-assessment
DATA_DIR=data
DEFAULT_THRESHOLD=3.3
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
EE_EXPORT_FOLDER=KernelBDA
```

- `EE_PROJECT_ID`: your registered Google Cloud / Earth Engine project ID.
- `DATA_DIR`: local directory containing the GeoJSON and GeoTIFF files.
- `DEFAULT_THRESHOLD`: building-level mean-T screening threshold used in the dashboard and summary API. `3.3` is the current project setting, not a universal calibrated threshold.
- `EE_EXPORT_FOLDER`: Google Drive folder used by New Assessment exports and fallback exports.

Earth Engine credentials are stored in your user account, not in this project. They are never bundled into the ZIP. If required, choose the active environment (`.venv-pwtt` when present, otherwise `.venv`) and authenticate:

```bash
ENV_DIR=.venv-pwtt; [ -x "$ENV_DIR/bin/earthengine" ] || ENV_DIR=.venv
"$ENV_DIR/bin/earthengine" authenticate
"$ENV_DIR/bin/python" -c "import ee; ee.Initialize(project='battle-damage-assessment'); print(ee.Number(1).getInfo())"
```

## Method details and important distinctions

- The project's current example uses Bakhmut bounds `37.949421, 48.556181, 38.043834, 48.621584`.
- The configured reference cutoff is `2022-02-22`, with a 12-month pre-event reference window (`2021-02-22` to `2022-02-22`).
- The configured inference window starts `2024-07-01` and spans one month (`2024-07-01` to `2024-08-01`). It is not an image captured immediately after the February 2022 event.
- The installed PWTT package groups Sentinel-1 GRD FLOAT observations by relative orbit, filters VV/VH, applies its Lee filter, log-transforms the backscatter and computes absolute two-sample T-statistics. It returns `T_statistic`, `damage`, `p_value`, `n_pre` and `n_post` bands.
- The installed package source shown in the working session defines its raster `damage` band using `t_smooth > 3`. The dashboard's building-level screening default of `mean_t > 3.3` is a separate, configurable project choice. Do not treat these thresholds as interchangeable.
- Building scores are zonal summaries over the T-statistic raster. Footprint coverage varies by OpenStreetMap mapping completeness and by raster overlap; a building with no valid pixels is marked `No raster data`, not `undamaged`.
- The before/after page displays median SAR context composites over the matching configured date windows. It is a visual comparison layer; the PWTT calculation itself uses the installed package's orbit-specific calculation. The slider reveals the inference-period composite and PWTT layer over the pre-event composite.

## Technology

- Sentinel-1 GRD FLOAT via Google Earth Engine
- Published `pwtt` Python package
- Python 3.11, GeoPandas, Rasterio, Rasterstats, OSMnx
- FastAPI + Uvicorn
- React 18 + Vite + React Leaflet + Leaflet

## Local development without the launcher

Backend:

```bash
ENV_DIR=.venv-pwtt; [ -x "$ENV_DIR/bin/python" ] || ENV_DIR=.venv
"$ENV_DIR/bin/python" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend in another Terminal:

```bash
cd frontend
npm run dev
```

## Limitations

- OSM building footprints are not complete everywhere; missing outlines are not evidence of no building or no damage.
- Sentinel-1 pixels are approximately 10 m native spacing; many small buildings can cover only a few pixels.
- Spatial spillover, non-damage land-surface changes, vegetation and other factors can produce false positives.
- The current threshold has not been calibrated by the project team against independent local damage labels. Do not quote the paper's aggregate AUC/F1 values as KERNEL's measured accuracy.
- The app is a local hackathon prototype. It does not include user authentication, a production database, multi-user task queues, or automatic field verification.

## References and attribution

- Ballinger, O. (2025), *Open access battle damage detection via Pixel-Wise T-Test on Sentinel-1 imagery*, Remote Sensing of Environment 331, 115025. https://doi.org/10.1016/j.rse.2025.115025
- Published PWTT implementation: https://github.com/oballinger/PWTT
- Google Earth Engine Sentinel-1 GRD collection: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD
- Google Earth Engine image download API and limits: https://developers.google.com/earth-engine/apidocs/ee-image-getdownloadurl
- OpenStreetMap data contributors: https://www.openstreetmap.org/copyright
