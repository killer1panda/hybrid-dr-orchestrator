"""Local validator and execution simulator for AWS Step Functions ASL definitions.

Allows deterministic, offline verification of the enterprise disaster recovery
workflow without incurring AWS cloud spend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AslValidationError(Exception):
    """Raised when an ASL state machine definition fails structural validation."""


class StepFunctionsSimulator:
    """Simulates the execution of the Hybrid DR Step Functions state machine."""

    def __init__(self, definition_path: str | Path | None = None) -> None:
        if definition_path is None:
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            definition_path = (
                repo_root
                / "infra"
                / "aws"
                / "modules"
                / "step-functions"
                / "asl"
                / "hybrid_dr_state_machine.json"
            )

        self.definition_path = Path(definition_path)
        self.definition = self._load_and_validate()

    def _load_and_validate(self) -> dict[str, Any]:
        """Load and validate the ASL definition structure."""
        if not self.definition_path.exists():
            raise FileNotFoundError(f"ASL file not found at: {self.definition_path}")

        try:
            with open(self.definition_path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        except json.JSONDecodeError as e:
            raise AslValidationError(f"Invalid JSON in ASL definition: {e}") from e

        if "StartAt" not in data or "States" not in data:
            raise AslValidationError("ASL definition missing 'StartAt' or 'States' keys.")

        states: dict[str, Any] = data["States"]
        start_at: str = data["StartAt"]

        if start_at not in states:
            raise AslValidationError(f"StartAt state '{start_at}' does not exist in States.")

        # Validate that all Next states exist
        for state_name, state_def in states.items():
            if not isinstance(state_def, dict):
                raise AslValidationError(f"State '{state_name}' definition must be an object.")

            state_type = state_def.get("Type")
            if not state_type:
                raise AslValidationError(f"State '{state_name}' missing 'Type'.")

            if "Next" in state_def:
                next_state = state_def["Next"]
                if next_state not in states:
                    raise AslValidationError(
                        f"State '{state_name}' has non-existent Next state '{next_state}'."
                    )

            if "Catch" in state_def:
                for catch_block in state_def["Catch"]:
                    catch_next = catch_block.get("Next")
                    if catch_next not in states:
                        raise AslValidationError(
                            f"State '{state_name}' catch handler references "
                            f"non-existent state '{catch_next}'."
                        )

        return data

    def simulate(
        self,
        mock_disaster: bool = True,
        mock_smoke_pass: bool = True,
        inject_error_at: str | None = None,
    ) -> list[str]:
        """Simulate an end-to-end execution of the state machine.

        Returns the list of state names visited in order.
        """
        states: dict[str, Any] = self.definition["States"]
        current_state_name: str | None = self.definition["StartAt"]
        execution_path: list[str] = []

        context: dict[str, Any] = {
            "QuorumResult": {"Payload": {"DisasterConfirmed": mock_disaster}},
            "ComputeResult": {
                "Payload": {
                    "InstanceIp": "15.135.65.200",
                    "HealthUrl": "http://15.135.65.200:8000/healthz",
                }
            },
            "SmokeTestResult": {"Payload": {"Passed": mock_smoke_pass}},
        }

        while current_state_name:
            execution_path.append(current_state_name)
            state_def = states[current_state_name]
            state_type = state_def["Type"]

            # Error injection
            if inject_error_at == current_state_name:
                if "Catch" in state_def:
                    current_state_name = state_def["Catch"][0]["Next"]
                    continue
                else:
                    break

            if state_type == "Task":
                current_state_name = state_def.get("Next")

            elif state_type == "Choice":
                choices = state_def.get("Choices", [])
                matched = False
                for choice in choices:
                    var_path = choice["Variable"]
                    bool_val = choice.get("BooleanEquals")
                    if var_path == "$.QuorumResult.Payload.DisasterConfirmed":
                        if context["QuorumResult"]["Payload"]["DisasterConfirmed"] == bool_val:
                            current_state_name = choice["Next"]
                            matched = True
                            break
                    elif var_path == "$.SmokeTestResult.Payload.Passed":
                        if context["SmokeTestResult"]["Payload"]["Passed"] == bool_val:
                            current_state_name = choice["Next"]
                            matched = True
                            break

                if not matched:
                    current_state_name = state_def.get("Default")

            elif state_type == "Wait":
                current_state_name = state_def.get("Next")

            elif state_type in ("Succeed", "Fail"):
                current_state_name = None

        return execution_path
