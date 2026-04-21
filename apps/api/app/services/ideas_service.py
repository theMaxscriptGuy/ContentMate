from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_content import GeneratedContent
from app.integrations.openai.ideas_client import OpenAIIdeasClient, OpenAIIdeasError
from app.repositories.channel_repository import ChannelRepository
from app.repositories.generated_content_repository import GeneratedContentRepository
from app.schemas.analysis import ChannelAnalysisPayload
from app.schemas.ideas import (
    ContentIdeasPayload,
    ContentIdeasResponse,
    GenerateIdeasResponse,
)
from app.workers.queue import create_job, set_job_status


class IdeasGenerationError(Exception):
    pass


class IdeasService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.channel_repository = ChannelRepository(session=session)
        self.generated_content_repository = GeneratedContentRepository(session=session)
        self.openai_ideas_client = OpenAIIdeasClient()

    async def generate_channel_ideas(
        self,
        channel_id: UUID,
        force_refresh: bool = False,
    ) -> GenerateIdeasResponse:
        channel = await self.channel_repository.get_by_id(str(channel_id))
        if channel is None:
            raise IdeasGenerationError("Channel not found")

        if not force_refresh:
            cached = await self.generated_content_repository.get_latest_for_channel(
                channel_id=str(channel_id),
                content_type="content_ideas",
            )
            if cached and cached.result_json:
                job_id = await create_job(job_namespace="ideas", resource_id=str(channel_id))
                await set_job_status(job_id=job_id, status="completed")
                return GenerateIdeasResponse(
                    job_id=job_id,
                    ideas=self._serialize_ideas(cached),
                )

        analysis_row = await self.generated_content_repository.get_latest_for_channel(
            channel_id=str(channel_id),
            content_type="channel_analysis",
        )
        if analysis_row is None or not analysis_row.result_json:
            raise IdeasGenerationError("Channel analysis not found. Run analysis first.")

        analysis = ChannelAnalysisPayload.model_validate(analysis_row.result_json)
        job_id = await create_job(job_namespace="ideas", resource_id=str(channel_id))
        await set_job_status(job_id=job_id, status="processing")

        try:
            result = self.openai_ideas_client.generate_ideas(
                channel_title=channel.title,
                analysis=analysis,
            )
        except OpenAIIdeasError as exc:
            await set_job_status(job_id=job_id, status="failed")
            raise IdeasGenerationError(str(exc)) from exc

        ideas_row = GeneratedContent(
            channel_id=channel.id,
            content_type="content_ideas",
            prompt_input={
                "analysis_id": analysis_row.id,
                "analysis_model": analysis_row.model_name,
            },
            result_json=result.payload.model_dump(),
            status="completed",
            model_name=f"openai:{result.model_name}",
        )
        self.session.add(ideas_row)
        await self.session.commit()
        await self.session.refresh(ideas_row)
        await set_job_status(job_id=job_id, status="completed")

        return GenerateIdeasResponse(
            job_id=job_id,
            ideas=self._serialize_ideas(ideas_row),
        )

    async def get_channel_ideas(self, channel_id: UUID) -> ContentIdeasResponse | None:
        record = await self.generated_content_repository.get_latest_for_channel(
            channel_id=str(channel_id),
            content_type="content_ideas",
        )
        if record is None or not record.result_json:
            return None
        return self._serialize_ideas(record)

    @staticmethod
    def _serialize_ideas(record: GeneratedContent) -> ContentIdeasResponse:
        return ContentIdeasResponse(
            id=UUID(record.id),
            channel_id=UUID(record.channel_id),
            content_type=record.content_type,
            status=record.status,
            model_name=record.model_name,
            created_at=record.created_at,
            result=ContentIdeasPayload.model_validate(record.result_json),
        )
