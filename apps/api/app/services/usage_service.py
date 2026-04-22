from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.usage_event import UsageEvent

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


class UsageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_analysis_status(self, user_id: str) -> UsageStatus:
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
        if status.remaining_today <= 0:
            raise UsageLimitExceededError(
                f"Daily analysis limit reached. You can run {status.daily_limit} analyses per day."
            )
        return status

    async def record_analysis(self, user_id: str, resource_id: str | None = None) -> UsageStatus:
        self.session.add(
            UsageEvent(
                user_id=user_id,
                action_type=ANALYSIS_ACTION,
                resource_id=resource_id,
                counted_at=datetime.now(timezone.utc),
            )
        )
        await self.session.commit()
        return await self.get_analysis_status(user_id=user_id)

    async def _count_today(self, user_id: str, action_type: str) -> int:
        today_start = datetime.combine(
            datetime.now(timezone.utc).date(),
            time.min,
            tzinfo=timezone.utc,
        )
        query: Select[tuple[int]] = select(func.count(UsageEvent.id)).where(
            UsageEvent.user_id == user_id,
            UsageEvent.action_type == action_type,
            UsageEvent.counted_at >= today_start,
        )
        result = await self.session.execute(query)
        return int(result.scalar_one())


def _tomorrow_utc() -> datetime:
    today = datetime.now(timezone.utc).date()
    return datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc)
