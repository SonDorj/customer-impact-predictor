# [AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]
param(
    [string]$JavaHome = $env:JAVA_HOME,
    [int]$Port = 8180,
    [string]$InferenceBaseUrl = "http://127.0.0.1:8181"
)
$ErrorActionPreference = "Stop"
$java = if ($JavaHome) { Join-Path $JavaHome "bin\java.exe" } else { "java" }
$jar = Join-Path $PSScriptRoot "target\customer-impact-service-0.1.0.jar"
if (!(Test-Path $jar)) { throw "Run build.ps1 before starting the backend." }
& $java -XX:ActiveProcessorCount=2 -Xmx384m -jar $jar `
    "--server.address=127.0.0.1" "--server.port=$Port" `
    "--impact.inference.base-url=$InferenceBaseUrl"
exit $LASTEXITCODE
