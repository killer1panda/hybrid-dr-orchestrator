"""Shared fixtures and mocks for Phase 5 tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from hybrid_dr.interfaces import (
    ActionProvider,
    Clock,
    FailoverState,
    LeaderLock,
    Notifier,
    SignalClass,
    SignalProvider,
    SignalResult,
    SignalStatus,
    StateStorage,
)


class MockClock(Clock):
    """Controllable clock for deterministic testing."""

    def __init__(self, start_ts: datetime | None = None) -> None:
        self._current_time = start_ts or datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
        self._monotonic = 1000.0

    def now_utc(self) -> datetime:
        return self._current_time

    def monotonic(self) -> float:
        return self._monotonic

    def sleep(self, seconds: float) -> None:
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        from datetime import timedelta

        self._current_time += timedelta(seconds=seconds)
        self._monotonic += seconds


class MockSignal(SignalProvider):
    """Configurable signal probe."""

    def __init__(
        self,
        name: str,
        sig_class: SignalClass,
        status: SignalStatus = SignalStatus.HEALTHY,
        latency_ms: float = 10.0,
    ) -> None:
        self._name = name
        self._class = sig_class
        self._status = status
        self._latency = latency_ms

    @property
    def signal_class(self) -> SignalClass:
        return self._class

    def check(self) -> SignalResult:
        return SignalResult(
            name=self._name,
            signal_class=self._class,
            status=self._status,
            latency_ms=self._latency,
            message=f"{self._name} is {self._status.value}",
        )

    def set_status(self, status: SignalStatus) -> None:
        self._status = status


class InMemoryStateStorage(StateStorage):
    """In-memory state storage."""

    def __init__(self, initial_state: FailoverState = FailoverState.IDLE) -> None:
        self.state = initial_state
        self.save_count = 0

    def load(self) -> FailoverState:
        return self.state

    def save(self, state: FailoverState) -> None:
        self.state = state
        self.save_count += 1


class MockActionProvider(ActionProvider):
    """Configurable action provider."""

    def __init__(
        self,
        fail_at: FailoverState | None = None,
    ) -> None:
        self.fail_at = fail_at
        self.calls: list[str] = []

    def execute_fencing(self) -> bool:
        self.calls.append("fencing")
        return self.fail_at != FailoverState.FENCING

    def execute_provisioning(self) -> bool:
        self.calls.append("provisioning")
        return self.fail_at != FailoverState.PROVISIONING

    def execute_restore(self) -> bool:
        self.calls.append("restore")
        return self.fail_at != FailoverState.RESTORING

    def execute_smoke_tests(self) -> bool:
        self.calls.append("smoke_tests")
        return self.fail_at != FailoverState.TESTING

    def execute_dns_cutover(self) -> bool:
        self.calls.append("dns_cutover")
        return self.fail_at != FailoverState.CUTOVER


class MockNotifier(Notifier):
    """Notifier capturing events."""

    def __init__(self) -> None:
        self.notifications: list[dict[str, Any]] = []

    def notify(self, event: str, message: str, level: str = "INFO") -> None:
        self.notifications.append({"event": event, "message": message, "level": level})


class MockLeaderLock(LeaderLock):
    """Configurable leader lock."""

    def __init__(self, can_acquire: bool = True) -> None:
        self.can_acquire = can_acquire
        self.acquired = False

    def acquire(self) -> bool:
        if self.can_acquire:
            self.acquired = True
            return True
        return False

    def release(self) -> None:
        self.acquired = False

    def is_locked(self) -> bool:
        return self.acquired


@pytest.fixture
def mock_clock() -> MockClock:
    return MockClock()
