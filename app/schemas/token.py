from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(..., min_length=32, description="Access token string.")
    token_type: str = Field(..., pattern="^Bearer$", description="Type of the token, typically 'Bearer'.")
    refresh_token: str | None = Field(None, description="Optional refresh token.")
    expires_in: int | None = Field(None, description="Time in seconds before token expires.")


class TokenWith2FA(BaseModel):
    """Token response that includes 2FA status."""

    access_token: str | None = Field(None, description="Access token (only provided if 2FA not required or verified).")
    token_type: str = Field("Bearer", description="Type of the token.")
    requires_2fa: bool = Field(False, description="Whether 2FA verification is required.")
    temp_token: str | None = Field(None, description="Temporary token for 2FA verification (if 2FA required).")
    expires_in: int | None = Field(None, description="Time in seconds before token expires.")


class TwoFactorVerifyRequest(BaseModel):
    """Request to verify 2FA code during login."""

    temp_token: str = Field(..., description="Temporary token from initial login.")
    code: str = Field(..., min_length=6, max_length=10, description="TOTP or backup code.")
