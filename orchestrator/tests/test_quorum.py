"""Unit tests for multi-signal QuorumEngine."""

from conftest import MockClock, MockSignal

from hybrid_dr.interfaces import SignalClass, SignalStatus
from hybrid_dr.quorum import QuorumEngine


def test_single_failing_signal_class_never_triggers_failover(mock_clock: MockClock) -> None:
    """False alarm immunity: HTTP probe failure alone must NOT trigger failover."""
    http_sig = MockSignal("http_probe", SignalClass.HTTP, SignalStatus.FAILED)
    tcp_sig = MockSignal("tcp_probe", SignalClass.TCP, SignalStatus.HEALTHY)
    heartbeat_sig = MockSignal("heartbeat", SignalClass.HEARTBEAT, SignalStatus.HEALTHY)

    engine = QuorumEngine(
        providers=[http_sig, tcp_sig, heartbeat_sig],
        failure_threshold=3,
        clock=mock_clock,
    )

    # Run 5 consecutive checks
    for _ in range(5):
        decision, reason = engine.evaluate()
        assert not decision
        assert "single-class failure ignored" in reason


def test_quorum_requires_multiple_independent_classes(mock_clock: MockClock) -> None:
    """Quorum requires at least 2 distinct signal classes failing."""
    http_sig = MockSignal("http_probe", SignalClass.HTTP, SignalStatus.FAILED)
    tcp_sig = MockSignal("tcp_probe", SignalClass.TCP, SignalStatus.FAILED)
    heartbeat_sig = MockSignal("heartbeat", SignalClass.HEARTBEAT, SignalStatus.HEALTHY)

    engine = QuorumEngine(
        providers=[http_sig, tcp_sig, heartbeat_sig],
        failure_threshold=3,
        clock=mock_clock,
    )

    # 1st fail
    dec1, _ = engine.evaluate()
    assert not dec1
    # 2nd fail
    dec2, _ = engine.evaluate()
    assert not dec2
    # 3rd fail -> Quorum reached!
    dec3, reason = engine.evaluate()
    assert dec3
    assert "QUORUM REACHED" in reason


def test_intermittent_health_resets_consecutive_counter(mock_clock: MockClock) -> None:
    """A transient recovery resets the consecutive failure counter to 0."""
    http_sig = MockSignal("http_probe", SignalClass.HTTP, SignalStatus.FAILED)
    tcp_sig = MockSignal("tcp_probe", SignalClass.TCP, SignalStatus.FAILED)

    engine = QuorumEngine(
        providers=[http_sig, tcp_sig],
        failure_threshold=3,
        clock=mock_clock,
    )

    assert not engine.evaluate()[0]  # Fail 1
    assert not engine.evaluate()[0]  # Fail 2

    # Cluster recovers briefly
    tcp_sig.set_status(SignalStatus.HEALTHY)
    assert not engine.evaluate()[0]  # Recovered
    assert engine.consecutive_failures == 0

    # Fails again
    tcp_sig.set_status(SignalStatus.FAILED)
    assert not engine.evaluate()[0]  # Fail 1 again
    assert engine.consecutive_failures == 1


def test_maintenance_mode_suppresses_failover(mock_clock: MockClock) -> None:
    """When maintenance mode is active, failover is strictly forbidden."""
    http_sig = MockSignal("http_probe", SignalClass.HTTP, SignalStatus.FAILED)
    tcp_sig = MockSignal("tcp_probe", SignalClass.TCP, SignalStatus.FAILED)

    engine = QuorumEngine(
        providers=[http_sig, tcp_sig],
        failure_threshold=1,
        maintenance_mode=True,
        clock=mock_clock,
    )

    dec, reason = engine.evaluate()
    assert not dec
    assert "Maintenance mode is active" in reason


def test_flapping_cooldown_prevents_rapid_fire(mock_clock: MockClock) -> None:
    """Cooldown prevents repeat trigger within cooldown window."""
    http_sig = MockSignal("http_probe", SignalClass.HTTP, SignalStatus.FAILED)
    tcp_sig = MockSignal("tcp_probe", SignalClass.TCP, SignalStatus.FAILED)

    engine = QuorumEngine(
        providers=[http_sig, tcp_sig],
        failure_threshold=1,
        cooldown_seconds=60.0,
        clock=mock_clock,
    )

    # 1st trigger
    dec1, _ = engine.evaluate()
    assert dec1

    # Immediate second check should be blocked by cooldown
    dec2, reason2 = engine.evaluate()
    assert not dec2
    assert "Flapping cooldown active" in reason2

    # Advance fake clock beyond 60s
    mock_clock.advance(65.0)
    dec3, _ = engine.evaluate()
    assert dec3
