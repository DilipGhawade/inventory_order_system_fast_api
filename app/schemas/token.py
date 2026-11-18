from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(description="JWT short-lived access token")
    refresh_token: str = Field(description="JWT long-lived refresh token")
    token_type: str = Field(default="bearer", description="OAuth2 token scheme")
    expires_in: int = Field(description="Access token expiration time in seconds")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=16, description="Valid JWT refresh token")


class TokenPayload(BaseModel):
    sub: str
    role: str
    type: str
    jti: str