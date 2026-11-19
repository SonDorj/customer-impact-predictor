# [AI-GENERATED CONTENT BY AIFEL TEAM ASSISTANT :: AIFEL-AI-LABEL-V1]
param(
    [string]$JavaHome = $env:JAVA_HOME,
    [ValidateSet("test", "package")][string]$Goal = "package"
)
$ErrorActionPreference = "Stop"
if ($JavaHome) { $env:JAVA_HOME = $JavaHome }
Push-Location $PSScriptRoot
try {
    & ".\mvnw.cmd" -B -ntp -s maven-settings.xml $Goal
    $result = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $result
