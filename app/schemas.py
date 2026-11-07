from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., min_length=1)


class Source(BaseModel):
    page: int | None = None
    article: str | None = None
    snippet: str


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        examples=["Which article is right to education?"],
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior conversation turns for context-aware follow-up questions.",
    )
    threshold: float | None = Field(
        default=None,
        ge=0.5,
        le=1.0,
        description="Cosine similarity cutoff (0.5 to 1.0). Leave null or omit to use default (0.90).",
        examples=[0.90],
    )
    run_tag: str | None = Field(
        default=None,
        max_length=64,
        examples=["test_run_1"],
    )
    dry_run: bool = False  # cache lookup only: no LLM call, no cache write


class AskResponse(BaseModel):
    answer: str
    standalone_question: str | None = None
    cache_hit: bool
    similarity: float | None
    matched_question: str | None
    sources: list[Source]
    latency_ms: float
    input_tokens: int
    output_tokens: int
