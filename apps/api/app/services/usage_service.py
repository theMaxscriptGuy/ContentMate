from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.usage_event import UsageEvent
from app.db.models.user import User

settings = get_settings()

ANALYSIS_ACTION = "pipeline_analysis"


class UsageLimitExceededError(Exception):
    pass


@dataclass(slots=True)
class UsageStatus:
    daily_limit: int
    used_today: int
    remaining_today: int
    resets_at: datetime
    unlimited_access: bool = False


class UsageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_analysis_status(self, user_id: str) -> UsageStatus:
        user = await self._get_user(user_id)
        if user.has_unlimited_analysis:
            return UsageStatus(
                daily_limit=settings.daily_analysis_limit,
                used_today=0,
                remaining_today=0,
                resets_at=_tomorrow_utc(),
                unlimited_access=True,
            )
        used_today = await self._count_today(user_id=user_id, action_type=ANALYSIS_ACTION)
        remaining = max(settings.daily_analysis_limit - used_today, 0)
        return UsageStatus(
            daily_limit=settings.daily_analysis_limit,
            used_today=used_today,
            remaining_today=remaining,
            resets_at=_tomorrow_utc(),
        )

    async def assert_can_run_analysis(self, user_id: str) -> UsageStatus:
        status = await self.get_analysis_status(user_id=user_id)
        if status.unlimited_access:
            return status
        if status.remaining_today <= 0:
            raise UsageLimitExceededError(
                f"Daily analysis limit reached. You can run {status.daily_limit} analyses per day."
            )
        return status

    async def record_analysis(self, user_id: str, resource_id: str | None = None) -> UsageStatus:
        user = await self._get_user(user_id)
        if user.has_unlimited_analysis:
            return await self.get_analysis_status(user_id=user_id)
        self.session.add(
            UsageEvent(
                user_id=user_id,
                action_type=ANALYSIS_ACTION,
                resource_id=resource_id,
                counted_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        return await self.get_analysis_status(user_id=user_id)

    async def _count_today(self, user_id: str, action_type: str) -> int:
        today_start = datetime.combine(
            datetime.now(UTC).date(),
            time.min,
            tzinfo=UTC,
        )
        query: Select[tuple[int]] = select(func.count(UsageEvent.id)).where(
            UsageEvent.user_id == user_id,
            UsageEvent.action_type == action_type,
            UsageEvent.counted_at >= today_start,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def _get_user(self, user_id: str) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            raise UsageLimitExceededError("User not found.")
        return user


def _tomorrow_utc() -> datetime:
    today = datetime.now(UTC).date()
    return datetime.combine(today + timedelta(days=1), time.min, tzinfo=UTC)
