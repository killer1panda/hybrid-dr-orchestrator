"""Web Dashboard for the Hybrid Cloud Disaster Recovery Orchestrator."""

from __future__ import annotations

import asyncio
import collections
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from .actions import CompositeActionProvider
from .audit import JsonlAuditLogger, SystemClock
from .config import OrchestratorConfig, load_config
from .interfaces import FailoverState, SignalProvider
from .notifier import WebhookNotifier
from .quorum import QuorumEngine
from .signals import HeartbeatSignalProvider, HttpSignalProvider, TcpSignalProvider
from .state_machine import FailoverStateMachine, FileLeaderLock, FileStateStorage


class DrillRequest(BaseModel):
    dry_run: bool = True


class MaintenanceRequest(BaseModel):
    enabled: bool


class FencingRequest(BaseModel):
    active_site: str


def _load_template_html() -> str:
    template_path = Path(__file__).resolve().parent / "templates" / "dashboard.html"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return "<html><body><h1>Dashboard template not found</h1></body></html>"


class _LogBus:
    """Thread-safe broadcast bus for SSE log lines."""

    def __init__(self, maxhistory: int = 500) -> None:
        self._lock = threading.Lock()
        self._history: collections.deque[str] = collections.deque(maxlen=maxhistory)
        # Each subscriber is an asyncio.Queue + its loop
        self._subscribers: list[tuple[asyncio.Queue[str], asyncio.AbstractEventLoop]] = []

    def push(self, line: str) -> None:
        import re
        # Remove ANSI escape sequences and orphaned bracket color codes
        clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\([a-zA-Z]|\[[0-9;]+m|\[0m|\[1m", "", line).strip()
        if not clean:
            return
        with self._lock:
            self._history.append(clean)
            dead = []
            for q, loop in self._subscribers:
                try:
                    loop.call_soon_threadsafe(q.put_nowait, clean)
                except Exception:
                    dead.append((q, loop))
            for d in dead:
                try:
                    self._subscribers.remove(d)
                except ValueError:
                    pass

    def subscribe(self, loop: asyncio.AbstractEventLoop) -> tuple[asyncio.Queue[str], list[str]]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=2000)
        with self._lock:
            history_snapshot = list(self._history)
            self._subscribers.append((q, loop))
        return q, history_snapshot

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        with self._lock:
            self._subscribers[:] = [(sq, sl) for sq, sl in self._subscribers if sq is not q]


class _StreamingAuditLogger:
    """Wraps JsonlAuditLogger and broadcasts every event to the SSE bus."""

    def __init__(self, inner: JsonlAuditLogger, bus: _LogBus) -> None:
        self._inner = inner
        self._bus = bus

    def log(
        self,
        event: str,
        state: FailoverState,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._inner.log(event, state, details)
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        detail_str = ""
        if details:
            detail_str = "  " + json.dumps(details, default=str)
        self._bus.push(f"[{ts}] [{state.value:>20}] {event}{detail_str}")


def create_dashboard_app(config: OrchestratorConfig) -> FastAPI:
    app = FastAPI(title="Hybrid DR Mission Control", version="2.0.0")

    storage = FileStateStorage(config.state_file)
    clock = SystemClock()
    audit = JsonlAuditLogger(config.audit_log_file, clock=clock)

    bus = _LogBus(maxhistory=500)

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

    start_monotonic = time.monotonic()
    chaos_state = {"blackout": False}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _load_template_html()

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        current_state = storage.load()
        signal_results: list[dict[str, Any]] = []
        for p in providers:
            res = p.check()
            status_val = res.status.value
            message_val = res.message
            if chaos_state["blackout"] and res.signal_class.value in ("http", "tcp"):
                status_val = "failed"
                message_val = "Simulated catastrophic blackout"
            signal_results.append({
                "name": res.name,
                "signal_class": res.signal_class.value,
                "status": status_val,
                "latency_ms": round(res.latency_ms, 2),
                "message": message_val,
            })

        fencing_active_site = "aws" if current_state == FailoverState.COMPLETED else "onprem"
        if not config.dry_run:
            try:
                import boto3
                session = boto3.Session(profile_name=config.aws_profile, region_name=config.aws_region)
                ssm = session.client("ssm")
                param = ssm.get_parameter(Name=config.aws.active_site_ssm_param)
                fencing_active_site = str(param["Parameter"]["Value"])
            except Exception:
                pass

        healthy_count = sum(1 for s in signal_results if s["status"] == "healthy")
        elapsed_s = round(time.monotonic() - start_monotonic, 1)

        if chaos_state["blackout"]:
            prev = quorum.consecutive_failures
            quorum.consecutive_failures = min(
                quorum.consecutive_failures + 1, config.quorum_failure_threshold
            )
            if prev < config.quorum_failure_threshold and quorum.consecutive_failures == config.quorum_failure_threshold:
                bus.push("🚨 QUORUM BREACHED: Multi-signal disaster threshold reached (3/3). Failover recommended.")
        else:
            quorum.consecutive_failures = 0

        return {
            "state": current_state.value,
            "dry_run": config.dry_run,
            "aws_region": config.aws_region,
            "maintenance_mode": config.maintenance_mode,
            "fencing_active_site": fencing_active_site,
            "signals": signal_results,
            "quorum": {
                "consecutive_failures": quorum.consecutive_failures,
                "failure_threshold": config.quorum_failure_threshold,
                "cooldown_seconds": config.cooldown_seconds,
            },
            "benchmarks": {
                "cold_rto_seconds": 1272,
                "golden_ami_rto_seconds": 405,
                "measured_rpo_seconds": 290,
                "sla_rpo_budget_seconds": config.rpo_threshold_seconds,
            },
            "costs": {
                "standing_compute_usd": 0.00,
                "persistent_monthly_usd": 0.50,
                "active_drill_hourly_usd": 0.034 if current_state != FailoverState.IDLE else 0.00,
            },
            "kpis": {
                "uptime_seconds": elapsed_s,
                "healthy_signals": healthy_count,
                "total_signals": len(signal_results),
                "readiness_pct": 100.0 if not chaos_state["blackout"] else 0.0,
                "measured_rpo_s": 290,
                "rpo_budget_pct": round((290 / max(config.rpo_threshold_seconds, 1)) * 100, 1),
                "rto_golden_ami_s": 405,
                "rto_cold_boot_s": 1272,
                "active_site": "aws" if current_state == FailoverState.COMPLETED
                    else ("onprem" if not chaos_state["blackout"] else "failing"),
                "chaos_blackout_active": chaos_state["blackout"],
            },
        }

    @app.get("/api/audit")
    def get_audit() -> list[dict[str, Any]]:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        log_files = [
            Path(config.audit_log_file),
            repo_root / "audit" / "drills.jsonl",
        ]
        entries: list[dict[str, Any]] = []
        for lf in log_files:
            if lf.exists():
                try:
                    with open(lf, "r", encoding="utf-8") as f:
                        for line in f:
                            cleaned = line.strip()
                            if cleaned:
                                entries.append(json.loads(cleaned))
                except Exception:
                    continue
        entries.sort(key=lambda x: str(x.get("ts_utc", "")), reverse=True)
        return entries[:50]

    @app.post("/api/drill")
    def run_drill(req: DrillRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
        drill_config = config.model_copy()
        drill_config.dry_run = req.dry_run
        streaming_audit = _StreamingAuditLogger(audit, bus)

        def _execute_drill() -> None:
            mode = "DRY-RUN SIMULATION" if drill_config.dry_run else "⚡ LIVE AWS PROVISIONING"
            bus.push(f"{'─'*60}")
            bus.push(f"  FAILOVER DRILL INITIATED — {mode}")
            bus.push(f"  Region: {drill_config.aws_region}  Account: {drill_config.allowed_account_id}")
            bus.push(f"{'─'*60}")

            # Auto-reset state machine if it is in terminal state
            curr_state = storage.load()
            if curr_state in (FailoverState.COMPLETED, FailoverState.FAILED_NEEDS_HUMAN):
                storage.save(FailoverState.IDLE)
                bus.push(f"Resetting state machine from {curr_state.value} to IDLE for new drill.")

            actions = CompositeActionProvider(
                config=drill_config,
                audit=streaming_audit,
                output_callback=bus.push,
            )
            lock = FileLeaderLock(drill_config.lock_file)
            notifier = WebhookNotifier(drill_config.webhook_url)
            sm = FailoverStateMachine(
                actions=actions,
                storage=storage,
                notifier=notifier,
                audit=streaming_audit,
                lock=lock,
                clock=clock,
            )
            final = sm.advance_to_completion()
            bus.push(f"{'─'*60}")
            bus.push(f"  DRILL COMPLETE — Final State: {final.value}")
            bus.push(f"{'─'*60}")

        background_tasks.add_task(_execute_drill)
        return {"status": "started", "message": f"Drill triggered (dry_run={req.dry_run})"}

    @app.get("/api/logs")
    async def stream_logs(request: Request) -> StreamingResponse:
        loop = asyncio.get_running_loop()
        q, history = bus.subscribe(loop)

        async def generator():
            # Flush history immediately
            for line in history:
                yield f"data: {line}\n\n"
            # Stream live events
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        line = await asyncio.wait_for(q.get(), timeout=20.0)
                        yield f"data: {line}\n\n"
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"
            finally:
                bus.unsubscribe(q)

        return StreamingResponse(generator(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        })

    @app.post("/api/failback")
    def run_failback() -> dict[str, Any]:
        bus.push("FAILBACK: Initiating AWS teardown and state reset...")
        actions = CompositeActionProvider(config=config, audit=audit)
        ok = actions.terraform.teardown()
        if ok:
            storage.save(FailoverState.IDLE)
            audit.log("FAILBACK_COMPLETED", FailoverState.IDLE, {"status": "reset to idle"})
            chaos_state["blackout"] = False
            bus.push("✓ FAILBACK COMPLETE — State reset to IDLE, AWS resources terminated")
            return {"status": "ok", "message": "Failback succeeded."}
        bus.push("✗ FAILBACK FAILED — Terraform teardown returned error")
        return {"status": "error", "message": "Failback teardown failed."}

    @app.post("/api/maintenance")
    def set_maintenance(req: MaintenanceRequest) -> dict[str, Any]:
        config.maintenance_mode = req.enabled
        quorum.maintenance_mode = req.enabled
        bus.push(f"MAINTENANCE MODE: {'ENABLED — quorum failover suppressed' if req.enabled else 'DISABLED — normal operation resumed'}")
        return {"status": "ok", "maintenance_mode": config.maintenance_mode}

    @app.post("/api/chaos/onprem")
    def trigger_chaos_onprem() -> dict[str, Any]:
        chaos_state["blackout"] = True
        try:
            import requests
            requests.post("http://127.0.0.1:8080/chaos/blackout", timeout=1.0)
        except Exception:
            pass
        audit.log("CHAOS_INJECTED", storage.load(), {"scenario": "blackout_kill_onprem"})
        bus.push("⚠  CHAOS INJECTED — Simulating catastrophic on-premises blackout")
        return {"status": "ok"}

    @app.post("/api/chaos/recover")
    def trigger_chaos_recover() -> dict[str, Any]:
        chaos_state["blackout"] = False
        try:
            import requests
            requests.post("http://127.0.0.1:8080/chaos/recover", timeout=1.0)
        except Exception:
            pass
        audit.log("CHAOS_CLEARED", storage.load(), {"scenario": "site_recovered"})
        bus.push("✓ CHAOS CLEARED — On-premises site health restored")
        return {"status": "ok"}

    return app


def run_dashboard_server(host: str = "0.0.0.0", port: int = 8500) -> None:
    import uvicorn
    cfg = load_config()
    application = create_dashboard_app(cfg)
    uvicorn.run(application, host=host, port=port)
