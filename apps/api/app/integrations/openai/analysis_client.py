from dataclasses import dataclass

from app.core.config import get_settings
from app.schemas.analysis import ChannelAnalysisPayload
from app.schemas.openai_usage import OpenAIUsage

settings = get_settings()


class OpenAIAnalysisError(Exception):
    pass


@dataclass(slots=True)
class OpenAIAnalysisResult:
    payload: ChannelAnalysisPayload
    model_name: str
    usage: OpenAIUsage


class OpenAIAnalysisClient:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.model = settings.openai_analysis_model
        self.max_transcript_chars = settings.openai_analysis_max_transcript_chars

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def analyze_channel(
        self,
        channel_title: str,
        videos: list[dict],
        transcript_text: str,
        transcript_coverage_ratio: float,
        analyzed_video_count: int,
        analyzed_transcript_count: int,
    ) -> OpenAIAnalysisResult:
        if not self.is_configured():
            raise OpenAIAnalysisError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise OpenAIAnalysisError(
                "OpenAI SDK is not installed. Run `pip install -e .` in apps/api."
            ) from exc

        client = OpenAI(api_key=self.api_key)
        prompt = self._build_prompt(
            channel_title=channel_title,
            videos=videos,
            transcript_text=transcript_text[: self.max_transcript_chars],
            transcript_coverage_ratio=transcript_coverage_ratio,
            analyzed_video_count=analyzed_video_count,
            analyzed_transcript_count=analyzed_transcript_count,
        )

        try:
            response = client.responses.parse(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior YouTube content strategist. "
                            "Analyze supplied YouTube channel evidence and return grounded, "
                            "practical insights."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                text_format=ChannelAnalysisPayload,
            )
        except Exception as exc:
            raise OpenAIAnalysisError(f"OpenAI analysis failed: {exc}") from exc

        payload = response.output_parsed
        if payload is None:
            raise OpenAIAnalysisError("OpenAI returned no parsed analysis.")

        payload.transcript_coverage_ratio = transcript_coverage_ratio
        payload.analyzed_video_count = analyzed_video_count
        payload.analyzed_transcript_count = analyzed_transcript_count
        return OpenAIAnalysisResult(
            payload=payload,
            model_name=self.model,
            usage=OpenAIUsage.from_response_usage(response.usage),
        )

    @staticmethod
    def _build_prompt(
        channel_title: str,
        videos: list[dict],
        transcript_text: str,
        transcript_coverage_ratio: float,
        analyzed_video_count: int,
        analyzed_transcript_count: int,
    ) -> str:
        sparse_channel = analyzed_video_count <= 5 or transcript_coverage_ratio < 0.35
        evidence_guidance = (
            "- This is a sparse-signal or early-stage channel. Be careful, modest, and explicit about uncertainty.\n"
            "- For sparse channels, describe the niche as an emerging direction or current content lane when needed, not a locked-in brand identity.\n"
            "- For sparse channels, infer the audience conservatively from current topics and packaging, not from imagined future scale.\n"
            "- For sparse channels, make the creator profile about observable tendencies in topic choice, tone, and packaging style.\n"
            "- For sparse channels, avoid pretending there is a proven repeatable format if the evidence does not show one."
            if sparse_channel
            else "- This channel has enough evidence to form more confident strategic observations, but still stay grounded in the supplied material."
        )
        return f"""
Analyze this YouTube channel using the provided video metadata and transcript text when available.

Rules:
- Base claims only on the supplied transcript text and metadata.
- Build a creator profile/persona that reflects how this creator tends to package and deliver content.
- If the channel evidence is sparse, recent, or limited, stay conservative.
- For sparse channels, avoid overconfident niche claims and avoid assuming a mature audience profile.
- For sparse channels, frame strengths as signals or tendencies, not established truths.
- If transcript coverage is 0, clearly infer from titles/descriptions only and reflect that
  limitation in strengths or gaps.
- Prefer semantic themes over raw repeated words.
- Topics should be concise phrases, not filler words.
- Mention counts may be approximate but should reflect transcript prominence.
- Strengths and gaps should be actionable for the creator.
- The creator profile should feel specific to this channel, not like a generic niche summary.
- Return only data that fits the provided schema.
{evidence_guidance}

Channel: {channel_title}
Transcript coverage ratio: {transcript_coverage_ratio}
Analyzed videos: {analyzed_video_count}
Analyzed transcripts: {analyzed_transcript_count}

Videos:
{videos}

Transcript:
{transcript_text}
""".strip()
