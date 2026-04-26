from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.core.config import get_settings
from app.schemas.analysis import ChannelAnalysisPayload
from app.schemas.ideas import (
    LongformIdeasPayload,
    PlannerIdeasPayload,
    ShortformIdeasPayload,
)
from app.schemas.openai_usage import OpenAIUsage

settings = get_settings()

T = TypeVar("T", bound=BaseModel)


class OpenAIIdeasError(Exception):
    pass


@dataclass(slots=True)
class OpenAIParsedResult(Generic[T]):
    payload: T
    model_name: str
    usage: OpenAIUsage


class OpenAIIdeasClient:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.model = settings.openai_analysis_model

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def generate_longform_ideas(
        self,
        channel_title: str,
        analysis: ChannelAnalysisPayload,
        country_hint: str | None = None,
        trend_context: str | None = None,
    ) -> OpenAIParsedResult[LongformIdeasPayload]:
        prompt = self._build_channel_prompt(
            channel_title=channel_title,
            analysis=analysis,
            country_hint=country_hint,
            trend_context=trend_context,
        )
        return self._parse_payload(
            payload_type=LongformIdeasPayload,
            system_prompt=(
                "You are the long-form content agent for a creator strategy system. "
                "Generate practical YouTube video concepts, title hooks, and thumbnail "
                "angles that fit the supplied channel analysis."
            ),
            user_prompt=(
                f"{prompt}\n\n"
                "Task:\n"
                "- First, identify a small set of current trends or active themes that genuinely fit this channel.\n"
                "- Return trend-fit items only when there is a believable connection to the creator profile, niche, or current content direction.\n"
                "- If no supplied trend items clearly fit the channel, return an empty trend_fit list.\n"
                "- Mark trend relevance simply as high, medium, or low.\n"
                "- For each trend-fit item, explain why it fits and give one concrete execution angle.\n"
                "- Produce strong long-form YouTube video ideas.\n"
                "- Video ideas should feel publishable soon, not vague brainstorm notes.\n"
                "- For each video idea, include packaging help with 3 distinct title options, "
                "1 thumbnail concept, 1 thumbnail text overlay, 1 opening hook, and a short "
                "packaging rationale.\n"
                "- Title hooks should complement the video ideas, not repeat them mechanically.\n"
                "- Thumbnail angles should be visual and specific.\n"
                "- Packaging suggestions should feel tailored to the specific idea, not generic.\n"
                "- Return only schema-compliant data."
            ),
        )

    def generate_shortform_ideas(
        self,
        channel_title: str,
        analysis: ChannelAnalysisPayload,
        country_hint: str | None = None,
        trend_context: str | None = None,
    ) -> OpenAIParsedResult[ShortformIdeasPayload]:
        prompt = self._build_channel_prompt(
            channel_title=channel_title,
            analysis=analysis,
            country_hint=country_hint,
            trend_context=trend_context,
        )
        return self._parse_payload(
            payload_type=ShortformIdeasPayload,
            system_prompt=(
                "You are the short-form content agent for a creator strategy system. "
                "Generate sharp, hook-led short-form ideas for YouTube Shorts and "
                "similar vertical formats."
            ),
            user_prompt=(
                f"{prompt}\n\n"
                "Task:\n"
                "- Produce short-form ideas with a strong opening hook.\n"
                "- Concepts should be easy to execute as Shorts or clips.\n"
                "- Source moments can reference likely video moments or recurring themes.\n"
                "- Return only schema-compliant data."
            ),
        )

    def generate_planner(
        self,
        channel_title: str,
        analysis: ChannelAnalysisPayload,
        longform: LongformIdeasPayload,
        shortform: ShortformIdeasPayload,
        country_hint: str | None = None,
    ) -> OpenAIParsedResult[PlannerIdeasPayload]:
        region_label = country_hint or "global"
        today = datetime.now(UTC).date().isoformat()
        current_year = datetime.now(UTC).year
        return self._parse_payload(
            payload_type=PlannerIdeasPayload,
            system_prompt=(
                "You are the planning agent for a creator strategy system. "
                "Build a compact, realistic 4-week publishing plan from the supplied "
                "channel strategy plus proposed long-form and short-form ideas."
            ),
            user_prompt=(
                f"Today is {today}. The current year is {current_year}.\n"
                f"Channel: {channel_title}\n"
                f"Country/region hint: {region_label}\n\n"
                "Rules:\n"
                "- Sequence ideas in a sensible order across 4 weeks.\n"
                "- Mix long-form and short-form deliberately.\n"
                "- Keep the plan compact and realistic for one creator team.\n"
                "- Return only schema-compliant data.\n\n"
                f"Analysis:\n{analysis.model_dump_json(indent=2)}\n\n"
                f"Long-form ideas:\n{longform.model_dump_json(indent=2)}\n\n"
                f"Short-form ideas:\n{shortform.model_dump_json(indent=2)}"
            ),
        )

    def _parse_payload(
        self,
        *,
        payload_type: type[T],
        system_prompt: str,
        user_prompt: str,
    ) -> OpenAIParsedResult[T]:
        if not self.is_configured():
            raise OpenAIIdeasError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise OpenAIIdeasError(
                "OpenAI SDK is not installed. Run `pip install -e .` in apps/api."
            ) from exc

        client = OpenAI(api_key=self.api_key)

        try:
            response = client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=payload_type,
            )
        except Exception as exc:
            raise OpenAIIdeasError(f"OpenAI ideas generation failed: {exc}") from exc

        payload = response.output_parsed
        if payload is None:
            raise OpenAIIdeasError("OpenAI returned no parsed ideas.")

        return OpenAIParsedResult(
            payload=payload,
            model_name=self.model,
            usage=OpenAIUsage.from_response_usage(response.usage),
        )

    @staticmethod
    def _build_channel_prompt(
        *,
        channel_title: str,
        analysis: ChannelAnalysisPayload,
        country_hint: str | None,
        trend_context: str | None,
    ) -> str:
        today = datetime.now(UTC).date().isoformat()
        current_year = datetime.now(UTC).year
        region_label = country_hint or "global"
        trend_block = trend_context or "No live trend snapshot was available for this run."
        sparse_channel = (
            analysis.analyzed_video_count <= 5 or analysis.transcript_coverage_ratio < 0.35
        )
        evidence_guidance = (
            "- This is a sparse-signal or recently started channel. Keep ideas adjacent to what is already visible on the channel.\n"
            "- For sparse channels, prefer small, testable concept variations over big format pivots or fully mature channel strategies.\n"
            "- For sparse channels, avoid inventing advanced audience sophistication or broad brand authority that the evidence does not support.\n"
            "- For sparse channels, make recommendations feel realistic for an early creator trying to discover what resonates."
            if sparse_channel
            else "- The channel has enough evidence for more developed recommendations, but keep them grounded in the supplied analysis."
        )
        return f"""
Generate actionable content ideas for this YouTube channel.

Rules:
- Ground every idea in the supplied channel analysis.
- Prefer ideas the creator can realistically produce.
- Make titles specific, clickable, and honest.
- Treat today as {today}. The current year is {current_year}.
- If a title includes a year, it must use {current_year}, never a past year like 2024 or 2025,
  unless the idea is explicitly a retrospective or historical comparison.
- Use current trend context from {region_label} only when it genuinely fits the channel niche.
- Do not force unrelated trends into ideas just because they are currently popular.
- Keep recommendations consistent with the creator profile and current channel maturity.
- For early or sparse channels, bias toward adjacent experiments that can teach the creator what works next.
- Return only data that fits the provided schema.
{evidence_guidance}

Channel: {channel_title}
Country/region hint: {region_label}

Current trend context:
{trend_block}

Analysis:
{analysis.model_dump_json(indent=2)}
""".strip()
