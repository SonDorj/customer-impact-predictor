#!/usr/bin/env bash
# [AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    printf 'Run bash setup.sh with Python 3.14 and JDK 21 first.\n' >&2
    exit 1
fi
exec env OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 \
    .venv/bin/python -m uvicorn impact_predictor.api:app \
    --host 127.0.0.1 --port "${IMPACT_PORT:-8181}" --workers 1 --no-access-log
