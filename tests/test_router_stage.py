from unittest.mock import MagicMock

from app.pipeline.router_stage import RouteAction, RouterStage
from app.services.intent_classifier import Intent, IntentResult


def _router(result: IntentResult) -> RouterStage:
    classifier = MagicMock()
    classifier.classify.return_value = result
    return RouterStage(
        classifier,
        wake_words=["tenri"],
        audience_markers={"teman-teman"},
        closing_phrases={"terima kasih"},
        acknowledgment_phrases={"oke", "iya"},
        question_detector=lambda text: "?" in text or "memangnya" in text.lower(),
    )


def test_router_answers_followup_question_inside_conversation() -> None:
    router = _router(IntentResult(
        intent=Intent.ASKING_TENRI,
        query="Memangnya seperti apa?",
        reason="conversation question",
    ))

    decision = router.route(
        "Memangnya seperti apa?",
        in_conversation=True,
        quiet_mode=False,
    )

    assert decision.action is RouteAction.ANSWER
    assert decision.has_question is True


def test_router_suppresses_short_acknowledgment() -> None:
    router = _router(IntentResult(
        intent=Intent.ASKING_TENRI,
        query="Oke.",
        reason="conversation continuation",
    ))
    decision = router.route("Oke.", in_conversation=True, quiet_mode=False)
    assert decision.action is RouteAction.IGNORE_ACK
    assert decision.normalized_ack == "oke"


def test_router_routes_bare_wake_word_to_acknowledgment() -> None:
    router = _router(IntentResult(
        intent=Intent.ASKING_TENRI,
        query="",
        reason="wake word only",
        was_wake_word=True,
    ))
    decision = router.route("Tenri", in_conversation=False, quiet_mode=False)
    assert decision.action is RouteAction.WAKE_ACK
    assert decision.was_direct_call is True


def test_router_keeps_presenter_narration_in_monitor_mode() -> None:
    router = _router(IntentResult(
        intent=Intent.EXPLAINING,
        query="AI bekerja dari data",
        reason="presenter narration",
    ))
    decision = router.route(
        "AI bekerja dari data",
        in_conversation=False,
        quiet_mode=False,
    )
    assert decision.action is RouteAction.MONITOR
