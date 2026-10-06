@echo off
set PYTHONPATH=%~dp0orchestrator\src
"%~dp0orchestrator\venv\Scripts\python.exe" -m hybrid_dr.cli status
