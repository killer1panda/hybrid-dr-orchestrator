"""Notification dispatcher for operator alerts."""

from __future__ import annotations

import logging

import requests

from .interfaces import Notifier

logger = logging.getLogger(__name__)


class WebhookNotifier(Notifier):
    """Dispatches JSON alert payloads to configured webhook URL."""

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url

    def notify(self, event: str, message: str, level: str = "INFO") -> None:
        """Send notification to webhook, or log to console if unconfigured."""
        payload = {
            "project": "hybrid-dr-orchestrator",
            "event": event,
            "level": level,
            "message": message,
        }

        if not self.webhook_url:
            print(f"[{level}] [ALERT] {event}: {message}")
            return

        try:
            requests.post(self.webhook_url, json=payload, timeout=5.0)
        except Exception as exc:
            logger.warning("Failed to send webhook notification: %s", exc)
            print(f"[{level}] [ALERT (webhook failed)] {event}: {message}")
