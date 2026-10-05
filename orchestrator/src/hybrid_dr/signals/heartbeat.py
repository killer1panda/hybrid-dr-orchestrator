"""Heartbeat monitoring probe via AWS SSM Parameter Store."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from ..audit import SystemClock
from ..interfaces import Clock, SignalClass, SignalResult, SignalStatus


class HeartbeatSignalProvider:
    """Verifies periodic push heartbeats published to AWS SSM Parameter Store."""

    def __init__(
        self,
        parameter_name: str = "/hybrid-dr/heartbeat/onprem",
        max_age_seconds: float = 90.0,
        aws_profile: str = "dr-sandbox",
        aws_region: str = "ap-southeast-2",
        name: str = "ssm_heartbeat",
        clock: Clock | None = None,
        ssm_client: Any | None = None,
    ) -> None:
        self.parameter_name = parameter_name
        self.max_age_seconds = max_age_seconds
        self.aws_profile = aws_profile
        self.aws_region = aws_region
        self.name = name
        self.clock = clock or SystemClock()
        self._ssm = ssm_client

    @property
    def signal_class(self) -> SignalClass:
        return SignalClass.HEARTBEAT

    def _get_client(self) -> Any:
        if self._ssm is not None:
            return self._ssm
        import boto3

        session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
        self._ssm = session.client("ssm")
        return self._ssm

    def check(self) -> SignalResult:
        start = time.monotonic()
        try:
            client = self._get_client()
            resp = client.get_parameter(Name=self.parameter_name)
            latency_ms = (time.monotonic() - start) * 1000.0

            raw_val = resp.get("Parameter", {}).get("Value", "{}")
            payload = json.loads(raw_val)
            ts_str = payload.get("ts_utc")

            if not ts_str:
                return SignalResult(
                    name=self.name,
                    signal_class=self.signal_class,
                    status=SignalStatus.FAILED,
                    latency_ms=round(latency_ms, 2),
                    message="Heartbeat payload missing ts_utc field",
                )

            heartbeat_dt = datetime.fromisoformat(ts_str)
            if heartbeat_dt.tzinfo is None:
                heartbeat_dt = heartbeat_dt.replace(tzinfo=timezone.utc)

            age_seconds = (self.clock.now_utc() - heartbeat_dt).total_seconds()
            if age_seconds <= self.max_age_seconds:
                return SignalResult(
                    name=self.name,
                    signal_class=self.signal_class,
                    status=SignalStatus.HEALTHY,
                    latency_ms=round(latency_ms, 2),
                    message=f"Heartbeat fresh (age: {round(age_seconds, 1)}s)",
                )

            age_str = f"{round(age_seconds, 1)}s"
            return SignalResult(
                name=self.name,
                signal_class=self.signal_class,
                status=SignalStatus.FAILED,
                latency_ms=round(latency_ms, 2),
                message=f"Heartbeat expired (age: {age_str} > max: {self.max_age_seconds}s)",
            )
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000.0
            return SignalResult(
                name=self.name,
                signal_class=self.signal_class,
                status=SignalStatus.FAILED,
                latency_ms=round(latency_ms, 2),
                message=f"Heartbeat lookup failed: {exc}",
            )
