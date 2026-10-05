"""Configuration loading and validation for the Hybrid DR Orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class OnPremConfig(BaseModel):
    """Configuration for on-premises monitoring endpoints."""

    health_url: str = "http://localhost:8080/healthz"
    host: str = "127.0.0.1"
    port: int = 8080
    heartbeat_ssm_param: str = "/hybrid-dr/heartbeat/onprem"
    heartbeat_max_age_seconds: int = 90


class AwsConfig(BaseModel):
    """Configuration for AWS resources."""

    route53_hosted_zone_id: str = "Z0157777J80LB1N4CSX2"
    dns_record_name: str = "app.dr-lab.internal"
    active_site_ssm_param: str = "/hybrid-dr/active-site"
    backup_bucket: str = "hybrid-dr-backups-758579869433-ap-southeast-2"


class OrchestratorConfig(BaseModel):
    """Top-level orchestrator configuration."""

    dry_run: bool = Field(default=True, description="When True, commands are simulated.")
    aws_region: str = "ap-southeast-2"
    aws_profile: str = "dr-sandbox"
    allowed_account_id: str = "758579869433"
    rpo_threshold_seconds: int = 300
    quorum_failure_threshold: int = 3
    cooldown_seconds: int = 60
    maintenance_mode: bool = False

    onprem: OnPremConfig = Field(default_factory=OnPremConfig)
    aws: AwsConfig = Field(default_factory=AwsConfig)

    state_file: str = "/tmp/hybrid_dr_state.json"
    audit_log_file: str = "/tmp/hybrid_dr_audit.jsonl"
    lock_file: str = "/tmp/hybrid_dr.lock"
    webhook_url: str | None = None


def load_config(path: str | Path | None = None) -> OrchestratorConfig:
    """Load configuration from YAML file or return defaults if absent."""
    if path is None:
        default_path = Path(__file__).resolve().parent.parent.parent / "config.example.yaml"
        if default_path.exists():
            path = default_path
        else:
            return OrchestratorConfig()

    config_path = Path(path)
    if not config_path.exists():
        return OrchestratorConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)

    return OrchestratorConfig(**(data or {}))
