#!/usr/bin/env bash
# [AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]
set -euo pipefail
cd "$(dirname "$0")"
JAVA=java
if [ -n "${JAVA_HOME:-}" ]; then JAVA="$JAVA_HOME/bin/java"; fi
JAR=springboot-service/target/customer-impact-service-0.1.0.jar
if [ ! -f "$JAR" ]; then
    printf 'Build with bash setup.sh before starting the backend.\n' >&2
    exit 1
fi
exec "$JAVA" -XX:ActiveProcessorCount=2 -Xmx384m -jar "$JAR"
