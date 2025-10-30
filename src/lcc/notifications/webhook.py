"""Webhook notification implementation."""

from __future__ import annotations

import asyncio
import os
from typing import Dict, List, Optional

import requests

from lcc.notifications.core import Notifier, Notification


class WebhookNotifier(Notifier):
    """Send notifications via webhooks."""

    def __init__(
        self,
        webhook_urls: Optional[List[str]] = None,
        timeout: int = 10,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize webhook notifier.

        Args:
            webhook_urls: List of webhook URLs to POST to
            timeout: Request timeout in seconds
            retry_count: Number of retries on failure
            retry_delay: Delay between retries in seconds
        """
        self.webhook_urls = webhook_urls or (
            os.getenv("LCC_WEBHOOK_URLS", "").split(",") if os.getenv("LCC_WEBHOOK_URLS") else []
        )
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay

    async def send(self, notification: Notification) -> bool:
        """
        Send webhook notification.

        Args:
            notification: Notification to send

        Returns:
            True if at least one webhook succeeds, False otherwise
        """
        if not self.webhook_urls:
            print("WebhookNotifier: No webhook URLs configured")
            return False

        payload = self._create_payload(notification)
        success_count = 0

        for url in self.webhook_urls:
            if await self._send_to_url(url, payload):
                success_count += 1

        return success_count > 0

    async def _send_to_url(self, url: str, payload: Dict) -> bool:
        """
        Send payload to a single webhook URL with retries.

        Args:
            url: Webhook URL
            payload: JSON payload

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.retry_count):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code < 400:
                    return True

                print(f"WebhookNotifier: HTTP {response.status_code} for {url}")

            except requests.RequestException as e:
                print(f"WebhookNotifier error (attempt {attempt + 1}/{self.retry_count}): {e}")

            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff

        return False

    def _create_payload(self, notification: Notification) -> Dict:
        """
        Create webhook payload.

        Args:
            notification: Notification data

        Returns:
            JSON-serializable payload
        """
        return {
            "type": notification.type.value,
            "title": notification.title,
            "message": notification.message,
            "severity": notification.severity,
            "timestamp": notification.timestamp.isoformat() if notification.timestamp else None,
            "metadata": notification.metadata or {}
        }
