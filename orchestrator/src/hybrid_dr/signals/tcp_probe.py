"""TCP socket connectivity probe."""

from __future__ import annotations

import socket
import time

from ..interfaces import SignalClass, SignalResult, SignalStatus


class TcpSignalProvider:
    """Layer 4 TCP handshake probe."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        timeout_seconds: float = 2.0,
        name: str = "tcp_probe",
    ) -> None:
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.name = name

    @property
    def signal_class(self) -> SignalClass:
        return SignalClass.TCP

    def check(self) -> SignalResult:
        start = time.monotonic()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout_seconds)
        try:
            sock.connect((self.host, self.port))
            latency_ms = (time.monotonic() - start) * 1000.0
            return SignalResult(
                name=self.name,
                signal_class=self.signal_class,
                status=SignalStatus.HEALTHY,
                latency_ms=round(latency_ms, 2),
                message=f"TCP connection established to {self.host}:{self.port}",
            )
        except OSError as exc:
            latency_ms = (time.monotonic() - start) * 1000.0
            return SignalResult(
                name=self.name,
                signal_class=self.signal_class,
                status=SignalStatus.FAILED,
                latency_ms=round(latency_ms, 2),
                message=f"TCP connection failed to {self.host}:{self.port}: {exc}",
            )
        finally:
            sock.close()
