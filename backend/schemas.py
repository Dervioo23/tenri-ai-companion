"""Request/response models for the Tenri web backend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class RouteRequest(BaseModel):
    transcript: str = Field(..., description="What the presenter said (STT output).")
    slide_index: int = Field(0, description="Client's current 0-based slide index.")
    history: list[Message] = Field(default_factory=list, description="Prior turns.")
    in_conversation: bool = Field(
        False, description="True if inside the conversation window (opened by name)."
    )
    quiet_mode: bool = Field(
        False, description="True if presenter closed the dialog (needs name to reopen)."
    )


class LlmParams(BaseModel):
    model: str
    max_tokens: int
    max_sentences: int
    max_chars: int


class RouteResponse(BaseModel):
    # answer | navigate | slide_info | slide_list | wake_ack | close | monitor | ignore
    action: str
    reason: str = ""
    intent: str = ""
    # answer payload (browser calls Groq with these + the user's key)
    messages: list[Message] | None = None
    llm: LlmParams | None = None
    context_str: str = ""
    sources: list[str] = Field(default_factory=list)
    # spoken text for non-LLM actions (wake_ack / close)
    text: str = ""
    # slide state
    slide_index: int = 0
    slide_str: str = ""
    slides: list[str] = Field(default_factory=list)
    # conversation-state hints for the client to apply
    extend_window: bool = False
    clear_quiet: bool = False
    set_quiet: bool = False
    clear_window: bool = False


class VerifyRequest(BaseModel):
    response: str
    context_str: str


class VerifyResponse(BaseModel):
    final_text: str
    overridden: bool


class HealthResponse(BaseModel):
    status: str
    slides: int
    chunks: int
    live_model: str
    detail: dict[str, Any] = Field(default_factory=dict)
