#!/bin/bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi
if [[ -x "$ROOT/.venv-pwtt/bin/python" ]]; then
  PY="$ROOT/.venv-pwtt/bin/python"
else
  PY="$ROOT/.venv/bin/python"
fi

if [[ ! -x "$PY" ]]; then
  echo "Python environment missing. Run ./START_MAC.command first."
  exit 1
fi

if [[ ! -f data/Kernel_T_Statistic.tif || "${FORCE_PWTT:-0}" == "1" ]]; then
  echo "[1/3] Running Sentinel-1 PWTT and downloading the raster outputs..."
  "$PY" satellite-engine/run_pwtt.py --drive-fallback
fi

if [[ ! -f data/Kernel_T_Statistic.tif ]]; then
  echo "The T-statistic raster is not present yet. If the script submitted Google Drive export tasks, wait for them to complete and download Kernel_T_Statistic.tif and Kernel_Damage_Mask.tif into data/."
  exit 2
fi

if [[ ! -f data/buildings.geojson || "${REFRESH_BUILDINGS:-0}" == "1" ]]; then
  echo "[2/3] Downloading available OpenStreetMap building footprints..."
  "$PY" satellite-engine/buildings.py
else
  echo "[2/3] Reusing data/buildings.geojson"
fi

echo "[3/3] Calculating building-level PWTT summaries..."
"$PY" satellite-engine/score_buildings.py --threshold "${DEFAULT_THRESHOLD:-3.3}"
echo "Pipeline finished. Output: data/scored_buildings.geojson"
