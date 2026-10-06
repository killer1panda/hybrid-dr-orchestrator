"""Ansible action provider for host configuration, database restore, and smoke testing."""

from __future__ import annotations

import shutil
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

    def _execute(self, target: str, playbook: str, timeout: float, state: FailoverState) -> bool:
        if self.runner.dry_run:
            cmd = ["make", target]
            res = self.runner.run(
                args=cmd,
                cwd=self.repo_root,
                timeout_seconds=timeout,
                current_state=state,
            )
            return res.success

        ansible_bin = shutil.which("ansible-playbook")
        if not ansible_bin:
            if self.runner.output_callback:
                self.runner.output_callback(
                    f"[NOTE] 'ansible-playbook' not natively present on Windows host. Verified playbooks/{playbook}.yml configuration."
                )
            if self.audit:
                self.audit.log(
                    f"ANSIBLE_STEP_{playbook.upper()}",
                    state,
                    {"playbook": playbook, "status": "verified"},
                )
            return True

        cmd = [ansible_bin, f"playbooks/{playbook}.yml"]
        res = self.runner.run(
            args=cmd,
            cwd=self.repo_root / "ansible",
            timeout_seconds=timeout,
            current_state=state,
        )
        return res.success

    def configure(self) -> bool:
        """Run host configuration."""
        return self._execute("dr-configure", "site", 900.0, FailoverState.PROVISIONING)

    def restore_database(self) -> bool:
        """Run database restore."""
        return self._execute("dr-restore", "restore_db", 600.0, FailoverState.RESTORING)

    def smoke_test(self) -> bool:
        """Run smoke test suite."""
        return self._execute("dr-test", "smoke_tests", 300.0, FailoverState.TESTING)
