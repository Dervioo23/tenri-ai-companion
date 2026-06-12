"""Typed events exchanged between Tenri runtime stages."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PipelineEventType(str, Enum):
    RUNTIME_STARTED = "runtime.started"
    CAPTURE_STARTED = "capture.started"
    UTTERANCE_CAPTURED = "capture.completed"
    INTENT_CLASSIFIED = "router.intent_classified"
    RETRIEVAL_COMPLETED = "brain.retrieval_completed"
    RESPONSE_COMPLETED = "response.completed"
    TURN_SKIPPED = "turn.skipped"
    TURN_FAILED = "turn.failed"
    RUNTIME_STOPPING = "runtime.stopping"


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    """A privacy-safe runtime event.

    Payloads should contain stage metadata and timings, never raw microphone
    transcripts or generated response text.
    """

    type: PipelineEventType
    turn_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)
