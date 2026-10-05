"""Structured monotonic JSONL audit logger and clock implementation."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .interfaces import Clock, FailoverState


class SystemClock:
    """Standard system clock implementing Clock protocol."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class JsonlAuditLogger:
    """Monotonic structured audit logger writing JSON lines."""

    def __init__(
        self,
        log_path: str | Path,
        run_id: str | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.log_path = Path(log_path)
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.clock = clock or SystemClock()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event: str,
        state: FailoverState,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append an audit record to the JSON lines file."""
        entry = {
            "run_id": self.run_id,
            "ts_utc": self.clock.now_utc().isoformat(),
            "monotonic_s": round(self.clock.monotonic(), 3),
            "event": event,
            "state": state.value,
            "details": details or {},
        }
        line = json.dumps(entry, default=str) + "\n"

        # Thread and process-safe append
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
