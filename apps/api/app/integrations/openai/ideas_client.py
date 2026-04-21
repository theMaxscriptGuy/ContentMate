from dataclasses import dataclass

from app.core.config import get_settings
from app.schemas.analysis import ChannelAnalysisPayload
from app.schemas.ideas import ContentIdeasPayload

settings = get_settings()


class OpenAIIdeasError(Exception):
    pass


@dataclass(slots=True)
class OpenAIIdeasResult:
    payload: ContentIdeasPayload
    model_name: str


class OpenAIIdeasClient:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.model = settings.openai_analysis_model

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def generate_ideas(
        self,
        channel_title: str,
        analysis: ChannelAnalysisPayload,
    ) -> OpenAIIdeasResult:
        if not self.is_configured():
            raise OpenAIIdeasError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise OpenAIIdeasError(
                "OpenAI SDK is not installed. Run `pip install -e .` in apps/api."
            ) from exc

        prompt = self._build_prompt(channel_title=channel_title, analysis=analysis)
        client = OpenAI(api_key=self.api_key)

        try:
            response = client.responses.parse(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are a YouTube strategist for creator-led channels. "
                            "Generate concrete, production-ready ideas."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                text_format=ContentIdeasPayload,
            )
        except Exception as exc:
            raise OpenAIIdeasError(f"OpenAI ideas generation failed: {exc}") from exc

        payload = response.output_parsed
        if payload is None:
            raise OpenAIIdeasError("OpenAI returned no parsed ideas.")
        return OpenAIIdeasResult(payload=payload, model_name=self.model)

    @staticmethod
    def _build_prompt(channel_title: str, analysis: ChannelAnalysisPayload) -> str:
        return f"""
Generate actionable content ideas for this YouTube channel.

Rules:
- Ground every idea in the supplied channel analysis.
- Prefer ideas the creator can realistically produce.
- Make titles specific, clickable, and honest.
- Shorts ideas should be clip-friendly and easy to produce.
- Thumbnail angles should describe visual composition, not just text.
- The calendar should be a compact 4-week publishing plan.
- Return only data that fits the provided schema.

Channel: {channel_title}

Analysis:
{analysis.model_dump_json(indent=2)}
""".strip()
