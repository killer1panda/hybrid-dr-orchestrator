$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\orchestrator\src"
Write-Host "Starting Mission Control Web Dashboard on http://localhost:8500 ..." -ForegroundColor Cyan
& "$PSScriptRoot\orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli dashboard --host 127.0.0.1 --port 8500
