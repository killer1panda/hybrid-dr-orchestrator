"""Unit tests for the AWS Step Functions ASL validator and simulator."""

import json
from pathlib import Path

import pytest

from hybrid_dr.step_functions import AslValidationError, StepFunctionsSimulator


def test_asl_default_definition_loads_and_validates() -> None:
    simulator = StepFunctionsSimulator()
    assert simulator.definition is not None
    assert simulator.definition["StartAt"] == "EvaluateQuorum"
    assert "LaunchReplicaCompute" in simulator.definition["States"]
    assert "FailedNeedsHuman" in simulator.definition["States"]


def test_asl_validation_missing_file(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        StepFunctionsSimulator(definition_path=non_existent)


def test_asl_validation_invalid_json(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(AslValidationError, match="Invalid JSON"):
        StepFunctionsSimulator(definition_path=bad_file)


def test_asl_validation_missing_keys(tmp_path: Path) -> None:
    incomplete_file = tmp_path / "incomplete.json"
    incomplete_file.write_text(json.dumps({"Comment": "test"}), encoding="utf-8")
    with pytest.raises(AslValidationError, match="missing 'StartAt' or 'States'"):
        StepFunctionsSimulator(definition_path=incomplete_file)


def test_asl_validation_missing_start_at(tmp_path: Path) -> None:
    bad_start = tmp_path / "bad_start.json"
    bad_start.write_text(
        json.dumps({"StartAt": "NonExistent", "States": {"StateA": {"Type": "Succeed"}}}),
        encoding="utf-8",
    )
    with pytest.raises(AslValidationError, match="StartAt state 'NonExistent' does not exist"):
        StepFunctionsSimulator(definition_path=bad_start)


def test_asl_validation_invalid_next(tmp_path: Path) -> None:
    bad_next = tmp_path / "bad_next.json"
    bad_next.write_text(
        json.dumps(
            {
                "StartAt": "StateA",
                "States": {
                    "StateA": {"Type": "Task", "Next": "GhostState"},
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AslValidationError, match="non-existent Next state 'GhostState'"):
        StepFunctionsSimulator(definition_path=bad_next)


def test_asl_validation_invalid_catch_next(tmp_path: Path) -> None:
    bad_catch = tmp_path / "bad_catch.json"
    bad_catch.write_text(
        json.dumps(
            {
                "StartAt": "StateA",
                "States": {
                    "StateA": {
                        "Type": "Task",
                        "Next": "StateB",
                        "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "GhostHandler"}],
                    },
                    "StateB": {"Type": "Succeed"},
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AslValidationError, match="references non-existent state 'GhostHandler'"):
        StepFunctionsSimulator(definition_path=bad_catch)


def test_simulation_happy_path() -> None:
    simulator = StepFunctionsSimulator()
    path = simulator.simulate(mock_disaster=True, mock_smoke_pass=True)

    expected = [
        "EvaluateQuorum",
        "IsDisasterConfirmed",
        "AcquireFencingLock",
        "NotifyFencingComplete",
        "LaunchReplicaCompute",
        "WaitForReplicaReady",
        "ExecuteDataRestore",
        "ExecuteSmokeTests",
        "AreSmokeTestsPassing",
        "ExecuteDnsCutover",
        "FailoverCompleted",
    ]
    assert path == expected


def test_simulation_false_alarm_aborts() -> None:
    simulator = StepFunctionsSimulator()
    path = simulator.simulate(mock_disaster=False)

    expected = [
        "EvaluateQuorum",
        "IsDisasterConfirmed",
        "QuorumHealthNormal",
    ]
    assert path == expected


def test_simulation_smoke_test_failure_escalates() -> None:
    simulator = StepFunctionsSimulator()
    path = simulator.simulate(mock_disaster=True, mock_smoke_pass=False)

    expected = [
        "EvaluateQuorum",
        "IsDisasterConfirmed",
        "AcquireFencingLock",
        "NotifyFencingComplete",
        "LaunchReplicaCompute",
        "WaitForReplicaReady",
        "ExecuteDataRestore",
        "ExecuteSmokeTests",
        "AreSmokeTestsPassing",
        "FailedNeedsHuman",
    ]
    assert path == expected


def test_simulation_injected_provisioning_error_triggers_catch() -> None:
    simulator = StepFunctionsSimulator()
    path = simulator.simulate(
        mock_disaster=True,
        mock_smoke_pass=True,
        inject_error_at="LaunchReplicaCompute",
    )

    expected = [
        "EvaluateQuorum",
        "IsDisasterConfirmed",
        "AcquireFencingLock",
        "NotifyFencingComplete",
        "LaunchReplicaCompute",
        "FailedNeedsHuman",
    ]
    assert path == expected
