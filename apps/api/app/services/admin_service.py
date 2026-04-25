from __future__ import annotations

from sqlalchemy import Select, desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.channel import Channel
from app.db.models.generated_content import GeneratedContent
from app.db.models.user import User
from app.schemas.admin import (
    AdminActivityChannel,
    AdminActivityResponse,
    AdminActivitySummary,
    AdminActivityUser,
    AdminAnalysisActivityItem,
)


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_activity(self, limit: int = 100) -> AdminActivityResponse:
        total_users = await self._count(select(func.count()).select_from(User))
        total_channel_analyses = await self._count(
            select(func.count())
            .select_from(GeneratedContent)
            .where(GeneratedContent.content_type == "channel_analysis")
        )
        total_channels = await self._count(
            select(func.count(distinct(GeneratedContent.channel_id)))
            .select_from(GeneratedContent)
            .where(
                GeneratedContent.content_type == "channel_analysis",
                GeneratedContent.channel_id.is_not(None),
            )
        )

        query: Select[tuple[GeneratedContent, User, Channel]] = (
            select(GeneratedContent, User, Channel)
            .join(User, GeneratedContent.user_id == User.id)
            .join(Channel, GeneratedContent.channel_id == Channel.id)
            .where(GeneratedContent.content_type == "channel_analysis")
            .order_by(desc(GeneratedContent.created_at))
            .limit(limit)
        )
        result = await self.session.execute(query)

        activity: list[AdminAnalysisActivityItem] = []
        for analysis, user, channel in result.all():
            prompt_input = analysis.prompt_input or {}
            activity.append(
                AdminAnalysisActivityItem(
                    analysis_id=analysis.id,
                    analyzed_at=analysis.created_at,
                    source_kind=str(prompt_input.get("source_kind") or "channel"),
                    analyzed_video_count=int(prompt_input.get("analyzed_video_count") or 0),
                    analyzed_transcript_count=int(
                        prompt_input.get("analyzed_transcript_count") or 0
                    ),
                    model_name=analysis.model_name,
                    user=AdminActivityUser(
                        id=user.id,
                        email=user.email,
                        name=user.name,
                    ),
                    channel=AdminActivityChannel(
                        id=channel.id,
                        title=channel.title,
                        channel_url=channel.channel_url,
                        subscriber_count=channel.subscriber_count,
                    ),
                )
            )

        return AdminActivityResponse(
            summary=AdminActivitySummary(
                total_users=total_users,
                total_channel_analyses=total_channel_analyses,
                total_channels=total_channels,
            ),
            activity=activity,
        )

    async def _count(self, query: Select[tuple[int]]) -> int:
        result = await self.session.execute(query)
        return int(result.scalar_one() or 0)
