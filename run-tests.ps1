$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\orchestrator"
try {
    Write-Host "==> Running Pytest Suite (Unit, Integration and Property Tests)..." -ForegroundColor Cyan
    & "$PSScriptRoot\orchestrator\venv\Scripts\pytest.exe" -v tests

    Write-Host "`n==> Running Mypy Strict Type Checks..." -ForegroundColor Cyan
    & "$PSScriptRoot\orchestrator\venv\Scripts\mypy.exe" --config-file pyproject.toml src tests

    Write-Host "`n==> Running Ruff Linting..." -ForegroundColor Cyan
    & "$PSScriptRoot\orchestrator\venv\Scripts\ruff.exe" check src tests

    Write-Host "`n✅ All tests, strict typing, and linting passed!" -ForegroundColor Green
}
finally {
    Pop-Location
}
