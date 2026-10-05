"""Command-line interface for the Disaster Recovery Orchestrator."""

from __future__ import annotations

import argparse
import sys
import time

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .actions import CompositeActionProvider
from .audit import JsonlAuditLogger, SystemClock
from .config import OrchestratorConfig, load_config
from .interfaces import FailoverState, SignalProvider
from .notifier import WebhookNotifier
from .quorum import QuorumEngine
from .signals import (
    HeartbeatSignalProvider,
    HttpSignalProvider,
    TcpSignalProvider,
)
from .state_machine import FailoverStateMachine, FileLeaderLock, FileStateStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hybrid-dr-orchestrator",
        description="Automated Hybrid Cloud Disaster Recovery Orchestrator",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--i-understand-this-provisions-aws",
        action="store_true",
        default=False,
        help="Explicit confirmation required to disable dry-run and provision real AWS resources",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: status
    subparsers.add_parser("status", help="Display current failover state and signal health")

    # Subcommand: drill
    drill_parser = subparsers.add_parser("drill", help="Execute an on-demand failover drill")
    drill_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Simulate failover without making cloud changes (default: True)",
    )

    # Subcommand: run
    subparsers.add_parser("run", help="Start continuous monitoring loop and automated failover")

    # Subcommand: failback
    subparsers.add_parser("failback", help="Tear down AWS replica and reset state to IDLE")

    # Subcommand: dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Launch the real-time Web Dashboard UI")
    dash_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind the dashboard server (default: 0.0.0.0)",
    )
    dash_parser.add_argument(
        "--port",
        type=int,
        default=8500,
        help="Port to bind the dashboard server (default: 8500)",
    )

    return parser


def cmd_status(config: OrchestratorConfig) -> int:
    storage = FileStateStorage(config.state_file)
    current_state = storage.load()
    print("========================================")
    print(" Hybrid DR Orchestrator Status")
    print("========================================")
    print(f"Current State:  {current_state.value}")
    print(f"Dry Run Mode:   {config.dry_run}")
    print(f"Region:         {config.aws_region}")
    print(f"State File:     {config.state_file}")
    print(f"Audit Log:      {config.audit_log_file}")
    print("----------------------------------------")

    # Run signal diagnostics
    providers: list[SignalProvider] = [
        HttpSignalProvider(url=config.onprem.health_url),
        TcpSignalProvider(host=config.onprem.host, port=config.onprem.port),
        HeartbeatSignalProvider(
            parameter_name=config.onprem.heartbeat_ssm_param,
            max_age_seconds=config.onprem.heartbeat_max_age_seconds,
            aws_profile=config.aws_profile,
            aws_region=config.aws_region,
        ),
    ]
    print("Live Signals:")
    for p in providers:
        res = p.check()
        status_symbol = "✅" if res.status.value == "healthy" else "❌"
        msg = f"  {status_symbol} [{res.signal_class.value.upper()}] {res.name}: {res.status.value}"
        if res.message:
            msg += f" ({res.message})"
        print(msg)

    return 0


def cmd_drill(config: OrchestratorConfig) -> int:
    print(f"==> Initiating Disaster Recovery Drill (dry_run={config.dry_run})...")
    clock = SystemClock()
    audit = JsonlAuditLogger(config.audit_log_file, clock=clock)
    storage = FileStateStorage(config.state_file)
    lock = FileLeaderLock(config.lock_file)
    notifier = WebhookNotifier(config.webhook_url)

    actions = CompositeActionProvider(config=config, audit=audit)
    sm = FailoverStateMachine(
        actions=actions,
        storage=storage,
        notifier=notifier,
        audit=audit,
        lock=lock,
        clock=clock,
    )

    final_state = sm.advance_to_completion()
    print(f"==> Drill execution complete. Final state: {final_state.value}")
    if final_state == FailoverState.COMPLETED:
        print("✅ SUCCESS: Full failover sequence executed successfully.")
        return 0
    else:
        print(f"❌ FAILOVER STALLED: Requires human intervention ({final_state.value}).")
        return 1


def cmd_failback(config: OrchestratorConfig) -> int:
    print("==> Initiating Failback and Teardown...")
    clock = SystemClock()
    audit = JsonlAuditLogger(config.audit_log_file, clock=clock)
    storage = FileStateStorage(config.state_file)
    actions = CompositeActionProvider(config=config, audit=audit)

    # Teardown DR environment
    ok = actions.terraform.teardown()
    if ok:
        storage.save(FailoverState.IDLE)
        audit.log("FAILBACK_COMPLETED", FailoverState.IDLE, {"status": "reset to idle"})
        print("✅ Failback complete: Ephemeral replica torn down, state reset to IDLE.")
        return 0
    else:
        print("❌ Failback teardown encountered an error.")
        return 1


def cmd_run(config: OrchestratorConfig) -> int:
    print(f"==> Starting continuous orchestrator monitor (dry_run={config.dry_run})...")
    clock = SystemClock()
    audit = JsonlAuditLogger(config.audit_log_file, clock=clock)
    storage = FileStateStorage(config.state_file)
    lock = FileLeaderLock(config.lock_file)
    notifier = WebhookNotifier(config.webhook_url)

    providers: list[SignalProvider] = [
        HttpSignalProvider(url=config.onprem.health_url),
        TcpSignalProvider(host=config.onprem.host, port=config.onprem.port),
        HeartbeatSignalProvider(
            parameter_name=config.onprem.heartbeat_ssm_param,
            max_age_seconds=config.onprem.heartbeat_max_age_seconds,
            aws_profile=config.aws_profile,
            aws_region=config.aws_region,
        ),
    ]
    quorum = QuorumEngine(
        providers=providers,
        failure_threshold=config.quorum_failure_threshold,
        cooldown_seconds=config.cooldown_seconds,
        maintenance_mode=config.maintenance_mode,
        clock=clock,
    )

    actions = CompositeActionProvider(config=config, audit=audit)
    sm = FailoverStateMachine(
        actions=actions,
        storage=storage,
        notifier=notifier,
        audit=audit,
        lock=lock,
        clock=clock,
    )

    while True:
        current_state = storage.load()
        if current_state != FailoverState.IDLE:
            print(f"Active failover in progress ({current_state.value}). Advancing...")
            sm.advance_to_completion()
            break

        disaster, reason = quorum.evaluate()
        if disaster:
            print(f"🚨 DISASTER CONFIRMED: {reason}")
            notifier.notify("DISASTER_TRIGGERED", reason, level="CRITICAL")
            sm.advance_to_completion()
            break
        else:
            print(f"[Heartbeat] {reason}")

        time.sleep(5.0)

    return 0


def cmd_dashboard(config: OrchestratorConfig, host: str = "0.0.0.0", port: int = 8500) -> int:
    """Launch the Mission Control Web Dashboard server."""
    print(f"==> Launching Mission Control Web Dashboard on http://{host}:{port} ...")
    from .dashboard import run_dashboard_server

    run_dashboard_server(host=host, port=port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)

    # Safety invariant: Real AWS changes strictly require explicit flag
    explicit_flag = getattr(args, "i_understand_this_provisions_aws", False)
    if not explicit_flag:
        config.dry_run = True

    if args.command == "status":
        return cmd_status(config)
    elif args.command == "drill":
        return cmd_drill(config)
    elif args.command == "failback":
        return cmd_failback(config)
    elif args.command == "run":
        return cmd_run(config)
    elif args.command == "dashboard":
        host = str(getattr(args, "host", "0.0.0.0"))
        port = int(getattr(args, "port", 8500))
        return cmd_dashboard(config, host=host, port=port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
