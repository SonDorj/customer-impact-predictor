# [AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]
param([string]$PythonCommand = "python", [string]$JavaHome = $env:JAVA_HOME)
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    & $PythonCommand scripts/check_runtime.py
    if ($LASTEXITCODE -ne 0) { throw "Python 3.14 is required." }
    if (!(Test-Path ".venv\Scripts\python.exe")) {
        & $PythonCommand -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
    }
    & ".\.venv\Scripts\python.exe" scripts/check_runtime.py
    if ($LASTEXITCODE -ne 0) { throw "Existing virtual environment is not Python 3.14." }
    & ".\.venv\Scripts\python.exe" -m pip install -r requirements-api.lock.txt
    if ($LASTEXITCODE -ne 0) { throw "Locked dependency installation failed." }
    & ".\springboot-service\build.ps1" -JavaHome $JavaHome
    if ($LASTEXITCODE -ne 0) { throw "Spring Boot build failed." }
} finally {
    Pop-Location
}
Write-Output "Setup complete. Start inference and Spring Boot in separate terminals."
