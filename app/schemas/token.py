from pydantic import BaseModel, Field
from typing import Optional

class Token(BaseModel):
    access_token: str = Field(..., min_length=32, description="Access token string.")
    token_type: str = Field(..., pattern="^Bearer$", description="Type of the token, typically 'Bearer'.")
    refresh_token: Optional[str] = Field(None, description="Optional refresh token.")
    expires_in: Optional[int] = Field(None, description="Time in seconds before token expires.")
