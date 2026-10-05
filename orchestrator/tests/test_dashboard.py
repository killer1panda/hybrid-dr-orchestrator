"""Tests for the Hybrid DR Orchestrator Web Dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from hybrid_dr.config import OrchestratorConfig
from hybrid_dr.dashboard import create_dashboard_app
from hybrid_dr.interfaces import FailoverState
from hybrid_dr.state_machine import FileStateStorage


def test_dashboard_index_renders_html(tmp_path: Path) -> None:
    """Ensure the root dashboard endpoint returns the Mission Control HTML."""
    cfg = OrchestratorConfig(
        state_file=str(tmp_path / "state.json"),
        audit_log_file=str(tmp_path / "audit.jsonl"),
        lock_file=str(tmp_path / "lock.lock"),
        dry_run=True,
    )
    app = create_dashboard_app(cfg)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert "HYBRID CLOUD DR" in response.text
    assert "MISSION CONTROL" in response.text
    assert "State Machine Lifecycle" in response.text


def test_dashboard_api_status_reports_correct_fields(tmp_path: Path) -> None:
    """Verify that /api/status returns valid telemetry structure."""
    state_file = tmp_path / "state.json"
    storage = FileStateStorage(str(state_file))
    storage.save(FailoverState.IDLE)

    cfg = OrchestratorConfig(
        state_file=str(state_file),
        audit_log_file=str(tmp_path / "audit.jsonl"),
        lock_file=str(tmp_path / "lock.lock"),
        dry_run=True,
    )
    app = create_dashboard_app(cfg)
    client = TestClient(app)

    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "IDLE"
    assert data["dry_run"] is True
    assert "signals" in data
    assert "quorum" in data
    assert "benchmarks" in data
    assert data["benchmarks"]["sla_rpo_budget_seconds"] == 300
    assert data["costs"]["standing_compute_usd"] == 0.00


def test_dashboard_maintenance_toggle(tmp_path: Path) -> None:
    """Verify that /api/maintenance updates the orchestrator setting."""
    cfg = OrchestratorConfig(
        state_file=str(tmp_path / "state.json"),
        audit_log_file=str(tmp_path / "audit.jsonl"),
        lock_file=str(tmp_path / "lock.lock"),
        maintenance_mode=False,
    )
    app = create_dashboard_app(cfg)
    client = TestClient(app)

    # Enable maintenance
    res = client.post("/api/maintenance", json={"enabled": True})
    assert res.status_code == 200
    assert res.json()["maintenance_mode"] is True

    # Check status reflects update
    res2 = client.get("/api/status")
    assert res2.json()["maintenance_mode"] is True


def test_dashboard_drill_trigger_dry_run(tmp_path: Path) -> None:
    """Verify that /api/drill accepts dry run triggers."""
    cfg = OrchestratorConfig(
        state_file=str(tmp_path / "state.json"),
        audit_log_file=str(tmp_path / "audit.jsonl"),
        lock_file=str(tmp_path / "lock.lock"),
        dry_run=True,
    )
    app = create_dashboard_app(cfg)
    client = TestClient(app)

    res = client.post("/api/drill", json={"dry_run": True})
    assert res.status_code == 200
    assert res.json()["status"] == "started"


def test_dashboard_failback_resets_state(tmp_path: Path) -> None:
    """Verify that /api/failback resets state storage to IDLE."""
    state_file = tmp_path / "state.json"
    storage = FileStateStorage(str(state_file))
    storage.save(FailoverState.COMPLETED)

    cfg = OrchestratorConfig(
        state_file=str(state_file),
        audit_log_file=str(tmp_path / "audit.jsonl"),
        lock_file=str(tmp_path / "lock.lock"),
        dry_run=True,
    )
    app = create_dashboard_app(cfg)
    client = TestClient(app)

    res = client.post("/api/failback")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert storage.load() == FailoverState.IDLE
