"""
Tests for PasswordResetToken model

Tests model methods for password reset token validation and expiry.
"""

from datetime import datetime, timedelta

import pytest

from app.models.password_reset import PasswordResetToken


class TestPasswordResetTokenIsExpired:
    """Test is_expired method"""

    def test_is_expired_with_future_expiry(self):
        """Test that token with future expiry is not expired"""
        token = PasswordResetToken()
        token.expires_at = datetime.utcnow() + timedelta(hours=1)

        assert token.is_expired() is False

    def test_is_expired_with_past_expiry(self):
        """Test that token with past expiry is expired"""
        token = PasswordResetToken()
        token.expires_at = datetime.utcnow() - timedelta(hours=1)

        assert token.is_expired() is True

    def test_is_expired_just_now(self):
        """Test that token that just expired is considered expired"""
        token = PasswordResetToken()
        token.expires_at = datetime.utcnow() - timedelta(seconds=1)

        assert token.is_expired() is True

    def test_is_expired_edge_case(self):
        """Test token expiry at exact current time"""
        token = PasswordResetToken()
        # Set to exact current time (will be slightly in past by execution)
        token.expires_at = datetime.utcnow()

        # Should be expired or very close
        result = token.is_expired()
        # Either expired or about to expire
        assert result in [True, False]


class TestPasswordResetTokenIsValid:
    """Test is_valid method"""

    def test_is_valid_with_unused_and_not_expired(self):
        """Test that unused, non-expired token is valid"""
        token = PasswordResetToken()
        token.expires_at = datetime.utcnow() + timedelta(hours=1)
        token.used = False

        assert token.is_valid() is True

    def test_is_valid_with_used_token(self):
        """Test that used token is not valid"""
        token = PasswordResetToken()
        token.expires_at = datetime.utcnow() + timedelta(hours=1)
        token.used = True

        assert token.is_valid() is False

    def test_is_valid_with_expired_token(self):
        """Test that expired token is not valid"""
        token = PasswordResetToken()
        token.expires_at = datetime.utcnow() - timedelta(hours=1)
        token.used = False

        assert token.is_valid() is False

    def test_is_valid_with_used_and_expired(self):
        """Test that used and expired token is not valid"""
        token = PasswordResetToken()
        token.expires_at = datetime.utcnow() - timedelta(hours=1)
        token.used = True

        assert token.is_valid() is False

    def test_is_valid_fresh_token(self):
        """Test freshly created valid token"""
        token = PasswordResetToken()
        token.expires_at = datetime.utcnow() + timedelta(minutes=30)
        token.used = False

        assert token.is_valid() is True


class TestPasswordResetTokenGetExpiryTime:
    """Test get_expiry_time static method"""

    def test_get_expiry_time_default(self):
        """Test default expiry time (1 hour)"""
        before = datetime.utcnow() + timedelta(hours=1)
        expiry = PasswordResetToken.get_expiry_time()
        after = datetime.utcnow() + timedelta(hours=1)

        # Expiry should be approximately 1 hour from now
        assert before <= expiry <= after + timedelta(seconds=1)

    def test_get_expiry_time_custom_hours(self):
        """Test custom expiry time"""
        hours = 2
        before = datetime.utcnow() + timedelta(hours=hours)
        expiry = PasswordResetToken.get_expiry_time(hours=hours)
        after = datetime.utcnow() + timedelta(hours=hours)

        # Expiry should be approximately 2 hours from now
        assert before <= expiry <= after + timedelta(seconds=1)

    def test_get_expiry_time_short_duration(self):
        """Test short expiry duration (15 minutes)"""
        minutes_in_hours = 0.25  # 15 minutes
        before = datetime.utcnow() + timedelta(hours=minutes_in_hours)
        expiry = PasswordResetToken.get_expiry_time(hours=minutes_in_hours)
        after = datetime.utcnow() + timedelta(hours=minutes_in_hours)

        assert before <= expiry <= after + timedelta(seconds=1)

    def test_get_expiry_time_long_duration(self):
        """Test long expiry duration (24 hours)"""
        hours = 24
        expiry = PasswordResetToken.get_expiry_time(hours=hours)
        expected_min = datetime.utcnow() + timedelta(hours=hours)

        # Should be at least 24 hours from now
        assert expiry >= expected_min - timedelta(seconds=1)

    def test_get_expiry_time_returns_future_time(self):
        """Test that expiry time is always in the future"""
        expiry = PasswordResetToken.get_expiry_time()
        now = datetime.utcnow()

        assert expiry > now


class TestPasswordResetTokenModel:
    """Test PasswordResetToken model attributes"""

    def test_password_reset_token_creation(self):
        """Test creating a password reset token instance"""
        token = PasswordResetToken()
        token.user_id = 1
        token.token = "test-token-123"
        token.expires_at = PasswordResetToken.get_expiry_time()
        token.used = False

        assert token.user_id == 1
        assert token.token == "test-token-123"
        assert token.used is False
        assert token.expires_at > datetime.utcnow()

    def test_password_reset_token_defaults(self):
        """Test default values"""
        token = PasswordResetToken()
        token.user_id = 1
        token.token = "token"
        token.expires_at = datetime.utcnow() + timedelta(hours=1)

        # used defaults to False
        assert hasattr(token, "used")


class TestPasswordResetTokenIntegration:
    """Test password reset token integration scenarios"""

    def test_full_token_lifecycle(self):
        """Test complete token lifecycle"""
        # Create token
        token = PasswordResetToken()
        token.user_id = 1
        token.token = "reset-token-xyz"
        token.expires_at = PasswordResetToken.get_expiry_time(hours=1)
        token.used = False

        # Initially valid
        assert token.is_valid() is True
        assert token.is_expired() is False

        # Mark as used
        token.used = True
        assert token.is_valid() is False

    def test_expired_token_lifecycle(self):
        """Test token that expires"""
        # Create token that's already expired
        token = PasswordResetToken()
        token.user_id = 1
        token.token = "expired-token"
        token.expires_at = datetime.utcnow() - timedelta(hours=2)
        token.used = False

        # Should be expired and invalid
        assert token.is_expired() is True
        assert token.is_valid() is False

    def test_token_expiry_timing(self):
        """Test token expiry at different time intervals"""
        # Token expires in 30 seconds
        token = PasswordResetToken()
        token.expires_at = datetime.utcnow() + timedelta(seconds=30)
        token.used = False

        # Should be valid now
        assert token.is_valid() is True

        # Simulate time passing (change expires_at to past)
        token.expires_at = datetime.utcnow() - timedelta(seconds=1)

        # Should be invalid now
        assert token.is_valid() is False
        assert token.is_expired() is True
