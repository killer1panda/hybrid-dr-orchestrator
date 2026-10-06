$ErrorActionPreference = "Stop"
Write-Host "==> Starting Mock On-Premises 3-Tier Cluster on http://localhost:8080 ..." -ForegroundColor Cyan
& "$PSScriptRoot\orchestrator\venv\Scripts\python.exe" "$PSScriptRoot\scripts\mock_onprem_service.py" --host 127.0.0.1 --port 8080
