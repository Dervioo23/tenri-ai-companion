from unittest.mock import MagicMock

from app.pipeline.brain_stage import BrainStage


def _brain() -> BrainStage:
    return BrainStage(
        retrieval=MagicMock(),
        query_rewriter=MagicMock(),
        prompt_builder=MagicMock(),
        deprioritized_slide_sources={"tenri-concept", "tursalahjalan-world"},
    )


def test_brain_prepares_grounded_normal_response() -> None:
    brain = _brain()
    chunks = [{"source_id": "paper-ai", "text": "AI belajar dari data."}]
    brain.query_rewriter.rewrite.return_value = "AI belajar data"
    brain.retrieval.search.return_value = chunks
    brain.retrieval.has_strong_match.return_value = True
    brain.retrieval.format_context.return_value = "[paper-ai] AI belajar dari data."
    brain.prompt_builder.build_messages.return_value = [{"role": "user", "content": "x"}]

    result = brain.prepare(
        user_input="Bagaimana AI belajar?",
        history=[],
        slide={"title": "AI"},
        slide_str="[1/2] AI",
        narrative_str="slide 1 dari 2",
        vision_context={"face_count": 1},
    )

    assert result.context_chunks == chunks
    assert result.no_context is False
    assert result.enriched_query == "AI belajar data"
    brain.prompt_builder.build_messages.assert_called_once()


def test_brain_discards_weak_retrieval_before_prompt() -> None:
    brain = _brain()
    brain.query_rewriter.rewrite.return_value = "siapa kamu"
    brain.retrieval.search.return_value = [{"source_id": "unrelated"}]
    brain.retrieval.has_strong_match.return_value = False
    brain.retrieval.format_context.return_value = ""
    brain.prompt_builder.build_messages.return_value = []

    result = brain.prepare(
        user_input="Siapa kamu?",
        history=[],
        slide=None,
        slide_str="",
        narrative_str="",
    )

    assert result.context_chunks == []
    assert result.no_context is True
    _, kwargs = brain.prompt_builder.build_messages.call_args
    assert kwargs["no_context"] is True


def test_brain_slide_explanation_filters_persona_sources() -> None:
    brain = _brain()
    brain.retrieval.search.return_value = [
        {"source_id": "tenri-concept", "text": "Persona Tenri"},
        {"source_id": "pengenalan-ai", "text": "Definisi AI"},
    ]
    brain.retrieval.has_strong_match.return_value = True
    brain.retrieval.format_context.return_value = "Definisi AI"
    brain.prompt_builder.build_slide_explanation_messages.return_value = [
        {"role": "user", "content": "slide"}
    ]

    result = brain.prepare(
        user_input="Jelaskan slide ini",
        history=[],
        slide={"title": "Definisi AI", "topics": ["AI"]},
        slide_str="[1/2] Definisi AI",
        narrative_str="slide 1 dari 2",
    )

    assert result.is_slide_explanation is True
    assert [chunk["source_id"] for chunk in result.context_chunks] == ["pengenalan-ai"]
    brain.prompt_builder.build_slide_explanation_messages.assert_called_once()
    brain.prompt_builder.build_messages.assert_not_called()


def test_brain_builds_interruption_context_from_topic_and_slide() -> None:
    brain = _brain()
    chunks = [{"source_id": "paper-1", "text": "Evidence"}]
    brain.retrieval.search.return_value = chunks
    brain.retrieval.has_strong_match.return_value = True
    brain.retrieval.format_context.return_value = "[paper-1] Evidence"

    context, no_context = brain.interruption_context(
        "klaim dokter",
        {"title": "AI Diagnosis", "topics": ["kesehatan"]},
    )

    assert context == "[paper-1] Evidence"
    assert no_context is False
    brain.retrieval.search.assert_called_once_with(
        "klaim dokter AI Diagnosis kesehatan"
    )
