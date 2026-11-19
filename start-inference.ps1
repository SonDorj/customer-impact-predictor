# [AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]
param([int]$Port = 8181, [string]$RunName = "run-001")
$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) { throw "Run setup.ps1 first to create the Windows virtual environment." }
$env:OPENBLAS_NUM_THREADS = "2"
$env:OMP_NUM_THREADS = "2"
$env:IMPACT_RUN_NAME = $RunName
Push-Location $PSScriptRoot
try {
    & $python -m uvicorn impact_predictor.api:app --host 127.0.0.1 `
        --port $Port --workers 1 --no-access-log
    $result = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $result
