"""
Email Service

Handles sending emails for password resets, notifications, and user communications.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings


class EmailService:
    """Service for sending emails with template support"""

    def __init__(self):
        """Initialize email service with Jinja2 template engine"""
        template_dir = Path(__file__).parent.parent.parent / "templates" / "emails"
        template_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_from = settings.smtp_from

    def _send_email(
        self,
        to_email: str | list[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        """
        Send an email using SMTP.

        Args:
            to_email: Recipient email address(es)
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_from
            msg["To"] = to_email if isinstance(to_email, str) else ", ".join(to_email)

            # Add plain text version if provided
            if text_body:
                part1 = MIMEText(text_body, "plain")
                msg.attach(part1)

            # Add HTML version
            part2 = MIMEText(html_body, "html")
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            # Log error in production
            print(f"Failed to send email: {e}")
            return False

    def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_token: str,
        reset_url: str | None = None,
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: User's email address
            username: User's username
            reset_token: Password reset token
            reset_url: Base URL for reset (optional, defaults to settings)

        Returns:
            bool: True if email sent successfully
        """
        if not reset_url:
            reset_url = f"{settings.app_url}/password-reset/reset"

        full_reset_link = f"{reset_url}?token={reset_token}"

        try:
            template = self.env.get_template("password_reset.html")
            html_body = template.render(
                username=username,
                reset_link=full_reset_link,
                app_name=settings.app_name,
            )

            # Plain text fallback
            text_body = f"""
            Hello {username},

            You requested to reset your password for {settings.app_name}.

            Please click the following link to reset your password:
            {full_reset_link}

            This link will expire in 1 hour.

            If you didn't request this, please ignore this email.

            Best regards,
            The {settings.app_name} Team
            """

            return self._send_email(
                to_email=to_email,
                subject=f"Password Reset - {settings.app_name}",
                html_body=html_body,
                text_body=text_body,
            )

        except Exception as e:
            print(f"Failed to send password reset email: {e}")
            # Fallback to plain text only
            return self._send_email(
                to_email=to_email,
                subject=f"Password Reset - {settings.app_name}",
                html_body=f"<html><body><pre>{text_body}</pre></body></html>",
                text_body=text_body,
            )

    def send_welcome_email(self, to_email: str, username: str) -> bool:
        """
        Send welcome email to new users.

        Args:
            to_email: User's email address
            username: User's username

        Returns:
            bool: True if email sent successfully
        """
        try:
            template = self.env.get_template("welcome.html")
            html_body = template.render(
                username=username,
                app_name=settings.app_name,
                login_url=f"{settings.app_url}/login",
            )

            text_body = f"""
            Welcome to {settings.app_name}, {username}!

            Your account has been successfully created.

            You can now log in at: {settings.app_url}/login

            Best regards,
            The {settings.app_name} Team
            """

            return self._send_email(
                to_email=to_email,
                subject=f"Welcome to {settings.app_name}!",
                html_body=html_body,
                text_body=text_body,
            )

        except Exception as e:
            print(f"Failed to send welcome email: {e}")
            return False

    def send_content_approval_notification(
        self,
        to_email: str,
        username: str,
        content_title: str,
        content_id: int,
        action: str,  # "submitted", "approved", "rejected"
    ) -> bool:
        """
        Send content approval notification email.

        Args:
            to_email: User's email address
            username: User's username
            content_title: Title of the content
            content_id: ID of the content
            action: Action type (submitted/approved/rejected)

        Returns:
            bool: True if email sent successfully
        """
        action_messages = {
            "submitted": f"Your content '{content_title}' has been submitted for approval.",
            "approved": f"Your content '{content_title}' has been approved and published!",
            "rejected": f"Your content '{content_title}' needs revision.",
        }

        message = action_messages.get(action, f"Update on '{content_title}'")
        content_url = f"{settings.app_url}/api/v1/content/{content_id}"

        try:
            template = self.env.get_template("content_notification.html")
            html_body = template.render(
                username=username,
                content_title=content_title,
                message=message,
                content_url=content_url,
                app_name=settings.app_name,
            )

            text_body = f"""
            Hello {username},

            {message}

            View content: {content_url}

            Best regards,
            The {settings.app_name} Team
            """

            return self._send_email(
                to_email=to_email,
                subject=f"Content Update - {settings.app_name}",
                html_body=html_body,
                text_body=text_body,
            )

        except Exception as e:
            print(f"Failed to send content notification email: {e}")
            return False

    def send_notification_email(
        self,
        to_email: str,
        username: str,
        subject: str,
        message: str,
    ) -> bool:
        """
        Send generic notification email.

        Args:
            to_email: User's email address
            username: User's username
            subject: Email subject
            message: Email message

        Returns:
            bool: True if email sent successfully
        """
        try:
            template = self.env.get_template("notification.html")
            html_body = template.render(
                username=username,
                message=message,
                app_name=settings.app_name,
            )

            text_body = f"""
            Hello {username},

            {message}

            Best regards,
            The {settings.app_name} Team
            """

            return self._send_email(
                to_email=to_email,
                subject=f"{subject} - {settings.app_name}",
                html_body=html_body,
                text_body=text_body,
            )

        except Exception as e:
            print(f"Failed to send notification email: {e}")
            return False


# Singleton instance
email_service = EmailService()
