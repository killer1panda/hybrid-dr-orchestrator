"""Property-based fuzz testing using Hypothesis to verify mathematical invariants."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from hybrid_dr.interfaces import (
    ActionProvider,
    Clock,
    FailoverState,
    SignalClass,
    SignalProvider,
    SignalResult,
    SignalStatus,
)
from hybrid_dr.quorum import QuorumEngine
from hybrid_dr.state_machine import FailoverStateMachine, FileStateStorage


class MockProvider(SignalProvider):
    def __init__(self, name: str, signal_class: SignalClass, status: SignalStatus) -> None:
        self._name = name
        self._class = signal_class
        self._status = status

    @property
    def name(self) -> str:
        return self._name

    @property
    def signal_class(self) -> SignalClass:
        return self._class

    def check(self) -> SignalResult:
        return SignalResult(
            name=self._name,
            signal_class=self._class,
            status=self._status,
            latency_ms=10.0,
            message=f"Status: {self._status.value}",
        )


class MockClock(Clock):
    def __init__(self, start_time: float = 1000.0) -> None:
        self.time_val = start_time

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return self.time_val

    def sleep(self, seconds: float) -> None:
        self.time_val += seconds

    def advance(self, seconds: float) -> None:
        self.time_val += seconds


# Strategy for generating signal classes
signal_class_strategy = st.sampled_from(
    [
        SignalClass.HTTP,
        SignalClass.TCP,
        SignalClass.HEARTBEAT,
        SignalClass.EXTERNAL,
    ]
)


@given(
    failing_class=signal_class_strategy,
    threshold=st.integers(min_value=2, max_value=10),
    num_cycles=st.integers(min_value=1, max_value=15),
)
@settings(max_examples=50)
def test_invariant_single_class_failure_never_triggers_disaster(
    failing_class: SignalClass, threshold: int, num_cycles: int
) -> None:
    """Invariant 1: A failure localized to only a single signal class NEVER causes quorum."""
    providers: list[SignalProvider] = []
    classes = [SignalClass.HTTP, SignalClass.TCP, SignalClass.HEARTBEAT, SignalClass.EXTERNAL]

    for sc in classes:
        status = SignalStatus.FAILED if sc == failing_class else SignalStatus.HEALTHY
        providers.append(MockProvider(name=f"probe_{sc.value}", signal_class=sc, status=status))

    engine = QuorumEngine(providers=providers, failure_threshold=threshold)

    for _ in range(num_cycles):
        decision, reason = engine.evaluate()
        assert not decision, f"False positive triggered for single failing class {failing_class}!"
        assert engine.consecutive_failures == 0


@given(
    statuses=st.lists(
        st.sampled_from([SignalStatus.HEALTHY, SignalStatus.FAILED]), min_size=4, max_size=8
    )
)
@settings(max_examples=50)
def test_invariant_maintenance_mode_suppression(statuses: list[SignalStatus]) -> None:
    """Invariant 2: When maintenance mode is active, failover is unconditionally suppressed."""
    classes = [SignalClass.HTTP, SignalClass.TCP, SignalClass.HEARTBEAT, SignalClass.EXTERNAL]
    providers: list[SignalProvider] = [
        MockProvider(
            name=f"p_{i}",
            signal_class=classes[i % len(classes)],
            status=statuses[i],
        )
        for i in range(len(statuses))
    ]

    engine = QuorumEngine(providers=providers, failure_threshold=1, maintenance_mode=True)
    decision, reason = engine.evaluate()
    assert not decision
    assert "Maintenance mode is active" in reason
    assert engine.consecutive_failures == 0


@given(
    cooldown=st.floats(min_value=10.0, max_value=300.0),
    elapsed=st.floats(min_value=0.1, max_value=9.9),
)
@settings(max_examples=30)
def test_invariant_flapping_cooldown(cooldown: float, elapsed: float) -> None:
    """Invariant 3: Flapping cooldown dampens rapid repeat evaluations."""
    clock = MockClock(start_time=100.0)
    # Providers that always fail across 2 classes + external
    providers = [
        MockProvider("http", SignalClass.HTTP, SignalStatus.FAILED),
        MockProvider("tcp", SignalClass.TCP, SignalStatus.FAILED),
        MockProvider("ext", SignalClass.EXTERNAL, SignalStatus.FAILED),
    ]

    engine = QuorumEngine(
        providers=providers,
        failure_threshold=1,
        cooldown_seconds=cooldown,
        clock=clock,
    )

    # First evaluation succeeds and triggers failover
    first_decision, _ = engine.evaluate()
    assert first_decision

    # Advance clock by less than cooldown
    clock.advance(elapsed)
    second_decision, second_reason = engine.evaluate()
    assert not second_decision
    assert "Flapping cooldown active" in second_reason


@given(
    target_state=st.sampled_from(
        [
            FailoverState.IDLE,
            FailoverState.FENCING,
            FailoverState.PROVISIONING,
            FailoverState.RESTORING,
            FailoverState.TESTING,
            FailoverState.CUTOVER,
            FailoverState.COMPLETED,
        ]
    )
)
@settings(max_examples=25)
def test_invariant_fsm_crash_recovery_determinism(target_state: FailoverState) -> None:
    """Invariant 4: Fresh FSM instantiated from persisted disk state resumes at exact state."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage_file = Path(tmp_dir) / f"fsm_state_{target_state.value}.json"

        # Pre-save target state simulating crash after committing transition
        storage = FileStateStorage(storage_file)
        storage.save(target_state)

        # Boot fresh machine
        mock_actions = MagicMock(spec=ActionProvider)
        fresh_fsm = FailoverStateMachine(actions=mock_actions, storage=storage)

        assert fresh_fsm.current_state == target_state
