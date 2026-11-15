#!/bin/bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [[ ! -x .venv-pwtt/bin/python && ! -x .venv/bin/python ]]; then
  echo "Run START_MAC.command once first to install dependencies."
  exit 1
fi
./scripts/run_pipeline.sh
read -r -p "Press Enter to close..."
