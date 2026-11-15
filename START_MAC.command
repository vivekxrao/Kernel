#!/bin/bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This launcher is intended for macOS. On another OS, follow README.md."
  exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js and npm are required. Install the macOS ARM64 LTS package from https://nodejs.org/ and run this launcher again."
  exit 1
fi

PYTHON_BIN="$(command -v python3.11 || true)"
if [[ -z "$PYTHON_BIN" && ! -x .venv-pwtt/bin/python && ! -x .venv/bin/python ]]; then
  echo "Python 3.11 was not found. Install it from https://www.python.org/downloads/release/python-3119/ and run this launcher again."
  exit 1
fi

# Reuse the existing PWTT environment from the earlier project setup when it
# exists. It already contains Earth Engine, PWTT and many GIS dependencies.
if [[ -x .venv-pwtt/bin/python ]]; then
  VENV_DIR=".venv-pwtt"
elif [[ -x .venv/bin/python ]]; then
  VENV_DIR=".venv"
else
  VENV_DIR=".venv"
  echo "Creating the unified Python 3.11 environment..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
PY="$ROOT/$VENV_DIR/bin/python"

REQ_HASH="$(shasum -a 256 backend/requirements.txt | awk '{print $1}')"
OLD_HASH="$(cat "$VENV_DIR/.requirements-hash" 2>/dev/null || true)"
if [[ "$REQ_HASH" != "$OLD_HASH" ]]; then
  echo "Installing/updating Python dependencies in $VENV_DIR (first run can take several minutes)..."
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r backend/requirements.txt
  printf '%s' "$REQ_HASH" > "$VENV_DIR/.requirements-hash"
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

mkdir -p logs data
export PYTHONUNBUFFERED=1
export DATA_DIR="${DATA_DIR:-data}"
export EE_PROJECT_ID="${EE_PROJECT_ID:-battle-damage-assessment}"
if "$PY" -c 'import certifi' >/dev/null 2>&1; then
  export SSL_CERT_FILE="$($PY -m certifi)"
  export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
fi

# If the user has the raster but not the scored GeoJSON, complete the local
# footprint aggregation before the API starts. Existing data is never deleted.
if [[ ! -f data/scored_buildings.geojson && -f data/Kernel_T_Statistic.tif ]]; then
  echo "Scored GeoJSON missing; running building download + aggregation..."
  if [[ ! -f data/buildings.geojson ]]; then
    "$PY" satellite-engine/buildings.py
  fi
  "$PY" satellite-engine/score_buildings.py --threshold "${DEFAULT_THRESHOLD:-3.3}"
elif [[ ! -f data/scored_buildings.geojson && ! -f data/Kernel_T_Statistic.tif ]]; then
  echo "No local PWTT raster found. Running the satellite + building pipeline..."
  "$PY" satellite-engine/run_pwtt.py --drive-fallback || true
  if [[ -f data/Kernel_T_Statistic.tif ]]; then
    "$PY" satellite-engine/buildings.py
    "$PY" satellite-engine/score_buildings.py --threshold "${DEFAULT_THRESHOLD:-3.3}"
  else
    echo "Earth Engine may have submitted Drive export tasks. Complete those exports and put the GeoTIFF files in data/, then run ./scripts/run_pipeline.sh."
  fi
fi

# Auth is stored in the user's Earth Engine config directory, not in this ZIP.
if ! "$PY" -c "import ee; ee.Initialize(project='${EE_PROJECT_ID}'); print('Earth Engine credentials OK')" >/dev/null 2>&1; then
  echo "Earth Engine credentials were not available to this Python environment. If satellite comparison or new assessment is needed, run:"
  echo "  $ROOT/$VENV_DIR/bin/earthengine authenticate"
  echo "Your local dashboard and already-downloaded GeoJSON can still run without Earth Engine."
fi

# Start both services; Ctrl+C in this window stops both.
"$PY" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
API_PID=$!
(cd frontend && npm run dev -- --host 127.0.0.1 --port 5173) > logs/frontend.log 2>&1 &
WEB_PID=$!
cleanup() {
  echo "Stopping Kernel services..."
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
  wait "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:5173 >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

open http://localhost:5173 >/dev/null 2>&1 || true

echo ""
echo "KERNEL DAMAGE INTELLIGENCE IS RUNNING"
echo "Dashboard: http://localhost:5173"
echo "API docs:  http://localhost:8000/docs"
echo "Logs:      logs/backend.log and logs/frontend.log"
echo "Press Ctrl+C here to stop both servers."
echo ""
tail -n 20 -f logs/backend.log logs/frontend.log
