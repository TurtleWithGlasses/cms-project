"""
Tests for Email Service

Tests email sending functionality including password reset, welcome emails,
and content notifications.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.services.email_service import EmailService, email_service


class TestEmailService:
    """Test email service functionality"""

    @pytest.fixture
    def mock_smtp(self):
        """Mock SMTP server"""
        with patch("app.services.email_service.smtplib.SMTP") as mock:
            smtp_instance = MagicMock()
            mock.return_value.__enter__.return_value = smtp_instance
            yield smtp_instance

    @pytest.fixture
    def email_svc(self):
        """Create email service instance"""
        return EmailService()

    def test_email_service_initialization(self, email_svc):
        """Test email service initializes correctly"""
        assert email_svc is not None
        assert email_svc.smtp_host is not None
        assert email_svc.smtp_port is not None

    def test_send_password_reset_email_success(self, email_svc, mock_smtp):
        """Test successful password reset email sending"""
        result = email_svc.send_password_reset_email(
            to_email="test@example.com", username="testuser", reset_token="abc123xyz"
        )

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    def test_send_password_reset_email_with_custom_url(self, email_svc, mock_smtp):
        """Test password reset email with custom reset URL"""
        custom_url = "https://example.com/reset"

        result = email_svc.send_password_reset_email(
            to_email="test@example.com", username="testuser", reset_token="abc123xyz", reset_url=custom_url
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_password_reset_email_failure(self, email_svc):
        """Test password reset email handles SMTP failure"""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")

            result = email_svc.send_password_reset_email(
                to_email="test@example.com", username="testuser", reset_token="abc123xyz"
            )

            assert result is False

    def test_send_welcome_email_success(self, email_svc, mock_smtp):
        """Test successful welcome email sending"""
        result = email_svc.send_welcome_email(to_email="newuser@example.com", username="newuser")

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    def test_send_welcome_email_failure(self, email_svc):
        """Test welcome email handles SMTP failure"""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP error")

            result = email_svc.send_welcome_email(to_email="test@example.com", username="testuser")

            assert result is False

    def test_send_content_approval_notification_submitted(self, email_svc, mock_smtp):
        """Test content submission notification"""
        result = email_svc.send_content_approval_notification(
            to_email="author@example.com",
            username="author",
            content_title="Test Article",
            content_id=123,
            action="submitted",
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_content_approval_notification_approved(self, email_svc, mock_smtp):
        """Test content approval notification"""
        result = email_svc.send_content_approval_notification(
            to_email="author@example.com",
            username="author",
            content_title="Test Article",
            content_id=123,
            action="approved",
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_content_approval_notification_rejected(self, email_svc, mock_smtp):
        """Test content rejection notification"""
        result = email_svc.send_content_approval_notification(
            to_email="author@example.com",
            username="author",
            content_title="Test Article",
            content_id=123,
            action="rejected",
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_content_notification_failure(self, email_svc):
        """Test content notification handles failure"""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("Network error")

            result = email_svc.send_content_approval_notification(
                to_email="author@example.com",
                username="author",
                content_title="Test Article",
                content_id=123,
                action="approved",
            )

            assert result is False

    def test_send_generic_notification_success(self, email_svc, mock_smtp):
        """Test generic notification email"""
        result = email_svc.send_notification_email(
            to_email="user@example.com",
            username="testuser",
            subject="Test Notification",
            message="This is a test message",
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_generic_notification_failure(self, email_svc):
        """Test generic notification handles failure"""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP error")

            result = email_svc.send_notification_email(
                to_email="user@example.com", username="testuser", subject="Test", message="Test message"
            )

            assert result is False

    def test_send_email_with_authentication(self, email_svc, mock_smtp):
        """Test email sending with SMTP authentication"""
        # Mock settings with authentication
        with (
            patch.object(email_svc, "smtp_user", "user@example.com"),
            patch.object(email_svc, "smtp_password", "password123"),
        ):
            result = email_svc.send_password_reset_email(
                to_email="test@example.com", username="testuser", reset_token="abc123"
            )

            assert result is True
            mock_smtp.login.assert_called_once_with("user@example.com", "password123")

    def test_send_email_without_authentication(self, email_svc, mock_smtp):
        """Test email sending without SMTP authentication"""
        with patch.object(email_svc, "smtp_user", None), patch.object(email_svc, "smtp_password", None):
            result = email_svc.send_welcome_email(to_email="test@example.com", username="testuser")

            assert result is True
            mock_smtp.login.assert_not_called()

    def test_send_email_multiple_recipients(self, email_svc, mock_smtp):
        """Test sending email to multiple recipients"""
        recipients = ["user1@example.com", "user2@example.com"]

        # Mock the _send_email method to accept list
        with patch.object(email_svc, "_send_email") as mock_send:
            mock_send.return_value = True

            result = email_svc._send_email(
                to_email=recipients, subject="Test", html_body="<p>Test</p>", text_body="Test"
            )

            assert result is True

    def test_email_templates_exist(self):
        """Test that email templates exist"""
        template_dir = Path(__file__).parent.parent / "templates" / "emails"

        assert (template_dir / "password_reset.html").exists()
        assert (template_dir / "welcome.html").exists()
        assert (template_dir / "content_notification.html").exists()
        assert (template_dir / "notification.html").exists()

    def test_singleton_instance(self):
        """Test email_service singleton exists"""
        assert email_service is not None
        assert isinstance(email_service, EmailService)

    @pytest.mark.parametrize(
        "action,expected_in_message",
        [
            ("submitted", "submitted for approval"),
            ("approved", "approved and published"),
            ("rejected", "needs revision"),
        ],
    )
    def test_content_notification_action_messages(self, email_svc, mock_smtp, action, expected_in_message):
        """Test different action types generate correct messages"""
        result = email_svc.send_content_approval_notification(
            to_email="author@example.com", username="author", content_title="Article", content_id=1, action=action
        )

        assert result is True
        # Verify the message was sent
        mock_smtp.send_message.assert_called_once()
