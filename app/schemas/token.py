from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(..., min_length=32, description="Access token string.")
    token_type: str = Field(..., pattern="^Bearer$", description="Type of the token, typically 'Bearer'.")
    refresh_token: str | None = Field(None, description="Optional refresh token.")
    expires_in: int | None = Field(None, description="Time in seconds before token expires.")
