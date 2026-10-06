"""Deterministic finite state machine with atomic persistence and leader locking."""

from __future__ import annotations

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore

try:
    import msvcrt
except ImportError:
    msvcrt = None  # type: ignore

import json
import os
import tempfile
from pathlib import Path
from typing import Callable

from .audit import SystemClock
from .interfaces import (
    ActionProvider,
    AuditLogger,
    Clock,
    FailoverState,
    LeaderLock,
    Notifier,
    StateStorage,
    TransitionRecord,
)


class FileStateStorage:
    """Atomic state persistence using temporary file swap."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> FailoverState:
        """Load state from disk or return IDLE if not found."""
        if not self.path.exists():
            return FailoverState.IDLE
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return FailoverState(data.get("state", FailoverState.IDLE.value))
        except (json.JSONDecodeError, ValueError, KeyError):
            return FailoverState.IDLE

    def save(self, state: FailoverState) -> None:
        """Atomically persist state by writing to tempfile then replacing."""
        dir_name = self.path.parent
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp:
            json.dump({"state": state.value}, tmp)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_name = tmp.name

        os.replace(temp_name, self.path)


class FileLeaderLock:
    """Non-blocking file-based leader lock using fcntl or msvcrt on Windows."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd: int | None = None

    def acquire(self) -> bool:
        """Attempt to acquire mutual exclusion lock."""
        if self._fd is not None:
            return True
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
            if fcntl is not None:
                fcntl_flock = getattr(fcntl, "flock")
                fcntl_lock_ex = getattr(fcntl, "LOCK_EX")
                fcntl_lock_nb = getattr(fcntl, "LOCK_NB")
                fcntl_flock(fd, fcntl_lock_ex | fcntl_lock_nb)
            elif msvcrt is not None:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            self._fd = fd
            return True
        except (BlockingIOError, OSError) as e:
            import errno

            if e.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                return False
            raise

    def release(self) -> None:
        """Release lock and close descriptor."""
        if self._fd is not None:
            try:
                if fcntl is not None:
                    fcntl_flock = getattr(fcntl, "flock")
                    fcntl_lock_un = getattr(fcntl, "LOCK_UN")
                    fcntl_flock(self._fd, fcntl_lock_un)
                elif msvcrt is not None:
                    try:
                        msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                os.close(self._fd)
            except OSError:
                pass
            finally:
                self._fd = None

    def is_locked(self) -> bool:
        return self._fd is not None


class InvalidTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""

    def __init__(self, from_state: FailoverState, to_state: FailoverState) -> None:
        super().__init__(
            f"Illegal state transition requested from {from_state.value} to {to_state.value}"
        )
        self.from_state = from_state
        self.to_state = to_state


# Explicit Transition Table: from_state -> {allowed_next_states}
LEGAL_TRANSITIONS: dict[FailoverState, set[FailoverState]] = {
    FailoverState.IDLE: {FailoverState.FENCING},
    FailoverState.FENCING: {FailoverState.PROVISIONING, FailoverState.FAILED_NEEDS_HUMAN},
    FailoverState.PROVISIONING: {FailoverState.RESTORING, FailoverState.FAILED_NEEDS_HUMAN},
    FailoverState.RESTORING: {FailoverState.TESTING, FailoverState.FAILED_NEEDS_HUMAN},
    FailoverState.TESTING: {FailoverState.CUTOVER, FailoverState.FAILED_NEEDS_HUMAN},
    FailoverState.CUTOVER: {FailoverState.COMPLETED, FailoverState.FAILED_NEEDS_HUMAN},
    FailoverState.COMPLETED: {FailoverState.IDLE},  # Reset after failback
    FailoverState.FAILED_NEEDS_HUMAN: {FailoverState.IDLE},  # Reset after manual remediation
}


class FailoverStateMachine:
    """Manages the lifecycle of automated failover with strict transition validation."""

    def __init__(
        self,
        actions: ActionProvider,
        storage: StateStorage,
        notifier: Notifier | None = None,
        audit: AuditLogger | None = None,
        lock: LeaderLock | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.actions = actions
        self.storage = storage
        self.notifier = notifier
        self.audit = audit
        self.lock = lock
        self.clock = clock or SystemClock()
        self.history: list[TransitionRecord] = []

        self.current_state = self.storage.load()

    def transition(self, next_state: FailoverState, error_message: str | None = None) -> None:
        """Validate and commit a state transition atomically."""
        allowed = LEGAL_TRANSITIONS.get(self.current_state, set())
        if next_state not in allowed:
            raise InvalidTransitionError(self.current_state, next_state)

        record = TransitionRecord(
            from_state=self.current_state,
            to_state=next_state,
            success=next_state != FailoverState.FAILED_NEEDS_HUMAN,
            timestamp_utc=self.clock.now_utc(),
            error_message=error_message,
        )
        self.history.append(record)

        self.current_state = next_state
        self.storage.save(next_state)

        if self.audit:
            self.audit.log(
                event=f"TRANSITION_{record.from_state.value}_TO_{record.to_state.value}",
                state=self.current_state,
                details={"error": error_message} if error_message else None,
            )

        if next_state == FailoverState.FAILED_NEEDS_HUMAN and self.notifier:
            err_text = error_message or "Unknown error"
            self.notifier.notify(
                event="FAILOVER_STALLED",
                message=f"Failover stalled at {record.from_state.value}: {err_text}",
                level="CRITICAL",
            )

    def step(self) -> FailoverState:
        """Execute the next single step according to current state."""
        dispatch_table: dict[FailoverState, tuple[Callable[[], bool], FailoverState]] = {
            FailoverState.FENCING: (self.actions.execute_fencing, FailoverState.PROVISIONING),
            FailoverState.PROVISIONING: (
                self.actions.execute_provisioning,
                FailoverState.RESTORING,
            ),
            FailoverState.RESTORING: (self.actions.execute_restore, FailoverState.TESTING),
            FailoverState.TESTING: (self.actions.execute_smoke_tests, FailoverState.CUTOVER),
            FailoverState.CUTOVER: (self.actions.execute_dns_cutover, FailoverState.COMPLETED),
        }

        if self.current_state == FailoverState.IDLE:
            self.transition(FailoverState.FENCING)
            return self.current_state

        if self.current_state in (FailoverState.COMPLETED, FailoverState.FAILED_NEEDS_HUMAN):
            return self.current_state

        action_fn, success_state = dispatch_table[self.current_state]
        try:
            ok = action_fn()
            if ok:
                self.transition(success_state)
            else:
                self.transition(
                    FailoverState.FAILED_NEEDS_HUMAN,
                    error_message=f"Action failed during {self.current_state.value}",
                )
        except Exception as exc:
            import traceback

            tb = traceback.format_exc()
            self.transition(
                FailoverState.FAILED_NEEDS_HUMAN,
                error_message=f"Exception during {self.current_state.value}: {exc}\n{tb}",
            )

        return self.current_state

    def advance_to_completion(self) -> FailoverState:
        """Advance the state machine repeatedly until terminal state or failure."""
        if self.lock and not self.lock.acquire():
            raise RuntimeError("Could not acquire leader lock. Another orchestrator may be active.")

        try:
            while self.current_state not in (
                FailoverState.COMPLETED,
                FailoverState.FAILED_NEEDS_HUMAN,
            ):
                self.step()
            return self.current_state
        finally:
            if self.lock:
                self.lock.release()
