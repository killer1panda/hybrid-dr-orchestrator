"""Multi-signal quorum evaluation and flapping protection."""

from __future__ import annotations

from typing import Any, Sequence

from .audit import SystemClock
from .interfaces import Clock, SignalClass, SignalProvider, SignalResult, SignalStatus


class QuorumEngine:
    """Evaluates multi-signal health checks against strict quorum criteria."""

    def __init__(
        self,
        providers: Sequence[SignalProvider],
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
        maintenance_mode: bool = False,
        clock: Clock | None = None,
    ) -> None:
        self.providers = list(providers)
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.maintenance_mode = maintenance_mode
        self.clock = clock or SystemClock()

        self.consecutive_failures = 0
        self.last_failover_decision_ts: float | None = None
        self.last_results: list[SignalResult] = []

    def evaluate(self) -> tuple[bool, str]:
        """Evaluate signals and return (decision_bool, reason_string).

        Returns:
            (True, reason) if all quorum criteria are met to trigger a failover.
            (False, reason) if quorum rejects failover or maintenance is active.
        """
        if self.maintenance_mode:
            self.consecutive_failures = 0
            return False, "Maintenance mode is active; failover suppressed."

        # Check flapping cooldown
        now_mono = self.clock.monotonic()
        if (
            self.last_failover_decision_ts is not None
            and (now_mono - self.last_failover_decision_ts) < self.cooldown_seconds
        ):
            return False, "Flapping cooldown active; waiting for stabilization."

        # Execute all health probes
        self.last_results = [p.check() for p in self.providers]

        if not self.last_results:
            return False, "No signal providers configured."

        failed_results = [r for r in self.last_results if r.status == SignalStatus.FAILED]
        failed_classes = {r.signal_class for r in failed_results}

        # Check external vantage if present
        external_providers = [p for p in self.providers if p.signal_class == SignalClass.EXTERNAL]
        external_agrees = True
        if external_providers:
            external_agrees = any(
                r.signal_class == SignalClass.EXTERNAL and r.status == SignalStatus.FAILED
                for r in failed_results
            )

        # Quorum rule: Requires failure across >= 2 independent signal classes
        # AND external agreement
        quorum_conditions_met = len(failed_classes) >= 2 and external_agrees

        if quorum_conditions_met:
            self.consecutive_failures += 1
            reason = (
                f"Quorum failure detected ({self.consecutive_failures}/{self.failure_threshold}): "
                f"failed classes={sorted(c.value for c in failed_classes)}, "
                f"external_agrees={external_agrees}"
            )
        else:
            self.consecutive_failures = 0
            reason = (
                f"Cluster healthy or single-class failure ignored: "
                f"failed classes={sorted(c.value for c in failed_classes)}"
            )

        if self.consecutive_failures >= self.failure_threshold:
            self.last_failover_decision_ts = now_mono
            return (
                True,
                f"QUORUM REACHED: Disaster confirmed after {self.consecutive_failures} checks.",
            )

        return False, reason

    def get_summary(self) -> dict[str, Any]:
        """Return diagnostic state of the quorum engine."""
        return {
            "consecutive_failures": self.consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "maintenance_mode": self.maintenance_mode,
            "signals": [
                {
                    "name": r.name,
                    "class": r.signal_class.value,
                    "status": r.status.value,
                    "latency_ms": r.latency_ms,
                    "message": r.message,
                }
                for r in self.last_results
            ],
        }
