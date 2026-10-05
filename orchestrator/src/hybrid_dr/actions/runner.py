"""Subprocess execution wrapper with strict safety and audit logging."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..interfaces import AuditLogger, FailoverState


@dataclass
class CommandResult:
    """Outcome of an external process execution."""

    returncode: int
    stdout: str
    stderr: str
    duration_s: float

    @property
    def success(self) -> bool:
        return self.returncode == 0


class SubprocessRunner:
    """Safe subprocess runner executing with shell=False and strict timeout."""

    def __init__(
        self,
        audit: AuditLogger | None = None,
        dry_run: bool = True,
    ) -> None:
        self.audit = audit
        self.dry_run = dry_run

    def run(
        self,
        args: list[str],
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout_seconds: float = 300.0,
        current_state: FailoverState = FailoverState.IDLE,
    ) -> CommandResult:
        """Run command safely, capturing output and logging to audit."""
        cmd_str = " ".join(args)

        if self.dry_run:
            if self.audit:
                self.audit.log(
                    event="DRY_RUN_COMMAND_SIMULATED",
                    state=current_state,
                    details={"command": cmd_str, "cwd": str(cwd) if cwd else None},
                )
            return CommandResult(
                returncode=0,
                stdout="[DRY-RUN] Command execution simulated successfully.\n",
                stderr="",
                duration_s=0.01,
            )

        import os
        import signal

        start = time.monotonic()
        try:
            with subprocess.Popen(
                args,
                cwd=cwd,
                env=env,
                shell=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            ) as proc:
                try:
                    stdout, stderr = proc.communicate(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    stdout, stderr = proc.communicate()
                    duration = round(time.monotonic() - start, 3)
                    if self.audit:
                        self.audit.log(
                            event="COMMAND_TIMED_OUT",
                            state=current_state,
                            details={
                                "command": cmd_str,
                                "timeout_seconds": timeout_seconds,
                                "duration_s": duration,
                            },
                        )
                    return CommandResult(
                        returncode=124,
                        stdout=stdout or "",
                        stderr=f"Process timed out after {timeout_seconds} seconds.",
                        duration_s=duration,
                    )

                duration = round(time.monotonic() - start, 3)
                if self.audit:
                    self.audit.log(
                        event="COMMAND_EXECUTED",
                        state=current_state,
                        details={
                            "command": cmd_str,
                            "returncode": proc.returncode,
                            "duration_s": duration,
                        },
                    )

                return CommandResult(
                    returncode=proc.returncode,
                    stdout=stdout or "",
                    stderr=stderr or "",
                    duration_s=duration,
                )
        except Exception as exc:
            duration = round(time.monotonic() - start, 3)
            if self.audit:
                self.audit.log(
                    event="COMMAND_ERROR",
                    state=current_state,
                    details={"command": cmd_str, "error": str(exc)},
                )
            return CommandResult(
                returncode=1,
                stdout="",
                stderr=f"Execution error: {exc}",
                duration_s=duration,
            )
