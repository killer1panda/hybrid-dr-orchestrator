$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\orchestrator\src"
Write-Host "==> Executing Reverse Failback & Cloud Teardown..." -ForegroundColor Cyan
& "$PSScriptRoot\orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli failback
