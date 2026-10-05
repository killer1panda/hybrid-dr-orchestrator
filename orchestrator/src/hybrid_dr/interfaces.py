"""Core protocols and interfaces for the Hybrid Cloud DR Orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol


class Clock(Protocol):
    """Protocol for time abstraction enabling deterministic testing."""

    def now_utc(self) -> datetime:
        """Return the current UTC datetime."""
        ...

    def monotonic(self) -> float:
        """Return monotonic clock value in seconds."""
        ...

    def sleep(self, seconds: float) -> None:
        """Sleep for the specified number of seconds."""
        ...


class SignalStatus(str, Enum):
    """Health status reported by an observation signal."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class SignalClass(str, Enum):
    """Independent fault domains for multi-signal quorum validation."""

    HTTP = "http"
    TCP = "tcp"
    HEARTBEAT = "heartbeat"
    EXTERNAL = "external"


@dataclass(frozen=True)
class SignalResult:
    """Outcome of an individual health check probe."""

    name: str
    signal_class: SignalClass
    status: SignalStatus
    latency_ms: float = 0.0
    message: str = ""


class SignalProvider(Protocol):
    """Protocol for a health monitoring probe."""

    @property
    def signal_class(self) -> SignalClass:
        """Return the category/class of this signal."""
        ...

    def check(self) -> SignalResult:
        """Execute the probe and return the result."""
        ...


class FailoverState(str, Enum):
    """Finite State Machine states for the disaster recovery lifecycle."""

    IDLE = "IDLE"
    FENCING = "FENCING"
    PROVISIONING = "PROVISIONING"
    RESTORING = "RESTORING"
    TESTING = "TESTING"
    CUTOVER = "CUTOVER"
    COMPLETED = "COMPLETED"
    FAILED_NEEDS_HUMAN = "FAILED_NEEDS_HUMAN"


class ActionProvider(Protocol):
    """Protocol for driving side-effecting recovery actions."""

    def execute_fencing(self) -> bool:
        """Fence on-premises site to prevent split-brain writes."""
        ...

    def execute_provisioning(self) -> bool:
        """Deploy ephemeral AWS replica via Terraform."""
        ...

    def execute_restore(self) -> bool:
        """Restore PostgreSQL database from S3 and replay WALs to promotion."""
        ...

    def execute_smoke_tests(self) -> bool:
        """Execute validation test suite against restored replica."""
        ...

    def execute_dns_cutover(self) -> bool:
        """Switch DNS records in Route 53 to point to the AWS replica."""
        ...


class StateStorage(Protocol):
    """Protocol for persisting and loading the state machine state."""

    def load(self) -> FailoverState:
        """Load the persisted state, or IDLE if none exists."""
        ...

    def save(self, state: FailoverState) -> None:
        """Persist state atomically."""
        ...


class LeaderLock(Protocol):
    """Protocol to ensure mutual exclusion across orchestrator processes."""

    def acquire(self) -> bool:
        """Attempt to acquire the leader lock."""
        ...

    def release(self) -> None:
        """Release the leader lock."""
        ...

    def is_locked(self) -> bool:
        """Check if lock is currently held."""
        ...


class Notifier(Protocol):
    """Protocol for alert dispatching."""

    def notify(self, event: str, message: str, level: str = "INFO") -> None:
        """Send a notification to operators."""
        ...


class AuditLogger(Protocol):
    """Protocol for structured monotonic audit event logging."""

    def log(
        self,
        event: str,
        state: FailoverState,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record an audit event."""
        ...


@dataclass
class TransitionRecord:
    """Record of an executed state transition."""

    from_state: FailoverState
    to_state: FailoverState
    success: bool
    timestamp_utc: datetime
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
