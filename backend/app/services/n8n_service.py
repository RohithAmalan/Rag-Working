"""Helpers for sending RAG events to n8n workflows."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from app.utils.config import settings

logger = logging.getLogger(__name__)


async def notify_n8n_event(
    event: str,
    severity: str,
    username: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Send a fire-and-forget event to the configured n8n webhook."""
    webhook_url = settings.n8n_webhook_url.strip()
    if not webhook_url:
        return

    payload = {
        "event": event,
        "severity": severity,
        "username": username,
        "details": details or {},
    }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(webhook_url, json=payload)

        if response.status_code >= 400:
            logger.warning(
                "n8n webhook returned %s for event %s: %s",
                response.status_code,
                event,
                response.text[:300],
            )
    except Exception as exc:
        logger.warning("Failed to notify n8n about %s: %s", event, exc)
