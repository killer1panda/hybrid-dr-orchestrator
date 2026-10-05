"""Route 53 DNS cutover action provider."""

from __future__ import annotations

from typing import Any

from ..config import OrchestratorConfig
from ..interfaces import AuditLogger, FailoverState


class DnsAction:
    """Manages Route 53 DNS record updates."""

    def __init__(
        self,
        config: OrchestratorConfig,
        audit: AuditLogger | None = None,
        route53_client: Any | None = None,
    ) -> None:
        self.config = config
        self.audit = audit
        self._r53 = route53_client

    def _get_client(self) -> Any:
        if self._r53 is not None:
            return self._r53
        import boto3

        session = boto3.Session(
            profile_name=self.config.aws_profile,
            region_name=self.config.aws_region,
        )
        self._r53 = session.client("route53")
        return self._r53

    def cutover(self, target_ip_or_cname: str = "15.135.65.200") -> bool:
        """Switch DNS record in Route 53 to point to the DR replica."""
        if self.config.dry_run:
            if self.audit:
                self.audit.log(
                    event="DNS_CUTOVER_SIMULATED",
                    state=FailoverState.CUTOVER,
                    details={
                        "record": self.config.aws.dns_record_name,
                        "target": target_ip_or_cname,
                    },
                )
            return True

        try:
            r53 = self._get_client()
            r53.change_resource_record_sets(
                HostedZoneId=self.config.aws.route53_hosted_zone_id,
                ChangeBatch={
                    "Comment": "Automated DR failover cutover",
                    "Changes": [
                        {
                            "Action": "UPSERT",
                            "ResourceRecordSet": {
                                "Name": self.config.aws.dns_record_name,
                                "Type": "A",
                                "TTL": 60,
                                "ResourceRecords": [{"Value": target_ip_or_cname}],
                            },
                        }
                    ],
                },
            )
            if self.audit:
                self.audit.log(
                    event="DNS_CUTOVER_COMPLETED",
                    state=FailoverState.CUTOVER,
                    details={
                        "record": self.config.aws.dns_record_name,
                        "target": target_ip_or_cname,
                    },
                )
            return True
        except Exception as exc:
            if self.audit:
                self.audit.log(
                    event="DNS_CUTOVER_FAILED",
                    state=FailoverState.CUTOVER,
                    details={"error": str(exc)},
                )
            return False
