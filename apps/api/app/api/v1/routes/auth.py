from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.auth import AuthResponse, AuthUser, GoogleLoginRequest
from app.services.auth_service import AuthError, AuthService

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

    return AuthResponse(access_token=token, user=AuthUser.model_validate(user))


@router.get("/me", response_model=AuthUser)
async def get_me(current_user: User = Depends(get_current_user)) -> AuthUser:
    return AuthUser.model_validate(current_user)
