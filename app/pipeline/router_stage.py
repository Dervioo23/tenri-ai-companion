"""Intent routing boundary for one normalized presenter utterance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.services.intent_classifier import Intent, IntentResult


class RouteAction(str, Enum):
    ANSWER = "answer"
    CLOSE = "close"
    IGNORE_AUDIENCE = "ignore_audience"
    MONITOR = "monitor"
    WAKE_ACK = "wake_ack"
    IGNORE_ACK = "ignore_ack"


@dataclass(frozen=True, slots=True)
class RouteDecision:
    action: RouteAction
    intent_result: IntentResult
    query: str
    was_direct_call: bool
    has_question: bool
    normalized_ack: str = ""


class RouterStage:
    """Classify an utterance and derive its side-effect-free route."""

    def __init__(
        self,
        classifier,
        *,
        wake_words: list[str],
        audience_markers: set[str] | frozenset[str],
        closing_phrases: set[str] | frozenset[str],
        acknowledgment_phrases: set[str] | frozenset[str],
        question_detector,
    ) -> None:
        self.classifier = classifier
        self.wake_words = wake_words
        self.audience_markers = audience_markers
        self.closing_phrases = closing_phrases
        self.acknowledgment_phrases = acknowledgment_phrases
        self.question_detector = question_detector

    def route(
        self,
        user_input: str,
        *,
        in_conversation: bool,
        quiet_mode: bool,
    ) -> RouteDecision:
        result = self.classifier.classify(
            user_input,
            wake_words=self.wake_words,
            audience_markers=self.audience_markers,
            closing_phrases=self.closing_phrases,
            in_conversation=in_conversation,
            quiet_mode=quiet_mode,
        )
        query = result.query if result.query is not None else user_input
        has_question = self.question_detector(query)
        normalized_ack = self._normalize_ack(query)

        if result.intent is Intent.CLOSING_TENRI:
            action = RouteAction.CLOSE
        elif result.intent is Intent.ASKING_AUDIENCE:
            action = RouteAction.IGNORE_AUDIENCE
        elif result.intent in (Intent.EXPLAINING, Intent.AMBIENT, Intent.NOISE):
            action = RouteAction.MONITOR
        elif result.was_wake_word and not query.strip():
            action = RouteAction.WAKE_ACK
        elif (
            not result.was_wake_word
            and not has_question
            and normalized_ack in self.acknowledgment_phrases
        ):
            action = RouteAction.IGNORE_ACK
        else:
            action = RouteAction.ANSWER

        return RouteDecision(
            action=action,
            intent_result=result,
            query=query,
            was_direct_call=result.was_wake_word,
            has_question=has_question,
            normalized_ack=normalized_ack,
        )

    @staticmethod
    def _normalize_ack(text: str) -> str:
        normalized = re.sub(r"[^\w\s]", " ", text.lower())
        return re.sub(r"\s+", " ", normalized).strip()
