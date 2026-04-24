import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.rate_limit import enforce_auth_rate_limit
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.auth import AuthResponse, AuthUser, GoogleLoginRequest, UsageStatusResponse
from app.services.auth_service import AuthError, AuthService
from app.services.usage_service import UsageService, UsageStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/google", response_model=AuthResponse)
async def login_with_google(
    payload: GoogleLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AuthResponse:
    request_id = getattr(request.state, "request_id", "-")
    logger.debug(
        "auth.google.request request_id=%s credential_length=%s",
        request_id,
        len(payload.credential),
    )
    await enforce_auth_rate_limit(request)
    service = AuthService(session=session)
    try:
        user, token = await service.login_with_google(payload.credential)
    except AuthError as exc:
        logger.exception("auth.google.failed request_id=%s", request_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    usage = await UsageService(session=session).get_analysis_status(user_id=user.id)
    logger.debug(
        "auth.google.response request_id=%s user_id=%s email=%s analyses_remaining=%s",
        request_id,
        user.id,
        user.email,
        usage.remaining_today,
    )
    return AuthResponse(
        access_token=token,
        user=AuthUser.model_validate(user),
        usage=_serialize_usage(usage),
    )


@router.get("/me", response_model=AuthResponse)
async def get_me(
    current_user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AuthResponse:
    usage = await UsageService(session=session).get_analysis_status(user_id=current_user.id)
    logger.debug(
        "auth.me.response user_id=%s email=%s analyses_remaining=%s",
        current_user.id,
        current_user.email,
        usage.remaining_today,
    )
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
