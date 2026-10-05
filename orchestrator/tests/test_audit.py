"""Unit tests for JsonlAuditLogger and FileStateStorage."""

import json
from pathlib import Path

from conftest import MockClock

from hybrid_dr.audit import JsonlAuditLogger
from hybrid_dr.interfaces import FailoverState
from hybrid_dr.state_machine import FileStateStorage


def test_jsonl_audit_logger_format(tmp_path: Path, mock_clock: MockClock) -> None:
    log_file = tmp_path / "audit.jsonl"
    logger = JsonlAuditLogger(log_file, run_id="test-run-123", clock=mock_clock)

    logger.log("SAMPLE_EVENT", FailoverState.FENCING, {"probe": "healthy"})

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])

    assert entry["run_id"] == "test-run-123"
    assert entry["event"] == "SAMPLE_EVENT"
    assert entry["state"] == "FENCING"
    assert entry["details"]["probe"] == "healthy"
    assert "ts_utc" in entry
    assert "monotonic_s" in entry


def test_file_state_storage_atomic_save_and_load(tmp_path: Path) -> None:
    state_file = tmp_path / "dr_state.json"
    storage = FileStateStorage(state_file)

    assert storage.load() == FailoverState.IDLE

    storage.save(FailoverState.PROVISIONING)
    assert storage.load() == FailoverState.PROVISIONING

    storage.save(FailoverState.COMPLETED)
    assert storage.load() == FailoverState.COMPLETED
