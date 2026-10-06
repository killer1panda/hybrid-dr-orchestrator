$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\orchestrator\src"
& "$PSScriptRoot\orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli status
