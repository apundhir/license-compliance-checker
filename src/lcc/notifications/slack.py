"""Slack notification implementation."""

from __future__ import annotations

import os
from typing import Dict, Optional

import requests

from lcc.notifications.core import Notifier, Notification


class SlackNotifier(Notifier):
    """Send notifications to Slack via webhook."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        channel: Optional[str] = None,
        username: str = "License Compliance Checker",
        icon_emoji: str = ":shield:",
        timeout: int = 10
    ):
        """
        Initialize Slack notifier.

        Args:
            webhook_url: Slack webhook URL
            channel: Override default channel (optional)
            username: Bot username
            icon_emoji: Bot icon emoji
            timeout: Request timeout in seconds
        """
        self.webhook_url = webhook_url or os.getenv("LCC_SLACK_WEBHOOK_URL", "")
        self.channel = channel or os.getenv("LCC_SLACK_CHANNEL", "")
        self.username = username
        self.icon_emoji = icon_emoji
        self.timeout = timeout

    async def send(self, notification: Notification) -> bool:
        """
        Send Slack notification.

        Args:
            notification: Notification to send

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            print("SlackNotifier: No webhook URL configured")
            return False

        try:
            payload = self._create_payload(notification)

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return True

            print(f"SlackNotifier: HTTP {response.status_code} - {response.text}")
            return False

        except requests.RequestException as e:
            print(f"SlackNotifier error: {e}")
            return False

    def _create_payload(self, notification: Notification) -> Dict:
        """
        Create Slack message payload.

        Args:
            notification: Notification data

        Returns:
            Slack API payload
        """
        # Determine color based on severity
        severity_colors = {
            "info": "#3b82f6",
            "warning": "#f59e0b",
            "error": "#ef4444"
        }
        color = severity_colors.get(notification.severity, "#6b7280")

        # Build attachment fields from metadata
        fields = []
        if notification.metadata:
            for key, value in notification.metadata.items():
                # Format key as title case
                title = key.replace("_", " ").title()
                fields.append({
                    "title": title,
                    "value": str(value),
                    "short": True
                })

        # Create attachment
        attachment = {
            "color": color,
            "title": notification.title,
            "text": notification.message,
            "fields": fields,
            "footer": "License Compliance Checker",
            "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
            "ts": int(notification.timestamp.timestamp()) if notification.timestamp else None
        }

        # Create payload
        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [attachment]
        }

        if self.channel:
            payload["channel"] = self.channel

        return payload
