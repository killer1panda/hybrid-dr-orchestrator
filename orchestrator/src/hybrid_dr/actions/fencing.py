"""Fencing action provider to isolate primary site and prevent split-brain."""

from __future__ import annotations

from typing import Any

from ..config import OrchestratorConfig
from ..interfaces import AuditLogger, FailoverState
from .runner import SubprocessRunner


class FencingAction:
    """Updates AWS SSM active-site fencing parameter and cuts on-prem writes."""

    def __init__(
        self,
        config: OrchestratorConfig,
        runner: SubprocessRunner | None = None,
        audit: AuditLogger | None = None,
        ssm_client: Any | None = None,
    ) -> None:
        self.config = config
        self.runner = runner or SubprocessRunner(audit=audit, dry_run=config.dry_run)
        self.audit = audit
        self._ssm = ssm_client

    def _get_ssm(self) -> Any:
        if self._ssm is not None:
            return self._ssm
        import boto3

        session = boto3.Session(
            profile_name=self.config.aws_profile,
            region_name=self.config.aws_region,
        )
        self._ssm = session.client("ssm")
        return self._ssm

    def execute(self) -> bool:
        """Set /hybrid-dr/active-site parameter to 'aws'."""
        if self.config.dry_run:
            if self.audit:
                self.audit.log(
                    event="FENCING_SIMULATED",
                    state=FailoverState.FENCING,
                    details={"target_active_site": "aws"},
                )
            return True

        try:
            ssm = self._get_ssm()
            ssm.put_parameter(
                Name=self.config.aws.active_site_ssm_param,
                Value="aws",
                Type="String",
                Overwrite=True,
            )
            if self.audit:
                self.audit.log(
                    event="FENCING_COMPLETED",
                    state=FailoverState.FENCING,
                    details={"active_site": "aws"},
                )
            return True
        except Exception as exc:
            if self.audit:
                self.audit.log(
                    event="FENCING_FAILED",
                    state=FailoverState.FENCING,
                    details={"error": str(exc)},
                )
            return False
