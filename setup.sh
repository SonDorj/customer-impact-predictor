#!/usr/bin/env bash
# [AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
"$PYTHON" scripts/check_runtime.py
if [ ! -x .venv/bin/python ]; then
    "$PYTHON" -m venv .venv
fi
.venv/bin/python scripts/check_runtime.py
.venv/bin/python -m pip install -r requirements-api.lock.txt
(
    cd springboot-service
    ./mvnw -B -ntp -s maven-settings.xml package
)
printf '\nSetup complete. Start inference and Spring Boot in separate terminals.\n'
