"""Unit tests for subprocess actions runner."""

import sys

from hybrid_dr.actions.runner import SubprocessRunner
from hybrid_dr.interfaces import FailoverState


def test_dry_run_simulates_success() -> None:
    runner = SubprocessRunner(dry_run=True)
    res = runner.run(["terraform", "apply", "-auto-approve"])
    assert res.success
    assert res.returncode == 0
    assert "[DRY-RUN]" in res.stdout


def test_real_execution_captures_output() -> None:
    runner = SubprocessRunner(dry_run=False)
    res = runner.run([sys.executable, "-c", "print('hello from subprocess')"])
    assert res.success
    assert "hello from subprocess" in res.stdout


def test_timeout_handling() -> None:
    runner = SubprocessRunner(dry_run=False)
    # Sleep longer than timeout
    res = runner.run(
        [sys.executable, "-c", "import time; time.sleep(1.0)"],
        timeout_seconds=0.1,
        current_state=FailoverState.TESTING,
    )
    assert not res.success
    assert res.returncode == 124
    assert "timed out" in res.stderr
