"""External vantage point health check probe."""

from __future__ import annotations

import time

from ..interfaces import SignalClass, SignalProvider, SignalResult, SignalStatus


class ExternalSignalProvider:
    """External observer probe confirming failure from outside the primary site."""

    def __init__(
        self,
        provider_delegate: SignalProvider | None = None,
        name: str = "external_vantage",
    ) -> None:
        self.delegate = provider_delegate
        self.name = name

    @property
    def signal_class(self) -> SignalClass:
        return SignalClass.EXTERNAL

    def check(self) -> SignalResult:
        start = time.monotonic()
        if self.delegate is not None:
            res = self.delegate.check()
            return SignalResult(
                name=self.name,
                signal_class=self.signal_class,
                status=res.status,
                latency_ms=res.latency_ms,
                message=f"External vantage: {res.message}",
            )

        latency_ms = (time.monotonic() - start) * 1000.0
        return SignalResult(
            name=self.name,
            signal_class=self.signal_class,
            status=SignalStatus.HEALTHY,
            latency_ms=round(latency_ms, 2),
            message="External vantage default check healthy",
        )
