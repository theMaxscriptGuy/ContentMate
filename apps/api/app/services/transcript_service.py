import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.transcript.client import TranscriptClient, TranscriptProviderError
from app.repositories.channel_repository import ChannelRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.schemas.transcript import (
    ChannelTranscriptSyncResponse,
    TranscriptChunkPreview,
    TranscriptRefreshResponse,
    TranscriptResponse,
)
from app.utils.text import chunk_text, clean_transcript_text, is_probably_transcript_text
from app.workers.queue import create_job, set_job_status


class VideoNotFoundError(Exception):
    pass


@dataclass(slots=True)
class _FetchResult:
    transcript: object
    created_or_updated: bool


class TranscriptService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.channel_repository = ChannelRepository(session=session)
        self.repository = TranscriptRepository(session=session)
        self.client = TranscriptClient()

    async def fetch_transcripts_for_channel(
        self,
        channel_id: UUID,
        include_existing: bool = False,
        include_text: bool = False,
    ) -> ChannelTranscriptSyncResponse:
        channel = await self.channel_repository.get_by_id(str(channel_id))
        if channel is None:
            raise VideoNotFoundError("Channel not found")

        videos = await self.channel_repository.list_active_videos_for_channel(str(channel_id))
        job_id = await create_job(job_namespace="transcripts", resource_id=str(channel_id))
        await set_job_status(job_id=job_id, status="processing")

        responses: list[TranscriptResponse] = []
        fetched_count = 0
        failed_count = 0

        for video in videos:
            transcript = await self.repository.get_transcript_by_video_id(video.id)
            if transcript and transcript.status == "completed" and not include_existing:
                responses.append(self._serialize_transcript(transcript, include_text=include_text))
                continue

            result = await self._fetch_and_store(video.id, force=include_existing)
            responses.append(
                self._serialize_transcript(result.transcript, include_text=include_text)
            )
            if result.transcript.status == "completed" and result.created_or_updated:
                fetched_count += 1
            if result.transcript.status == "failed":
                failed_count += 1

        await set_job_status(job_id=job_id, status="completed")
        return ChannelTranscriptSyncResponse(
            job_id=job_id,
            channel_id=channel_id,
            processed_videos=len(videos),
            fetched_transcripts=fetched_count,
            failed_transcripts=failed_count,
            transcripts=responses,
        )

    async def fetch_transcript_for_video(
        self,
        video_id: UUID,
        force: bool = False,
        include_text: bool = False,
    ) -> TranscriptRefreshResponse:
        job_id = await create_job(job_namespace="transcripts", resource_id=str(video_id))
        await set_job_status(job_id=job_id, status="processing")
        result = await self._fetch_and_store(str(video_id), force=force)
        await set_job_status(job_id=job_id, status="completed")
        return TranscriptRefreshResponse(
            job_id=job_id,
            transcript=self._serialize_transcript(result.transcript, include_text=include_text),
        )

    async def get_transcript_for_video(
        self,
        video_id: UUID,
        include_text: bool = True,
    ) -> TranscriptResponse | None:
        transcript = await self.repository.get_transcript_by_video_id(str(video_id))
        if transcript is None:
            return None
        return self._serialize_transcript(transcript, include_text=include_text)

    async def get_transcript_record(self, video_id: str):
        return await self.repository.get_transcript_by_video_id(video_id)

    async def _fetch_and_store(self, video_id: str, force: bool) -> _FetchResult:
        video = await self.repository.get_video(video_id)
        if video is None:
            raise VideoNotFoundError("Video not found")

        transcript = await self.repository.get_transcript_by_video_id(video.id)
        if transcript and transcript.status == "completed" and not force:
            return _FetchResult(transcript=transcript, created_or_updated=False)

        if transcript is None:
            from app.db.models.transcript import Transcript

            transcript = Transcript(video_id=video.id, status="pending")
            self.session.add(transcript)
            await self.session.flush()

        try:
            payload = await asyncio.to_thread(self.client.fetch_transcript, video.youtube_video_id)
            cleaned_text = clean_transcript_text(payload.raw_text)
            raw_is_transcript = is_probably_transcript_text(payload.raw_text)
            cleaned_is_transcript = is_probably_transcript_text(cleaned_text)
            if not raw_is_transcript or not cleaned_is_transcript:
                raise TranscriptProviderError(
                    "Transcript provider returned YouTube page/player config instead of captions."
                )
            chunks = chunk_text(cleaned_text)
            transcript.language = payload.language
            transcript.source = payload.source
            transcript.raw_text = payload.raw_text
            transcript.cleaned_text = cleaned_text
            transcript.chunk_count = len(chunks)
            transcript.status = "completed"
            transcript.error_message = None
            transcript.fetched_at = datetime.now(timezone.utc)
            video.transcript_status = "completed"
        except TranscriptProviderError as exc:
            transcript.status = "failed"
            transcript.error_message = str(exc)
            transcript.fetched_at = datetime.now(timezone.utc)
            video.transcript_status = "failed"

        await self.session.commit()
        await self.session.refresh(transcript)
        return _FetchResult(transcript=transcript, created_or_updated=True)

    def _serialize_transcript(self, transcript, include_text: bool = True) -> TranscriptResponse:
        chunk_previews = [
            TranscriptChunkPreview(index=index, text=chunk)
            for index, chunk in enumerate(chunk_text(transcript.cleaned_text or "")[:3], start=1)
        ]
        return TranscriptResponse(
            id=UUID(transcript.id),
            video_id=UUID(transcript.video_id),
            language=transcript.language,
            source=transcript.source,
            cleaned_text=transcript.cleaned_text if include_text else None,
            chunk_count=transcript.chunk_count,
            status=transcript.status,
            error_message=transcript.error_message,
            fetched_at=transcript.fetched_at,
            chunks=chunk_previews,
        )
