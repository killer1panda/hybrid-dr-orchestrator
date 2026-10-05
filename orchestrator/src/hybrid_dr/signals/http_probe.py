"""HTTP health check probe."""

from __future__ import annotations

import time

import requests

from ..interfaces import SignalClass, SignalResult, SignalStatus


class HttpSignalProvider:
    """HTTP endpoint probe (e.g. GET /healthz)."""

    def __init__(
        self,
        url: str = "http://localhost:8080/healthz",
        timeout_seconds: float = 3.0,
        name: str = "http_probe",
    ) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.name = name

    @property
    def signal_class(self) -> SignalClass:
        return SignalClass.HTTP

    def check(self) -> SignalResult:
        start = time.monotonic()
        try:
            resp = requests.get(self.url, timeout=self.timeout_seconds)
            latency_ms = (time.monotonic() - start) * 1000.0

            if resp.status_code == 200:
                return SignalResult(
                    name=self.name,
                    signal_class=self.signal_class,
                    status=SignalStatus.HEALTHY,
                    latency_ms=round(latency_ms, 2),
                    message=f"HTTP 200 OK from {self.url}",
                )
            return SignalResult(
                name=self.name,
                signal_class=self.signal_class,
                status=SignalStatus.FAILED,
                latency_ms=round(latency_ms, 2),
                message=f"HTTP status {resp.status_code} from {self.url}",
            )
        except requests.exceptions.RequestException as exc:
            latency_ms = (time.monotonic() - start) * 1000.0
            return SignalResult(
                name=self.name,
                signal_class=self.signal_class,
                status=SignalStatus.FAILED,
                latency_ms=round(latency_ms, 2),
                message=f"HTTP request error: {exc}",
            )
