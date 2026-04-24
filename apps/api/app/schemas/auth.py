from uuid import UUID

from pydantic import BaseModel, Field


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=5000)


class VoucherRedeemRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)


class AuthUser(BaseModel):
    id: UUID
    email: str
    name: str | None
    avatar_url: str | None
    has_unlimited_analysis: bool

    model_config = {"from_attributes": True}


class UsageStatusResponse(BaseModel):
    daily_analysis_limit: int
    analyses_used_today: int
    analyses_remaining_today: int
    unlimited_access: bool
    analysis_credit_balance: int
    resets_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser
    usage: UsageStatusResponse
