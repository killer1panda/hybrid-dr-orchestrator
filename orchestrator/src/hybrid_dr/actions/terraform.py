"""Terraform action provider for provisioning ephemeral AWS DR environment."""

from __future__ import annotations

import os
import subprocess
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

    def _ensure_ssh_key(self) -> str:
        """Ensure an SSH public key exists and return its contents."""
        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(parents=True, exist_ok=True)
        key_file = ssh_dir / "id_rsa"
        pub_file = ssh_dir / "id_rsa.pub"
        if not pub_file.exists():
            try:
                subprocess.run(
                    ["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", str(key_file), "-q", "-N", ""],
                    check=True,
                    capture_output=True,
                )
            except Exception:
                pass
        if pub_file.exists():
            return pub_file.read_text(encoding="utf-8").strip()
        return ""

    def provision(self) -> bool:
        """Initialize and apply Terraform configuration."""
        if self.runner.dry_run:
            cmd = ["make", "dr-up"]
            res = self.runner.run(
                args=cmd,
                cwd=self.repo_root,
                timeout_seconds=1200.0,
                current_state=FailoverState.PROVISIONING,
            )
            return res.success

        ssh_pub = self._ensure_ssh_key()
        env_vars = {"TF_VAR_ssh_public_key": ssh_pub}

        # 1. Terraform init
        init_res = self.runner.run(
            args=["terraform", "init", "-input=false", "-no-color"],
            cwd=self.tf_dir,
            env=env_vars,
            timeout_seconds=300.0,
            current_state=FailoverState.PROVISIONING,
        )
        if not init_res.success:
            return False

        # 2. Terraform apply
        apply_res = self.runner.run(
            args=["terraform", "apply", "-auto-approve", "-input=false", "-no-color"],
            cwd=self.tf_dir,
            env=env_vars,
            timeout_seconds=1200.0,
            current_state=FailoverState.PROVISIONING,
        )
        return apply_res.success

    def teardown(self) -> bool:
        """Teardown ephemeral Terraform resources."""
        if self.runner.dry_run:
            cmd = ["make", "dr-down"]
            res = self.runner.run(
                args=cmd,
                cwd=self.repo_root,
                timeout_seconds=1200.0,
                current_state=FailoverState.COMPLETED,
            )
            return res.success

        ssh_pub = self._ensure_ssh_key()
        env_vars = {"TF_VAR_ssh_public_key": ssh_pub}

        res = self.runner.run(
            args=["terraform", "destroy", "-auto-approve", "-input=false", "-no-color"],
            cwd=self.tf_dir,
            env=env_vars,
            timeout_seconds=1200.0,
            current_state=FailoverState.COMPLETED,
        )
        return res.success
