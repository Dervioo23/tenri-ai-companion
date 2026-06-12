"""Retrieval and prompt-construction boundary for Tenri's response brain."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

logger = logging.getLogger("AICompanion.BrainStage")

_SLIDE_EXPLANATION_RE = re.compile(
    r"\b(?:jelaskan|terangkan|paparkan|uraikan|bahas|ulas|ceritakan)\b"
    r".{0,40}\bslide\b|\bslide\b.{0,40}"
    r"\b(?:jelaskan|terangkan|paparkan|uraikan|bahas|ulas|ceritakan)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class BrainResult:
    messages: list
    context_chunks: list
    context_str: str
    enriched_query: str
    is_slide_explanation: bool
    retrieval_seconds: float

    @property
    def no_context(self) -> bool:
        return not bool(self.context_chunks)


class BrainStage:
    def __init__(
        self,
        *,
        retrieval,
        query_rewriter,
        prompt_builder,
        deprioritized_slide_sources: set[str] | frozenset[str],
    ) -> None:
        self.retrieval = retrieval
        self.query_rewriter = query_rewriter
        self.prompt_builder = prompt_builder
        self.deprioritized_slide_sources = frozenset(deprioritized_slide_sources)

    def prepare(
        self,
        *,
        user_input: str,
        history: list,
        slide: dict | None,
        slide_str: str,
        narrative_str: str,
        vision_context: dict | None = None,
    ) -> BrainResult:
        is_slide_explanation = self.is_slide_explanation_request(user_input)
        if is_slide_explanation:
            enriched_query = self.slide_explanation_query(slide, user_input)
        else:
            enriched_query = self.query_rewriter.rewrite(user_input, slide, history)

        started_at = time.monotonic()
        chunks = self.retrieval.search(enriched_query)
        if is_slide_explanation:
            chunks = self.filter_slide_explanation_chunks(
                chunks,
                self.deprioritized_slide_sources,
            )
        if chunks and not self.retrieval.has_strong_match(chunks):
            logger.info("Retrieval discarded: weak query/source overlap.")
            chunks = []
        retrieval_seconds = round(time.monotonic() - started_at, 2)
        context_str = self.retrieval.format_context(chunks)

        if is_slide_explanation:
            messages = self.prompt_builder.build_slide_explanation_messages(
                user_input=user_input,
                history=history,
                slide_str=slide_str,
                context_str=context_str,
                narrative_str=narrative_str,
            )
        else:
            messages = self.prompt_builder.build_messages(
                user_input=user_input,
                history=history,
                vision_context=vision_context,
                slide_str=slide_str,
                context_str=context_str,
                no_context=not bool(chunks),
                narrative_str=narrative_str,
            )

        return BrainResult(
            messages=messages,
            context_chunks=chunks,
            context_str=context_str,
            enriched_query=enriched_query,
            is_slide_explanation=is_slide_explanation,
            retrieval_seconds=retrieval_seconds,
        )

    def interruption_context(self, topic: str, slide: dict | None) -> tuple[str, bool]:
        parts = [topic] if topic else []
        if slide:
            parts.append(slide.get("title", ""))
            parts.extend(slide.get("topics", []))
        query = " ".join(part for part in parts if part).strip()
        if not query:
            return "", True
        chunks = self.retrieval.search(query)
        if chunks and not self.retrieval.has_strong_match(chunks):
            logger.info("Interruption retrieval discarded: weak query/source overlap.")
            chunks = []
        return self.retrieval.format_context(chunks) if chunks else "", not bool(chunks)

    @staticmethod
    def is_slide_explanation_request(user_input: str) -> bool:
        return bool(_SLIDE_EXPLANATION_RE.search(user_input or ""))

    @staticmethod
    def slide_explanation_query(slide: dict | None, fallback: str) -> str:
        if not slide:
            return fallback
        parts = [
            slide.get("subtitle", ""),
            slide.get("title", ""),
            " ".join(slide.get("topics", [])),
            slide.get("presenter_notes", ""),
            slide.get("tenri_role", ""),
        ]
        return " ".join(part for part in parts if part).strip() or fallback

    @staticmethod
    def filter_slide_explanation_chunks(
        chunks: list,
        deprioritized_sources: set[str] | frozenset[str],
    ) -> list:
        if not chunks:
            return []
        preferred = [
            chunk for chunk in chunks
            if str(chunk.get("source_id", "")).lower()
            not in deprioritized_sources
        ]
        return preferred or chunks
