"""Ansible action provider for host configuration, database restore, and smoke testing."""

from __future__ import annotations

from pathlib import Path

from ..config import OrchestratorConfig
from ..interfaces import AuditLogger, FailoverState
from .runner import SubprocessRunner


class AnsibleAction:
    """Manages Ansible execution for configuration, restore, and validation."""

    def __init__(
        self,
        config: OrchestratorConfig,
        repo_root: Path | None = None,
        runner: SubprocessRunner | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self.config = config
        self.repo_root = repo_root or Path(__file__).resolve().parents[4]
        self.runner = runner or SubprocessRunner(audit=audit, dry_run=config.dry_run)
        self.audit = audit

    def configure(self) -> bool:
        """Run make dr-configure."""
        cmd = ["make", "dr-configure"]
        res = self.runner.run(
            args=cmd,
            cwd=self.repo_root,
            timeout_seconds=900.0,
            current_state=FailoverState.PROVISIONING,
        )
        return res.success

    def restore_database(self) -> bool:
        """Run make dr-restore."""
        cmd = ["make", "dr-restore"]
        res = self.runner.run(
            args=cmd,
            cwd=self.repo_root,
            timeout_seconds=600.0,
            current_state=FailoverState.RESTORING,
        )
        return res.success

    def smoke_test(self) -> bool:
        """Run make dr-test."""
        cmd = ["make", "dr-test"]
        res = self.runner.run(
            args=cmd,
            cwd=self.repo_root,
            timeout_seconds=300.0,
            current_state=FailoverState.TESTING,
        )
        return res.success
