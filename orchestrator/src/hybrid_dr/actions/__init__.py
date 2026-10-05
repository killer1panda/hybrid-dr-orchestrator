"""Action providers package combining individual steps into ActionProvider protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import OrchestratorConfig
from ..interfaces import ActionProvider, AuditLogger
from .ansible import AnsibleAction
from .dns import DnsAction
from .fencing import FencingAction
from .runner import SubprocessRunner
from .terraform import TerraformAction


class CompositeActionProvider(ActionProvider):
    """Coordinates real or dry-run side effects implementing ActionProvider protocol."""

    def __init__(
        self,
        config: OrchestratorConfig,
        repo_root: Path | None = None,
        audit: AuditLogger | None = None,
        ssm_client: Any | None = None,
        route53_client: Any | None = None,
    ) -> None:
        self.config = config
        self.runner = SubprocessRunner(audit=audit, dry_run=config.dry_run)
        self.fencing = FencingAction(
            config=config, runner=self.runner, audit=audit, ssm_client=ssm_client
        )
        self.terraform = TerraformAction(
            config=config, repo_root=repo_root, runner=self.runner, audit=audit
        )
        self.ansible = AnsibleAction(
            config=config, repo_root=repo_root, runner=self.runner, audit=audit
        )
        self.dns = DnsAction(config=config, audit=audit, route53_client=route53_client)

    def execute_fencing(self) -> bool:
        return self.fencing.execute()

    def execute_provisioning(self) -> bool:
        ok_tf = self.terraform.provision()
        if not ok_tf:
            return False
        return self.ansible.configure()

    def execute_restore(self) -> bool:
        return self.ansible.restore_database()

    def execute_smoke_tests(self) -> bool:
        return self.ansible.smoke_test()

    def execute_dns_cutover(self) -> bool:
        return self.dns.cutover()


__all__ = [
    "SubprocessRunner",
    "FencingAction",
    "TerraformAction",
    "AnsibleAction",
    "DnsAction",
    "CompositeActionProvider",
]
