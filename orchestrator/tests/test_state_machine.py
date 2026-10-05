"""Unit tests for the FailoverStateMachine."""

import pytest
from conftest import (
    InMemoryStateStorage,
    MockActionProvider,
    MockClock,
    MockLeaderLock,
    MockNotifier,
)

from hybrid_dr.interfaces import FailoverState
from hybrid_dr.state_machine import (
    LEGAL_TRANSITIONS,
    FailoverStateMachine,
    InvalidTransitionError,
)


def test_happy_path_full_execution(mock_clock: MockClock) -> None:
    """Full end-to-end legal transition flow from IDLE to COMPLETED."""
    storage = InMemoryStateStorage(FailoverState.IDLE)
    actions = MockActionProvider()
    notifier = MockNotifier()
    sm = FailoverStateMachine(
        actions=actions,
        storage=storage,
        notifier=notifier,
        clock=mock_clock,
    )

    final = sm.advance_to_completion()
    assert final == FailoverState.COMPLETED
    assert storage.load() == FailoverState.COMPLETED
    assert actions.calls == [
        "fencing",
        "provisioning",
        "restore",
        "smoke_tests",
        "dns_cutover",
    ]
    assert len(notifier.notifications) == 0


def test_illegal_transitions_raise_error(mock_clock: MockClock) -> None:
    """Verify that every transition outside the transition table raises InvalidTransitionError."""
    actions = MockActionProvider()
    storage = InMemoryStateStorage()
    sm = FailoverStateMachine(actions=actions, storage=storage, clock=mock_clock)

    for state in FailoverState:
        sm.current_state = state
        allowed = LEGAL_TRANSITIONS.get(state, set())
        for candidate in FailoverState:
            if candidate not in allowed:
                with pytest.raises(InvalidTransitionError):
                    sm.transition(candidate)


def test_action_failure_routes_to_failed_needs_human(mock_clock: MockClock) -> None:
    """If an action fails during RESTORING, state machine must transition to FAILED_NEEDS_HUMAN."""
    storage = InMemoryStateStorage(FailoverState.IDLE)
    actions = MockActionProvider(fail_at=FailoverState.RESTORING)
    notifier = MockNotifier()
    sm = FailoverStateMachine(
        actions=actions,
        storage=storage,
        notifier=notifier,
        clock=mock_clock,
    )

    final = sm.advance_to_completion()
    assert final == FailoverState.FAILED_NEEDS_HUMAN
    assert storage.load() == FailoverState.FAILED_NEEDS_HUMAN
    assert len(notifier.notifications) == 1
    assert notifier.notifications[0]["event"] == "FAILOVER_STALLED"


def test_crash_resumption_skips_completed_steps(mock_clock: MockClock) -> None:
    """Simulate crash mid-flight: on restart, it must resume from persisted state."""
    storage = InMemoryStateStorage(FailoverState.RESTORING)
    actions = MockActionProvider()
    sm = FailoverStateMachine(
        actions=actions,
        storage=storage,
        clock=mock_clock,
    )

    assert sm.current_state == FailoverState.RESTORING
    final = sm.advance_to_completion()
    assert final == FailoverState.COMPLETED

    # Did NOT call fencing or provisioning again!
    assert "fencing" not in actions.calls
    assert "provisioning" not in actions.calls
    assert actions.calls == ["restore", "smoke_tests", "dns_cutover"]


def test_leader_lock_blocks_concurrent_orchestrator(mock_clock: MockClock) -> None:
    """If another orchestrator holds the lock, advance_to_completion raises RuntimeError."""
    storage = InMemoryStateStorage(FailoverState.IDLE)
    actions = MockActionProvider()
    busy_lock = MockLeaderLock(can_acquire=False)

    sm = FailoverStateMachine(
        actions=actions,
        storage=storage,
        lock=busy_lock,
        clock=mock_clock,
    )

    with pytest.raises(RuntimeError, match="Could not acquire leader lock"):
        sm.advance_to_completion()
