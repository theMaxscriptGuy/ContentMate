from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.auth import AuthResponse, AuthUser, GoogleLoginRequest, UsageStatusResponse
from app.services.auth_service import AuthError, AuthService
from app.services.usage_service import UsageService, UsageStatus

router = APIRouter()


@router.post("/google", response_model=AuthResponse)
async def login_with_google(
    payload: GoogleLoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    service = AuthService(session=session)
    try:
        user, token = await service.login_with_google(payload.credential)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    usage = await UsageService(session=session).get_analysis_status(user_id=user.id)
    return AuthResponse(
        access_token=token,
        user=AuthUser.model_validate(user),
        usage=_serialize_usage(usage),
    )


@router.get("/me", response_model=AuthResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    usage = await UsageService(session=session).get_analysis_status(user_id=current_user.id)
    return AuthResponse(
        access_token="",
        user=AuthUser.model_validate(current_user),
        usage=_serialize_usage(usage),
    )


def _serialize_usage(status: UsageStatus) -> UsageStatusResponse:
    return UsageStatusResponse(
        daily_analysis_limit=status.daily_limit,
        analyses_used_today=status.used_today,
        analyses_remaining_today=status.remaining_today,
        resets_at=status.resets_at.isoformat(),
    )
