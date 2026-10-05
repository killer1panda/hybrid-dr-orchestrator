"""Decoupled Terraform CLI automation runner with structured outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ..interfaces import AuditLogger, FailoverState
from .runner import SubprocessRunner


@dataclass
class TerraformExecutionResult:
    """Structured result of a Terraform CLI invocation."""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    outputs: dict[str, Any] = field(default_factory=dict)


class TerraformRunner:
    """Production-grade Terraform CLI runner providing structured I/O and dry-run safety."""

    def __init__(
        self,
        working_dir: str | Path,
        dry_run: bool = True,
        audit: AuditLogger | None = None,
        runner: SubprocessRunner | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.working_dir = Path(working_dir)
        self.dry_run = dry_run
        self.audit = audit
        self.runner = runner or SubprocessRunner(audit=audit, dry_run=dry_run)
        self.env = env

    def init(self) -> TerraformExecutionResult:
        """Execute terraform init."""
        cmd = ["terraform", "init", "-input=false"]
        res = self.runner.run(
            args=cmd,
            cwd=self.working_dir,
            env=self.env,
            timeout_seconds=300.0,
            current_state=FailoverState.PROVISIONING,
        )
        return TerraformExecutionResult(
            success=res.success,
            returncode=res.returncode,
            stdout=res.stdout,
            stderr=res.stderr,
            duration_s=res.duration_s,
        )

    def plan(self, var_file: str | Path | None = None) -> TerraformExecutionResult:
        """Execute terraform plan."""
        cmd = ["terraform", "plan", "-input=false"]
        if var_file:
            cmd.extend(["-var-file", str(var_file)])
        res = self.runner.run(
            args=cmd,
            cwd=self.working_dir,
            env=self.env,
            timeout_seconds=300.0,
            current_state=FailoverState.PROVISIONING,
        )
        return TerraformExecutionResult(
            success=res.success,
            returncode=res.returncode,
            stdout=res.stdout,
            stderr=res.stderr,
            duration_s=res.duration_s,
        )

    def apply(self, var_file: str | Path | None = None) -> TerraformExecutionResult:
        """Execute terraform apply -auto-approve -input=false and capture outputs."""
        cmd = ["terraform", "apply", "-auto-approve", "-input=false"]
        if var_file:
            cmd.extend(["-var-file", str(var_file)])
        res = self.runner.run(
            args=cmd,
            cwd=self.working_dir,
            env=self.env,
            timeout_seconds=900.0,
            current_state=FailoverState.PROVISIONING,
        )
        outputs: dict[str, Any] = {}
        if res.success:
            outputs = self.output()

        return TerraformExecutionResult(
            success=res.success,
            returncode=res.returncode,
            stdout=res.stdout,
            stderr=res.stderr,
            duration_s=res.duration_s,
            outputs=outputs,
        )

    def output(self) -> dict[str, Any]:
        """Fetch and parse terraform output -json."""
        if self.dry_run:
            return {
                "replica_public_ip": {"value": "15.135.65.200", "type": "string"},
                "health_check_url": {
                    "value": "http://15.135.65.200:8000/healthz",
                    "type": "string",
                },
                "r53_record_fqdn": {"value": "app.dr-lab.internal", "type": "string"},
            }

        cmd = ["terraform", "output", "-json"]
        res = self.runner.run(
            args=cmd,
            cwd=self.working_dir,
            env=self.env,
            timeout_seconds=60.0,
            current_state=FailoverState.PROVISIONING,
        )
        if not res.success or not res.stdout.strip():
            return {}

        try:
            parsed: dict[str, Any] = json.loads(res.stdout)
            return parsed
        except json.JSONDecodeError:
            return {}

    def destroy(self, var_file: str | Path | None = None) -> TerraformExecutionResult:
        """Execute terraform destroy -auto-approve -input=false."""
        cmd = ["terraform", "destroy", "-auto-approve", "-input=false"]
        if var_file:
            cmd.extend(["-var-file", str(var_file)])
        res = self.runner.run(
            args=cmd,
            cwd=self.working_dir,
            env=self.env,
            timeout_seconds=900.0,
            current_state=FailoverState.COMPLETED,
        )
        return TerraformExecutionResult(
            success=res.success,
            returncode=res.returncode,
            stdout=res.stdout,
            stderr=res.stderr,
            duration_s=res.duration_s,
        )
