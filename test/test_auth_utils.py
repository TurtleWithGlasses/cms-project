"""
Tests for authentication utility functions (JWT token creation and validation)
"""
import pytest
from datetime import timedelta
from jose import jwt
from fastapi import HTTPException
from app.utils.auth_utils import create_access_token, decode_access_token
from app.constants import SECRET_KEY, ALGORITHM


class TestCreateAccessToken:
    """Test JWT token creation"""

    def test_create_token_with_default_expiration(self):
        """Test creating token with default expiration time"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)

        # Decode to verify structure
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert "exp" in payload

    def test_create_token_with_custom_expiration(self):
        """Test creating token with custom expiration delta"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires_delta)

        assert token is not None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test@example.com"

    def test_create_token_with_additional_claims(self):
        """Test creating token with additional custom claims"""
        data = {
            "sub": "test@example.com",
            "role": "admin",
            "user_id": 123
        }
        token = create_access_token(data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert payload["role"] == "admin"
        assert payload["user_id"] == 123

    def test_create_token_with_empty_data(self):
        """Test creating token with empty data dictionary"""
        data = {}
        token = create_access_token(data)

        assert token is not None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload


class TestDecodeAccessToken:
    """Test JWT token decoding and validation"""

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        email = decode_access_token(token)
        assert email == "test@example.com"

    def test_decode_token_without_sub_claim(self):
        """Test decoding token without 'sub' claim raises exception"""
        # Create token without 'sub' claim
        to_encode = {"user_id": 123, "exp": None}
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)

        assert exc_info.value.status_code == 401
        assert "sub" in exc_info.value.detail.lower()

    def test_decode_expired_token(self):
        """Test decoding an expired token raises exception"""
        # Create an already-expired token
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta=expires_delta)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_decode_invalid_token(self):
        """Test decoding an invalid/malformed token"""
        invalid_token = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(invalid_token)

        assert exc_info.value.status_code == 401

    def test_decode_token_with_wrong_secret(self):
        """Test decoding token with wrong secret key"""
        # Create token with different secret
        data = {"sub": "test@example.com"}
        wrong_token = jwt.encode(data, "wrong_secret_key", algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(wrong_token)

        assert exc_info.value.status_code == 401

    def test_decode_token_with_wrong_algorithm(self):
        """Test decoding token created with different algorithm"""
        data = {"sub": "test@example.com"}
        # Create token with HS512 instead of HS256
        wrong_algo_token = jwt.encode(data, SECRET_KEY, algorithm="HS512")

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(wrong_algo_token)

        assert exc_info.value.status_code == 401


class TestTokenRoundTrip:
    """Test creating and decoding tokens in sequence"""

    def test_create_and_decode_roundtrip(self):
        """Test that created token can be decoded successfully"""
        test_emails = [
            "user@example.com",
            "admin@test.com",
            "editor@company.org"
        ]

        for email in test_emails:
            data = {"sub": email}
            token = create_access_token(data)
            decoded_email = decode_access_token(token)
            assert decoded_email == email

    def test_multiple_tokens_different_users(self):
        """Test creating and decoding multiple tokens for different users"""
        users = [
            {"sub": "user1@example.com", "role": "user"},
            {"sub": "user2@example.com", "role": "admin"},
            {"sub": "user3@example.com", "role": "editor"}
        ]

        tokens = []
        for user_data in users:
            token = create_access_token(user_data)
            tokens.append(token)

        # Decode all tokens and verify
        for idx, token in enumerate(tokens):
            decoded_email = decode_access_token(token)
            assert decoded_email == users[idx]["sub"]
