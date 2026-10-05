"""Unit tests for configuration validation."""

from pathlib import Path

from hybrid_dr.config import OrchestratorConfig, load_config


def test_default_config_has_safe_defaults() -> None:
    cfg = OrchestratorConfig()
    assert cfg.dry_run is True
    assert cfg.aws_region == "ap-southeast-2"
    assert cfg.quorum_failure_threshold == 3
    assert cfg.maintenance_mode is False


def test_load_config_from_missing_file_falls_back(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist.yaml"
    cfg = load_config(non_existent)
    assert cfg.dry_run is True


def test_load_config_valid_yaml(tmp_path: Path) -> None:
    yaml_file = tmp_path / "custom_config.yaml"
    yaml_file.write_text(
        """
dry_run: false
quorum_failure_threshold: 5
aws_region: "ap-southeast-2"
onprem:
  health_url: "http://test-server:9000/healthz"
""",
        encoding="utf-8",
    )
    cfg = load_config(yaml_file)
    assert cfg.dry_run is False
    assert cfg.quorum_failure_threshold == 5
    assert cfg.onprem.health_url == "http://test-server:9000/healthz"
