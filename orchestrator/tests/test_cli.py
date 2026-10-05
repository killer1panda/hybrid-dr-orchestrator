"""Unit tests for the CLI entrypoint."""

from pathlib import Path

from hybrid_dr.cli import main
from hybrid_dr.interfaces import FailoverState
from hybrid_dr.state_machine import FileStateStorage


def test_cli_drill_dry_run(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    audit_file = tmp_path / "audit.jsonl"
    config_file = tmp_path / "test_config.yaml"

    config_file.write_text(
        f"""
dry_run: true
state_file: "{state_file}"
audit_log_file: "{audit_file}"
""",
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config_file), "drill", "--dry-run"])
    assert exit_code == 0

    storage = FileStateStorage(state_file)
    assert storage.load() == FailoverState.COMPLETED
    assert audit_file.exists()


def test_cli_failback_resets_state(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    audit_file = tmp_path / "audit.jsonl"
    config_file = tmp_path / "test_config.yaml"

    storage = FileStateStorage(state_file)
    storage.save(FailoverState.COMPLETED)

    config_file.write_text(
        f"""
dry_run: true
state_file: "{state_file}"
audit_log_file: "{audit_file}"
""",
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config_file), "failback"])
    assert exit_code == 0
    assert storage.load() == FailoverState.IDLE
