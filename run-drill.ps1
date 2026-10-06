param(
    [switch]$Live = $false
)
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\orchestrator\src"

if ($Live) {
    Write-Host "==> Launching LIVE DR Drill with AWS provisioning..." -ForegroundColor Yellow
    & "$PSScriptRoot\orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli --i-understand-this-provisions-aws drill
} else {
    Write-Host "==> Launching Simulated DR Drill (dry-run mode)..." -ForegroundColor Cyan
    & "$PSScriptRoot\orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli drill --dry-run
}
