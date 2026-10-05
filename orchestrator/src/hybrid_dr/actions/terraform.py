"""Terraform action provider for provisioning ephemeral AWS DR environment."""

from __future__ import annotations

from pathlib import Path

from ..config import OrchestratorConfig
from ..interfaces import AuditLogger, FailoverState
from .runner import SubprocessRunner


class TerraformAction:
    """Manages ephemeral Terraform lifecycle."""

    def __init__(
        self,
        config: OrchestratorConfig,
        repo_root: Path | None = None,
        runner: SubprocessRunner | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self.config = config
        self.repo_root = repo_root or Path(__file__).resolve().parents[4]
        self.tf_dir = self.repo_root / "infra" / "aws" / "envs" / "dr"
        self.runner = runner or SubprocessRunner(audit=audit, dry_run=config.dry_run)
        self.audit = audit

    def provision(self) -> bool:
        """Run make dr-up or terraform apply."""
        cmd = ["make", "dr-up"]
        res = self.runner.run(
            args=cmd,
            cwd=self.repo_root,
            timeout_seconds=600.0,
            current_state=FailoverState.PROVISIONING,
        )
        return res.success

    def teardown(self) -> bool:
        """Run make dr-down or terraform destroy."""
        cmd = ["make", "dr-down"]
        res = self.runner.run(
            args=cmd,
            cwd=self.repo_root,
            timeout_seconds=600.0,
            current_state=FailoverState.COMPLETED,
        )
        return res.success
