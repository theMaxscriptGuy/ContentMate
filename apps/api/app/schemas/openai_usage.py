from pydantic import BaseModel


class OpenAIUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0

    @classmethod
    def from_response_usage(cls, usage: object | None) -> "OpenAIUsage":
        if usage is None:
            return cls()

        input_details = getattr(usage, "input_tokens_details", None)
        output_details = getattr(usage, "output_tokens_details", None)
        return cls(
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
            reasoning_tokens=int(getattr(output_details, "reasoning_tokens", 0) or 0),
            cached_tokens=int(getattr(input_details, "cached_tokens", 0) or 0),
        )


class OpenAIUsageBreakdown(BaseModel):
    strategy: OpenAIUsage = OpenAIUsage()
    longform: OpenAIUsage = OpenAIUsage()
    shortform: OpenAIUsage = OpenAIUsage()
    planner: OpenAIUsage = OpenAIUsage()
    total: OpenAIUsage = OpenAIUsage()
