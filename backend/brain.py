"""TenriBrain — stateless orchestration over the reused brain modules.

Replicates the decision logic of ``InteractionLoop.run()`` that is relevant to a
web turn, minus everything audio/key-related. Built once at startup; every method
is safe to call concurrently because per-request slide state is derived from the
client's ``slide_index`` (no shared mutable state is written).
"""

from __future__ import annotations

import logging
import random

from app.config import Config
from app.core.prompt_builder import PromptBuilder
from app.services.answer_verifier import AnswerVerifier
from app.services.document_loader import DocumentLoader
from app.services.intent_classifier import IntentClassifier
from app.services.presentation_tracker import PresentationTracker
from app.services.query_rewriter import QueryRewriter
from app.services.retrieval import RetrievalService
from app.pipeline.router_stage import RouteAction, RouterStage

from backend import constants as C

logger = logging.getLogger("TenriWeb.Brain")


class TenriBrain:
    def __init__(self) -> None:
        # Load knowledge base + slides once.
        chunks = DocumentLoader().load_all_documents()
        self.retrieval = RetrievalService(chunks)
        self.prompt_builder = PromptBuilder()
        self.query_rewriter = QueryRewriter()
        self.answer_verifier = AnswerVerifier()

        tracker = PresentationTracker()
        self._slides = tracker.all_slides()
        self._chunk_count = len(chunks)

        self.router = RouterStage(
            IntentClassifier(),
            wake_words=Config.WAKE_WORDS,
            audience_markers=C.AUDIENCE_MARKERS,
            closing_phrases=C.CLOSING_PHRASES,
            acknowledgment_phrases=C.ACKNOWLEDGMENT_PHRASES,
            question_detector=C.has_question_word,
        )
        self.live_model = (Config.GROQ_LIVE_MODEL or Config.GROQ_MODEL).strip()
        logger.info(
            "TenriBrain ready: %d slides, %d chunks, model=%s",
            len(self._slides), self._chunk_count, self.live_model,
        )

    # ------------------------------------------------------------------ helpers

    @property
    def slide_count(self) -> int:
        return len(self._slides)

    @property
    def chunk_count(self) -> int:
        return self._chunk_count

    def _tracker_at(self, slide_index: int) -> PresentationTracker:
        """A per-request tracker view positioned at the client's slide index.

        Shares the immutable slide list; the index is local to this view so
        concurrent requests never collide.
        """
        t = PresentationTracker.__new__(PresentationTracker)
        t._slides = self._slides
        n = len(self._slides)
        if n:
            t._current_index = max(0, min(int(slide_index or 0), n - 1))
        else:
            t._current_index = 0
        return t

    @staticmethod
    def _history_dicts(history) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in history]

    # ------------------------------------------------------------------ route

    def route(self, req) -> dict:
        user_input = (req.transcript or "").strip()
        if not user_input:
            return {"action": "ignore", "reason": "empty", "slide_index": req.slide_index}

        slide_index = int(req.slide_index or 0)
        tracker = self._tracker_at(slide_index)

        # 1) Slide commands (stateless navigation).
        if tracker.is_active():
            cmd = tracker.detect_command(user_input)
            if cmd == "status":
                slide = tracker.current_slide()
                return {
                    "action": "slide_info", "slide_index": slide_index,
                    "slide_str": tracker.format_context(slide),
                }
            if cmd == "list":
                return {
                    "action": "slide_list", "slide_index": slide_index,
                    "slides": [s.get("title", "?") for s in self._slides],
                }
            if cmd:  # next / prev / goto:N
                tracker.handle_command(cmd)
                new_index = tracker._current_index
                slide = tracker.current_slide()
                # Pure navigation stays silent; navigation + a question falls
                # through to the LLM with the new slide as context.
                if not C.has_question_word(user_input):
                    return {
                        "action": "navigate", "slide_index": new_index,
                        "slide_str": tracker.format_context(slide),
                    }
                slide_index = new_index
                tracker = self._tracker_at(slide_index)

        # 2) Intent routing (hybrid addressee model).
        decision = self.router.route(
            user_input, in_conversation=req.in_conversation, quiet_mode=req.quiet_mode
        )
        action = decision.action
        query = decision.query

        if action is RouteAction.CLOSE:
            return {
                "action": "close", "text": random.choice(C.FAREWELL_RESPONSES),
                "set_quiet": True, "clear_window": True, "slide_index": slide_index,
            }
        if action is RouteAction.IGNORE_AUDIENCE:
            return {"action": "monitor", "intent": "audience", "slide_index": slide_index}
        if action is RouteAction.MONITOR:
            return {
                "action": "monitor",
                "intent": decision.intent_result.intent.value,
                "slide_index": slide_index,
            }
        if action is RouteAction.WAKE_ACK:
            return {
                "action": "wake_ack", "text": random.choice(C.WAKE_ACK_RESPONSES),
                "extend_window": True, "clear_quiet": True, "slide_index": slide_index,
            }
        if action is RouteAction.IGNORE_ACK:
            return {"action": "ignore", "reason": "acknowledgment", "slide_index": slide_index}

        # 3) ANSWER — build the grounded prompt for the browser to run on Groq.
        payload = self._build_answer(query, slide_index, self._history_dicts(req.history))
        payload["extend_window"] = True
        payload["clear_quiet"] = bool(decision.was_direct_call)
        return payload

    def _build_answer(self, user_input: str, slide_index: int, history: list[dict]) -> dict:
        tracker = self._tracker_at(slide_index)
        slide = tracker.current_slide()
        is_expl = C.is_slide_explanation_request(user_input)

        if is_expl:
            enriched = C.slide_explanation_query(slide, user_input)
        else:
            enriched = self.query_rewriter.rewrite(user_input, slide, history)

        chunks = self.retrieval.search(enriched)
        if is_expl:
            chunks = C.filter_slide_explanation_chunks(chunks)
        if chunks and not self.retrieval.has_strong_match(chunks):
            chunks = []
        context_str = self.retrieval.format_context(chunks)
        no_context = not bool(chunks)

        slide_str = tracker.format_context(slide) if slide else ""
        narrative = tracker.format_narrative_context()

        if is_expl:
            messages = self.prompt_builder.build_slide_explanation_messages(
                user_input=user_input, history=history,
                slide_str=slide_str, context_str=context_str, narrative_str=narrative,
            )
        else:
            messages = self.prompt_builder.build_messages(
                user_input=user_input, history=history, slide_str=slide_str,
                context_str=context_str, no_context=no_context, narrative_str=narrative,
            )

        caps = C.response_caps(user_input)
        return {
            "action": "answer",
            "messages": messages,
            "llm": {"model": self.live_model, **caps},
            "context_str": context_str,
            "sources": list({c.get("source_id") for c in chunks}) if chunks else [],
            "slide_index": slide_index,
            "slide_str": slide_str,
        }

    # ------------------------------------------------------------------ verify

    def verify(self, response_text: str, context_str: str) -> dict:
        final, overridden = self.answer_verifier.check(response_text, context_str)
        return {"final_text": final, "overridden": overridden}
