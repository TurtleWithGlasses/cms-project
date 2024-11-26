from pydantic import BaseModel, Field
from typing import Optional

class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Type of the token, typically 'bearer'")
    expires_in: Optional[int] = Field(None, description="Time in seconds until the token expires")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjMwNTk3NzUyfQ.tjK_JEPhV24vA",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        }
