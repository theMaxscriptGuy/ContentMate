from __future__ import annotations

import logging
from typing import TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent_workflow import (
    AgentEvidencePackage,
    AgentTranscriptEvidence,
    AgentVideoEvidence,
    AgentWorkflowMeta,
)
from app.schemas.analysis import ChannelAnalysisResponse
from app.schemas.channel import ChannelSyncResponse, VideoSummary
from app.schemas.ideas import GenerateIdeasResponse
from app.schemas.openai_usage import OpenAIUsage, OpenAIUsageBreakdown
from app.schemas.pipeline import RunPipelineResponse
from app.schemas.transcript import ChannelTranscriptSyncResponse
from app.services.agent_strategy_service import AgentStrategyService
from app.services.ideas_service import IdeasGenerationContext, IdeasService
from app.services.transcript_service import TranscriptService
from app.services.youtube_service import ChannelNotFoundError, YouTubeService
from app.workers.queue import enqueue_channel_sync_job


class AgentWorkflowError(Exception):
    pass


logger = logging.getLogger(__name__)


def _sample_titles(videos: list[AgentVideoEvidence], limit: int = 3) -> list[str]:
    return [video.title for video in videos[:limit]]


class AgentWorkflowState(TypedDict, total=False):
    source_kind: str
    channel_url: str
    video_url: str
    user_id: str
    force_transcript_refresh: bool
    force_ideas_refresh: bool
    include_videos: bool
    include_streams: bool
    include_shorts: bool
    channel_id: str
    target_video_id: str
    channel_sync: ChannelSyncResponse
    transcript_sync: ChannelTranscriptSyncResponse
    evidence_package: AgentEvidencePackage
    analysis: ChannelAnalysisResponse
    strategy_usage: OpenAIUsage
    ideas_context: IdeasGenerationContext
    longform_ideas: object
    shortform_ideas: object
    planner_ideas: object
    ideas_usage: OpenAIUsageBreakdown
    ideas_response: GenerateIdeasResponse


class AgentWorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.youtube_service = YouTubeService(session=session)
        self.transcript_service = TranscriptService(session=session)
        self.strategy_service = AgentStrategyService(session=session)
        self.ideas_service = IdeasService(session=session)
        self.graph = self._build_graph().compile()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentWorkflowState)
        graph.add_node("sync_channel", self._sync_channel_node)
        graph.add_node("fetch_transcripts", self._fetch_transcripts_node)
        graph.add_node("build_evidence", self._build_evidence_node)
        graph.add_node("strategy_agent", self._strategy_agent_node)
        graph.add_node("load_cached_ideas", self._load_cached_ideas_node)
        graph.add_node("longform_agent", self._longform_agent_node)
        graph.add_node("shortform_agent", self._shortform_agent_node)
        graph.add_node("planner_agent", self._planner_agent_node)
        graph.add_node("assemble_ideas", self._assemble_ideas_node)
        graph.add_edge(START, "sync_channel")
        graph.add_edge("sync_channel", "fetch_transcripts")
        graph.add_edge("fetch_transcripts", "build_evidence")
        graph.add_edge("build_evidence", "strategy_agent")
        graph.add_edge("strategy_agent", "load_cached_ideas")
        graph.add_conditional_edges(
            "load_cached_ideas",
            self._route_after_cached_ideas,
            {
                "end": END,
                "longform_agent": "longform_agent",
            },
        )
        graph.add_edge("longform_agent", "shortform_agent")
        graph.add_edge("shortform_agent", "planner_agent")
        graph.add_edge("planner_agent", "assemble_ideas")
        graph.add_edge("assemble_ideas", END)
        return graph

    async def run(
        self,
        channel_url: str,
        user_id: str,
        force_transcript_refresh: bool = False,
        force_ideas_refresh: bool = True,
        include_videos: bool = True,
        include_streams: bool = True,
        include_shorts: bool = True,
    ) -> RunPipelineResponse:
        logger.debug(
            "agent.workflow.start channel_url=%s user_id=%s "
            "include_videos=%s include_streams=%s include_shorts=%s",
            channel_url,
            user_id,
            include_videos,
            include_streams,
            include_shorts,
        )
        state = await self.graph.ainvoke(
            {
                "source_kind": "channel",
                "channel_url": channel_url,
                "user_id": user_id,
                "force_transcript_refresh": force_transcript_refresh,
                "force_ideas_refresh": force_ideas_refresh,
                "include_videos": include_videos,
                "include_streams": include_streams,
                "include_shorts": include_shorts,
            }
        )
        return self._finalize_state(state)

    async def run_video(
        self,
        video_url: str,
        user_id: str,
        force_transcript_refresh: bool = False,
        force_ideas_refresh: bool = True,
    ) -> RunPipelineResponse:
        logger.debug("agent.workflow.start video_url=%s user_id=%s", video_url, user_id)
        state = await self.graph.ainvoke(
            {
                "source_kind": "video",
                "video_url": video_url,
                "user_id": user_id,
                "force_transcript_refresh": force_transcript_refresh,
                "force_ideas_refresh": force_ideas_refresh,
                "include_videos": True,
                "include_streams": False,
                "include_shorts": False,
            }
        )
        return self._finalize_state(state)

    def _finalize_state(self, state: AgentWorkflowState) -> RunPipelineResponse:
        channel_sync = state.get("channel_sync")
        transcript_sync = state.get("transcript_sync")
        analysis = state.get("analysis")
        ideas_response = state.get("ideas_response")
        evidence_package = state.get("evidence_package")
        if (
            channel_sync is None
            or transcript_sync is None
            or analysis is None
            or ideas_response is None
            or evidence_package is None
        ):
            raise AgentWorkflowError("Agent workflow did not complete successfully.")

        analyzed_videos = [
            VideoSummary(
                id=video.video_id,
                youtube_video_id=video.youtube_video_id,
                title=video.title,
                description=video.description,
                published_at=video.published_at,
                duration_seconds=video.duration_seconds,
                view_count=video.view_count,
                like_count=video.like_count,
                comment_count=video.comment_count,
                thumbnail_url=video.thumbnail_url,
                transcript_status=video.transcript_status,
                analysis_status="completed",
            )
            for video in evidence_package.videos
        ]
        response_channel_sync = channel_sync.model_copy(
            update={
                "videos": analyzed_videos,
            }
        )

        logger.debug(
            "agent.workflow.completed channel_id=%s title=%s transcript_fetched=%s "
            "transcript_failed=%s ideas_model=%s strategy_model=%s "
            "strategy_tokens=%s ideas_tokens=%s total_tokens=%s",
            channel_sync.channel.id,
            channel_sync.channel.title,
            transcript_sync.fetched_transcripts,
            transcript_sync.failed_transcripts,
            ideas_response.ideas.model_name,
            analysis.model_name,
            state.get("strategy_usage", OpenAIUsage()).total_tokens,
            state.get("ideas_usage", OpenAIUsageBreakdown()).total.total_tokens,
            (
                state.get("strategy_usage", OpenAIUsage()).total_tokens
                + state.get("ideas_usage", OpenAIUsageBreakdown()).total.total_tokens
            ),
        )
        return RunPipelineResponse(
            job_id=transcript_sync.job_id,
            channel_sync=response_channel_sync,
            transcript_sync=transcript_sync,
            analysis=analysis,
            ideas=ideas_response.ideas,
        )
    async def _sync_channel_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        source_kind = state.get("source_kind", "channel")
        logger.debug(
            "agent.workflow.node.sync_channel.start source_kind=%s target=%s",
            source_kind,
            state.get("video_url") if source_kind == "video" else state.get("channel_url"),
        )
        try:
            if source_kind == "video":
                sync_result = await self.youtube_service.sync_video_from_url(
                    video_url=state["video_url"],
                    user_id=state["user_id"],
                )
            else:
                sync_result = await self.youtube_service.sync_channel_from_url(
                    channel_url=state["channel_url"],
                    user_id=state["user_id"],
                    include_videos=state["include_videos"],
                    include_streams=state["include_streams"],
                    include_shorts=state["include_shorts"],
                )
        except ChannelNotFoundError as exc:
            raise AgentWorkflowError(str(exc)) from exc

        channel_job_id = await enqueue_channel_sync_job(channel_id=sync_result.channel.id)
        logger.debug(
            "agent.workflow.node.sync_channel.completed channel_id=%s "
            "title=%s videos=%s sample_titles=%s",
            sync_result.channel.id,
            sync_result.channel.title,
            len(sync_result.videos),
            [video.title for video in sync_result.videos[:3]],
        )
        next_state: AgentWorkflowState = {
            "channel_id": str(sync_result.channel.id),
            "channel_sync": ChannelSyncResponse(
                job_id=channel_job_id,
                channel=sync_result.channel,
                videos=sync_result.videos,
            ),
        }
        if source_kind == "video" and sync_result.videos:
            next_state["target_video_id"] = str(sync_result.videos[0].id)
        return next_state

    async def _fetch_transcripts_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        logger.debug(
            "agent.workflow.node.fetch_transcripts.start channel_id=%s",
            state["channel_id"],
        )
        if state.get("target_video_id"):
            single = await self.transcript_service.fetch_transcript_for_video(
                video_id=UUID(state["target_video_id"]),
                force=state["force_transcript_refresh"],
                include_text=False,
            )
            transcript_sync = ChannelTranscriptSyncResponse(
                job_id=single.job_id,
                channel_id=UUID(state["channel_id"]),
                processed_videos=1,
                fetched_transcripts=1 if single.transcript.status == "completed" else 0,
                failed_transcripts=1 if single.transcript.status == "failed" else 0,
                transcripts=[single.transcript],
            )
        else:
            transcript_sync = await self.transcript_service.fetch_transcripts_for_channel(
                channel_id=UUID(state["channel_id"]),
                include_existing=state["force_transcript_refresh"],
                include_text=False,
            )
        logger.debug(
            "agent.workflow.node.fetch_transcripts.completed channel_id=%s fetched=%s failed=%s",
            state["channel_id"],
            transcript_sync.fetched_transcripts,
            transcript_sync.failed_transcripts,
        )
        return {"transcript_sync": transcript_sync}

    async def _build_evidence_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        channel_sync = state["channel_sync"]
        logger.debug("agent.workflow.node.build_evidence.start channel_id=%s", state["channel_id"])
        if state.get("target_video_id"):
            video = await self.transcript_service.repository.get_video(state["target_video_id"])
            videos = [video] if video is not None else []
        else:
            videos = await self.youtube_service.repository.list_active_videos_for_channel(
                state["channel_id"]
            )
        transcript_rows: list[AgentTranscriptEvidence] = []
        joined_transcripts: list[str] = []
        analyzed_transcript_count = 0

        for video in videos:
            transcript = await self.transcript_service.get_transcript_record(video.id)
            if transcript is None:
                continue
            transcript_rows.append(
                AgentTranscriptEvidence(
                    video_id=transcript.video_id,
                    status=transcript.status,
                    language=transcript.language,
                    source=transcript.source,
                    chunk_count=transcript.chunk_count,
                    error_message=transcript.error_message,
                    cleaned_text=transcript.cleaned_text,
                )
            )
            if transcript.status == "completed" and transcript.cleaned_text:
                analyzed_transcript_count += 1
                joined_transcripts.append(transcript.cleaned_text)

        selected_content_types = []
        if state["include_videos"]:
            selected_content_types.append("videos")
        if state["include_streams"]:
            selected_content_types.append("streams")
        if state["include_shorts"]:
            selected_content_types.append("shorts")

        analysis_mode = "transcript-backed" if analyzed_transcript_count > 0 else "metadata-only"
        evidence = AgentEvidencePackage(
            channel_id=state["channel_id"],
            channel_title=channel_sync.channel.title,
            channel_description=channel_sync.channel.description,
            workflow_meta=AgentWorkflowMeta(
                source_kind=state.get("source_kind", "channel"),
                analysis_mode=analysis_mode,
                transcript_coverage_ratio=round(analyzed_transcript_count / max(len(videos), 1), 2),
                analyzed_video_count=len(videos),
                analyzed_transcript_count=analyzed_transcript_count,
                selected_content_types=selected_content_types,
            ),
            videos=[
                AgentVideoEvidence(
                    video_id=video.id,
                    youtube_video_id=video.youtube_video_id,
                    title=video.title,
                    description=video.description,
                    published_at=video.published_at,
                    duration_seconds=video.duration_seconds,
                    view_count=video.view_count,
                    like_count=video.like_count,
                    comment_count=video.comment_count,
                    thumbnail_url=video.thumbnail_url,
                    transcript_status=video.transcript_status,
                )
                for video in videos
            ],
            transcripts=transcript_rows,
            joined_transcript_text=self._build_joined_text(
                videos,
                transcript_rows,
                joined_transcripts,
            ),
        )
        logger.debug(
            "agent.workflow.node.build_evidence.completed channel_id=%s "
            "mode=%s content_types=%s videos=%s transcripts=%s sample_titles=%s",
            state["channel_id"],
            analysis_mode,
            ",".join(selected_content_types),
            len(videos),
            analyzed_transcript_count,
            _sample_titles(evidence.videos),
        )
        return {"evidence_package": evidence}

    async def _strategy_agent_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        logger.debug("agent.workflow.node.strategy_agent.start channel_id=%s", state["channel_id"])
        result = await self.strategy_service.generate_strategy(
            channel_id=UUID(state["channel_id"]),
            evidence=state["evidence_package"],
        )
        analysis = result.analysis
        logger.debug(
            "agent.workflow.node.strategy_agent.completed channel_id=%s "
            "model=%s niche=%s audience=%s total_tokens=%s",
            state["channel_id"],
            analysis.model_name,
            analysis.result.niche,
            analysis.result.target_audience,
            result.usage.total_tokens,
        )
        return {"analysis": analysis, "strategy_usage": result.usage}

    async def _load_cached_ideas_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        logger.debug(
            "agent.workflow.node.load_cached_ideas.start channel_id=%s",
            state["channel_id"],
        )
        ideas_response = await self.ideas_service.get_cached_ideas_response(
            channel_id=UUID(state["channel_id"]),
            force_refresh=state["force_ideas_refresh"],
        )
        if ideas_response is not None:
            logger.debug(
                "agent.workflow.node.load_cached_ideas.completed channel_id=%s cache_hit=true "
                "video_ideas=%s shorts_ideas=%s calendar_items=%s",
                state["channel_id"],
                len(ideas_response.ideas.result.video_ideas),
                len(ideas_response.ideas.result.shorts_ideas),
                len(ideas_response.ideas.result.content_calendar),
            )
            return {"ideas_response": ideas_response}

        ideas_context = await self.ideas_service.build_generation_context(
            channel_id=UUID(state["channel_id"])
        )
        logger.debug(
            "agent.workflow.node.load_cached_ideas.completed channel_id=%s cache_hit=false "
            "trend_geo=%s trend_loaded=%s",
            state["channel_id"],
            ideas_context.trend_geo,
            bool(ideas_context.trend_items),
        )
        return {"ideas_context": ideas_context}

    @staticmethod
    def _route_after_cached_ideas(state: AgentWorkflowState) -> str:
        return "end" if state.get("ideas_response") is not None else "longform_agent"

    async def _longform_agent_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        logger.debug("agent.workflow.node.longform_agent.start channel_id=%s", state["channel_id"])
        result = await self.ideas_service.generate_longform_ideas(state["ideas_context"])
        logger.debug(
            "agent.workflow.node.longform_agent.completed channel_id=%s model=%s video_ideas=%s",
            state["channel_id"],
            result.model_name,
            len(result.payload.video_ideas),
        )
        return {"longform_ideas": result}

    async def _shortform_agent_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        logger.debug("agent.workflow.node.shortform_agent.start channel_id=%s", state["channel_id"])
        result = await self.ideas_service.generate_shortform_ideas(state["ideas_context"])
        logger.debug(
            "agent.workflow.node.shortform_agent.completed channel_id=%s model=%s shorts_ideas=%s",
            state["channel_id"],
            result.model_name,
            len(result.payload.shorts_ideas),
        )
        return {"shortform_ideas": result}

    async def _planner_agent_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        logger.debug("agent.workflow.node.planner_agent.start channel_id=%s", state["channel_id"])
        result = await self.ideas_service.generate_planner(
            context=state["ideas_context"],
            longform=state["longform_ideas"].payload,
            shortform=state["shortform_ideas"].payload,
        )
        logger.debug(
            "agent.workflow.node.planner_agent.completed channel_id=%s model=%s calendar_items=%s",
            state["channel_id"],
            result.model_name,
            len(result.payload.content_calendar),
        )
        return {"planner_ideas": result}

    async def _assemble_ideas_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        logger.debug("agent.workflow.node.assemble_ideas.start channel_id=%s", state["channel_id"])
        artifacts = await self.ideas_service.persist_generated_ideas(
            context=state["ideas_context"],
            longform=state["longform_ideas"],
            shortform=state["shortform_ideas"],
            planner=state["planner_ideas"],
        )
        ideas_response = artifacts.response
        logger.debug(
            "agent.workflow.node.assemble_ideas.completed channel_id=%s model=%s "
            "video_ideas=%s shorts_ideas=%s calendar_items=%s total_tokens=%s",
            state["channel_id"],
            ideas_response.ideas.model_name,
            len(ideas_response.ideas.result.video_ideas),
            len(ideas_response.ideas.result.shorts_ideas),
            len(ideas_response.ideas.result.content_calendar),
            artifacts.usage.total.total_tokens,
        )
        return {"ideas_response": ideas_response, "ideas_usage": artifacts.usage}

    @staticmethod
    def _build_joined_text(videos, transcript_rows, joined_transcripts: list[str]) -> str:
        transcript_by_video_id = {item.video_id: item for item in transcript_rows}
        evidence_blocks: list[str] = []
        for video in videos:
            parts = [video.title or ""]
            if video.description:
                parts.append(video.description)
            metadata_text = " ".join(part.strip() for part in parts if part.strip())

            transcript_text = None
            transcript = transcript_by_video_id.get(video.id)
            if transcript and transcript.status == "completed":
                transcript_text = transcript.cleaned_text

            block_parts = [metadata_text] if metadata_text else []
            if transcript_text:
                block_parts.append(transcript_text)

            if block_parts:
                evidence_blocks.append("\n\n".join(block_parts))

        if evidence_blocks:
            return "\n\n".join(evidence_blocks)

        return "\n\n".join(joined_transcripts)
