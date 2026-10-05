@echo off
setlocal
set PYTHONPATH=%~dp0orchestrator\src
if "%1"=="--live" (
    echo ==> Launching LIVE DR Drill with AWS provisioning...
    "%~dp0orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli --i-understand-this-provisions-aws drill
) else (
    echo ==> Launching Simulated DR Drill [dry-run mode]...
    "%~dp0orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli drill --dry-run
)
endlocal
