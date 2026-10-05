"""Unit tests for the decoupled Terraform CLI runner."""

from pathlib import Path
from unittest.mock import MagicMock

from hybrid_dr.actions.runner import CommandResult, SubprocessRunner
from hybrid_dr.actions.terraform_runner import TerraformRunner


def test_terraform_runner_dry_run_lifecycle(tmp_path: Path) -> None:
    runner = TerraformRunner(working_dir=tmp_path, dry_run=True)

    init_res = runner.init()
    assert init_res.success
    assert init_res.returncode == 0

    plan_res = runner.plan(var_file="test.tfvars")
    assert plan_res.success
    assert plan_res.returncode == 0

    apply_res = runner.apply(var_file="test.tfvars")
    assert apply_res.success
    assert apply_res.returncode == 0
    assert "replica_public_ip" in apply_res.outputs
    assert apply_res.outputs["replica_public_ip"]["value"] == "15.135.65.200"

    out = runner.output()
    assert out["health_check_url"]["value"] == "http://15.135.65.200:8000/healthz"

    destroy_res = runner.destroy()
    assert destroy_res.success
    assert destroy_res.returncode == 0


def test_terraform_runner_real_output_parsing(tmp_path: Path) -> None:
    mock_sub = MagicMock(spec=SubprocessRunner)
    mock_sub.run.return_value = CommandResult(
        returncode=0,
        stdout='{"replica_ip": {"value": "10.0.1.50"}}',
        stderr="",
        duration_s=0.5,
    )

    runner = TerraformRunner(working_dir=tmp_path, dry_run=False, runner=mock_sub)
    out = runner.output()
    assert out == {"replica_ip": {"value": "10.0.1.50"}}


def test_terraform_runner_real_output_invalid_json(tmp_path: Path) -> None:
    mock_sub = MagicMock(spec=SubprocessRunner)
    mock_sub.run.return_value = CommandResult(
        returncode=0,
        stdout="not valid json",
        stderr="",
        duration_s=0.5,
    )

    runner = TerraformRunner(working_dir=tmp_path, dry_run=False, runner=mock_sub)
    out = runner.output()
    assert out == {}


def test_terraform_runner_apply_failure_propagates(tmp_path: Path) -> None:
    mock_sub = MagicMock(spec=SubprocessRunner)
    mock_sub.run.return_value = CommandResult(
        returncode=1,
        stdout="",
        stderr="Error: Invalid provider configuration",
        duration_s=1.2,
    )

    runner = TerraformRunner(working_dir=tmp_path, dry_run=False, runner=mock_sub)
    apply_res = runner.apply()
    assert not apply_res.success
    assert apply_res.returncode == 1
    assert "Invalid provider configuration" in apply_res.stderr
    assert apply_res.outputs == {}
