from uuid import UUID

from pydantic import BaseModel


class GoogleLoginRequest(BaseModel):
    credential: str


class AuthUser(BaseModel):
    id: UUID
    email: str
    name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}


class UsageStatusResponse(BaseModel):
    daily_analysis_limit: int
    analyses_used_today: int
    analyses_remaining_today: int
    resets_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser
    usage: UsageStatusResponse
