from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.admin import AdminActivityResponse
from app.services.admin_service import AdminService

router = APIRouter()


@router.get("/activity", response_model=AdminActivityResponse)
async def get_admin_activity(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> AdminActivityResponse:
    return await AdminService(session=session).get_activity()
