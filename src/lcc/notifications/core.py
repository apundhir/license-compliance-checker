"""Core notification system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class NotificationType(str, Enum):
    """Types of notifications."""
    SCAN_COMPLETE = "scan_complete"
    SCAN_FAILED = "scan_failed"
    VIOLATION_DETECTED = "violation_detected"
    POLICY_UPDATED = "policy_updated"
    HIGH_RISK_DEPENDENCY = "high_risk_dependency"


@dataclass
class Notification:
    """Notification data structure."""
    type: NotificationType
    title: str
    message: str
    severity: str = "info"  # info, warning, error
    metadata: Dict[str, Any] | None = None
    timestamp: datetime | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class Notifier(ABC):
    """Base class for notification channels."""

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """
        Send a notification.

        Args:
            notification: Notification to send

        Returns:
            True if successful, False otherwise
        """
        pass


class NotificationService:
    """Service for managing and sending notifications."""

    def __init__(self):
        """Initialize notification service."""
        self.notifiers: List[Notifier] = []

    def register_notifier(self, notifier: Notifier) -> None:
        """
        Register a notification channel.

        Args:
            notifier: Notifier instance to register
        """
        self.notifiers.append(notifier)

    async def notify(self, notification: Notification) -> Dict[str, bool]:
        """
        Send notification to all registered channels.

        Args:
            notification: Notification to send

        Returns:
            Dictionary mapping notifier class name to success status
        """
        results = {}

        for notifier in self.notifiers:
            try:
                success = await notifier.send(notification)
                results[notifier.__class__.__name__] = success
            except Exception as e:
                # Log error but don't fail entire notification
                print(f"Error sending notification via {notifier.__class__.__name__}: {e}")
                results[notifier.__class__.__name__] = False

        return results

    async def notify_scan_complete(
        self,
        scan_id: str,
        project: str,
        violations: int,
        warnings: int,
        duration_seconds: float
    ) -> Dict[str, bool]:
        """
        Notify that a scan has completed.

        Args:
            scan_id: Scan ID
            project: Project name
            violations: Number of violations
            warnings: Number of warnings
            duration_seconds: Scan duration

        Returns:
            Notification results
        """
        severity = "error" if violations > 0 else ("warning" if warnings > 0 else "info")

        notification = Notification(
            type=NotificationType.SCAN_COMPLETE,
            title=f"Scan Complete: {project}",
            message=f"Scan completed for {project} with {violations} violations and {warnings} warnings.",
            severity=severity,
            metadata={
                "scan_id": scan_id,
                "project": project,
                "violations": violations,
                "warnings": warnings,
                "duration_seconds": duration_seconds
            }
        )

        return await self.notify(notification)

    async def notify_violation_detected(
        self,
        project: str,
        component: str,
        license: str,
        reason: str
    ) -> Dict[str, bool]:
        """
        Notify about a license violation.

        Args:
            project: Project name
            component: Component name
            license: License identifier
            reason: Violation reason

        Returns:
            Notification results
        """
        notification = Notification(
            type=NotificationType.VIOLATION_DETECTED,
            title=f"License Violation: {component}",
            message=f"License violation detected in {project}: {component} ({license}). {reason}",
            severity="error",
            metadata={
                "project": project,
                "component": component,
                "license": license,
                "reason": reason
            }
        )

        return await self.notify(notification)

    async def notify_policy_updated(
        self,
        policy_name: str,
        updated_by: str
    ) -> Dict[str, bool]:
        """
        Notify about a policy update.

        Args:
            policy_name: Policy name
            updated_by: Username who updated the policy

        Returns:
            Notification results
        """
        notification = Notification(
            type=NotificationType.POLICY_UPDATED,
            title=f"Policy Updated: {policy_name}",
            message=f"Policy '{policy_name}' was updated by {updated_by}.",
            severity="info",
            metadata={
                "policy_name": policy_name,
                "updated_by": updated_by
            }
        )

        return await self.notify(notification)
