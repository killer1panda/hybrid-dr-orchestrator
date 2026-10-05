@echo off
setlocal
echo ==> Running Pytest Suite (Unit, Integration and Property Tests)...
pushd "%~dp0orchestrator"
"%~dp0orchestrator\venv\Scripts\pytest.exe" -v tests
if %ERRORLEVEL% neq 0 (
    popd
    exit /b %ERRORLEVEL%
)

echo.
echo ==> Running Mypy Strict Type Checks...
"%~dp0orchestrator\venv\Scripts\mypy.exe" --config-file pyproject.toml src tests
if %ERRORLEVEL% neq 0 (
    popd
    exit /b %ERRORLEVEL%
)

echo.
echo ==> Running Ruff Linting...
"%~dp0orchestrator\venv\Scripts\ruff.exe" check src tests
if %ERRORLEVEL% neq 0 (
    popd
    exit /b %ERRORLEVEL%
)

popd
echo.
echo [SUCCESS] All tests, strict typing, and linting passed!
endlocal
