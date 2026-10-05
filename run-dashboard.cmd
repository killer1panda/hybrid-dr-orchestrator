@echo off
set PATH=C:\Program Files\Git\bin;C:\MinGW\bin;%PATH%
set PYTHONPATH=%~dp0orchestrator\src
echo Starting Mission Control Web Dashboard on http://localhost:8500 ...
"%~dp0orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli dashboard --host 127.0.0.1 --port 8500
