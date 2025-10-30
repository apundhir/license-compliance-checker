"""Email notification implementation."""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from lcc.notifications.core import Notifier, Notification


class EmailNotifier(Notifier):
    """Send notifications via email."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        to_emails: Optional[List[str]] = None,
        use_tls: bool = True
    ):
        """
        Initialize email notifier.

        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: From email address
            to_emails: List of recipient email addresses
            use_tls: Whether to use TLS
        """
        self.smtp_host = smtp_host or os.getenv("LCC_SMTP_HOST", "localhost")
        self.smtp_port = smtp_port or int(os.getenv("LCC_SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("LCC_SMTP_USER", "")
        self.smtp_password = smtp_password or os.getenv("LCC_SMTP_PASSWORD", "")
        self.from_email = from_email or os.getenv("LCC_FROM_EMAIL", "noreply@lcc.local")
        self.to_emails = to_emails or (os.getenv("LCC_TO_EMAILS", "").split(",") if os.getenv("LCC_TO_EMAILS") else [])
        self.use_tls = use_tls

    async def send(self, notification: Notification) -> bool:
        """
        Send email notification.

        Args:
            notification: Notification to send

        Returns:
            True if successful, False otherwise
        """
        if not self.to_emails:
            print("EmailNotifier: No recipients configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[LCC] {notification.title}"
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)

            # Create plain text and HTML versions
            text_content = self._create_text_content(notification)
            html_content = self._create_html_content(notification)

            # Attach both versions
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            if self.smtp_host == "localhost" and not self.smtp_user:
                # For testing: print instead of sending
                print(f"[EmailNotifier] Would send email:\n{text_content}")
                return True

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, self.to_emails, msg.as_string())

            return True

        except Exception as e:
            print(f"EmailNotifier error: {e}")
            return False

    def _create_text_content(self, notification: Notification) -> str:
        """Create plain text email content."""
        content = f"""{notification.title}

{notification.message}

Severity: {notification.severity.upper()}
Time: {notification.timestamp.isoformat() if notification.timestamp else 'N/A'}
"""

        if notification.metadata:
            content += "\nDetails:\n"
            for key, value in notification.metadata.items():
                content += f"  {key}: {value}\n"

        content += "\n---\nLicense Compliance Checker\n"

        return content

    def _create_html_content(self, notification: Notification) -> str:
        """Create HTML email content."""
        severity_colors = {
            "info": "#3b82f6",
            "warning": "#f59e0b",
            "error": "#ef4444"
        }

        color = severity_colors.get(notification.severity, "#6b7280")

        html = f"""
<html>
  <head>
    <style>
      body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
      .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
      .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
      .content {{ background-color: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
      .footer {{ background-color: #f3f4f6; padding: 10px; text-align: center; font-size: 12px; color: #6b7280; border-radius: 0 0 5px 5px; }}
      .metadata {{ background-color: white; padding: 15px; margin-top: 15px; border-radius: 5px; }}
      .metadata-item {{ margin: 5px 0; }}
      .badge {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; text-transform: uppercase; }}
      .badge-info {{ background-color: #dbeafe; color: #1e40af; }}
      .badge-warning {{ background-color: #fef3c7; color: #92400e; }}
      .badge-error {{ background-color: #fee2e2; color: #991b1b; }}
    </style>
  </head>
  <body>
    <div class="container">
      <div class="header">
        <h2 style="margin: 0;">{notification.title}</h2>
      </div>
      <div class="content">
        <p>{notification.message}</p>
        <div>
          <span class="badge badge-{notification.severity}">{notification.severity}</span>
        </div>
"""

        if notification.metadata:
            html += """
        <div class="metadata">
          <h3 style="margin-top: 0;">Details</h3>
"""
            for key, value in notification.metadata.items():
                html += f'          <div class="metadata-item"><strong>{key}:</strong> {value}</div>\n'

            html += "        </div>\n"

        html += f"""
      </div>
      <div class="footer">
        <p>License Compliance Checker | {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if notification.timestamp else ''}</p>
      </div>
    </div>
  </body>
</html>
"""

        return html
