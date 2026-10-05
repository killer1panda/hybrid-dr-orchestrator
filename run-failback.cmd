@echo off
setlocal
set PYTHONPATH=%~dp0orchestrator\src
echo ==> Executing Reverse Failback and Cloud Teardown...
"%~dp0orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli failback
endlocal
