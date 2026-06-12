import json
from unittest.mock import patch
from app.services.trigger_service import TriggerService

SAMPLE_TRIGGERS = [
    {
        "id": "t001",
        "patterns": ["la galigo", "sawerigading"],
        "topic": "Epos La Galigo",
        "mode": "comment",
        "slide_ids": [2],
    },
    {
        "id": "t002",
        "patterns": ["groq", "llm"],
        "topic": "Teknologi LLM",
        "mode": "comment",
        "slide_ids": [3],
    },
    {
        "id": "t003",
        "patterns": ["tanya jawab"],
        "topic": "Sesi Tanya Jawab",
        "mode": "question",
        "slide_ids": [5],
    },
    {
        "id": "t004",
        "patterns": ["retrieval", "bm25"],
        "topic": "Knowledge Base",
        "mode": "memory",
        "slide_ids": [4],
    },
]


def make_service(tmp_path, triggers=None):
    triggers_file = tmp_path / "triggers.json"
    data = SAMPLE_TRIGGERS if triggers is None else triggers
    triggers_file.write_text(json.dumps(data), encoding="utf-8")
    with patch("app.services.trigger_service.TRIGGERS_PATH", triggers_file):
        return TriggerService()


class TestLoad:
    def test_loads_triggers(self, tmp_path):
        svc = make_service(tmp_path)
        assert svc.is_active()
        assert svc.total() == 4

    def test_missing_file_is_inactive(self, tmp_path):
        with patch("app.services.trigger_service.TRIGGERS_PATH", tmp_path / "missing.json"):
            svc = TriggerService()
        assert not svc.is_active()

    def test_empty_list_is_inactive(self, tmp_path):
        svc = make_service(tmp_path, triggers=[])
        assert not svc.is_active()

    def test_all_triggers_returns_copy(self, tmp_path):
        svc = make_service(tmp_path)
        lst = svc.all_triggers()
        lst.clear()
        assert svc.total() == 4


class TestDetect:
    def test_detects_pattern_in_text(self, tmp_path):
        svc = make_service(tmp_path)
        result = svc.detect("ceritakan tentang la galigo kepada kami")
        assert result is not None
        assert result["id"] == "t001"

    def test_case_insensitive(self, tmp_path):
        svc = make_service(tmp_path)
        result = svc.detect("La Galigo adalah epos besar")
        assert result is not None

    def test_no_match_returns_none(self, tmp_path):
        svc = make_service(tmp_path)
        result = svc.detect("hari ini cuaca sangat cerah di luar")
        assert result is None

    def test_returns_first_trigger_on_multiple_matches(self, tmp_path):
        svc = make_service(tmp_path)
        # t001 ("la galigo") comes before t002 ("groq") in SAMPLE_TRIGGERS
        result = svc.detect("la galigo dan groq adalah topik hari ini")
        assert result["id"] == "t001"

    def test_matches_second_pattern_in_trigger(self, tmp_path):
        svc = make_service(tmp_path)
        result = svc.detect("sawerigading adalah tokoh besar dalam epos")
        assert result is not None
        assert result["id"] == "t001"

    def test_inactive_service_returns_none(self, tmp_path):
        svc = make_service(tmp_path, triggers=[])
        assert svc.detect("la galigo groq llm tanya jawab") is None

    def test_partial_match_inside_sentence(self, tmp_path):
        svc = make_service(tmp_path)
        result = svc.detect("sistem bm25 sangat efisien untuk pencarian")
        assert result is not None
        assert result["id"] == "t004"

    def test_second_trigger_fires_when_first_not_present(self, tmp_path):
        svc = make_service(tmp_path)
        result = svc.detect("kami menggunakan groq sebagai backend llm")
        assert result is not None
        assert result["id"] == "t002"

    def test_single_word_pattern_does_not_match_inside_larger_word(self, tmp_path):
        svc = make_service(
            tmp_path,
            triggers=[{"id": "tx", "patterns": ["mengenal"], "topic": "", "mode": "comment"}],
        )

        assert svc.detect("presenter sedang mengenalkan teknologi baru") is None

    def test_single_word_pattern_still_matches_as_whole_word(self, tmp_path):
        svc = make_service(
            tmp_path,
            triggers=[{"id": "tx", "patterns": ["mengenal"], "topic": "", "mode": "comment"}],
        )

        result = svc.detect("sekarang kita mengenal teknologi baru")

        assert result is not None
        assert result["id"] == "tx"

    def test_multiword_pattern_respects_phrase_boundaries(self, tmp_path):
        svc = make_service(
            tmp_path,
            triggers=[{"id": "tx", "patterns": ["la galigo"], "topic": "", "mode": "comment"}],
        )

        assert svc.detect("kisah la galigo dibahas hari ini") is not None
        assert svc.detect("awalan la galigokan tidak valid") is None


class TestBuildPrompt:
    def test_comment_includes_topic(self, tmp_path):
        svc = make_service(tmp_path)
        trigger = SAMPLE_TRIGGERS[0]  # "Epos La Galigo", mode "comment"
        prompt = svc.build_prompt(trigger)
        assert "Epos La Galigo" in prompt

    def test_question_includes_topic(self, tmp_path):
        svc = make_service(tmp_path)
        trigger = SAMPLE_TRIGGERS[2]  # "Sesi Tanya Jawab", mode "question"
        prompt = svc.build_prompt(trigger)
        assert "Sesi Tanya Jawab" in prompt

    def test_memory_includes_topic(self, tmp_path):
        svc = make_service(tmp_path)
        trigger = SAMPLE_TRIGGERS[3]  # "Knowledge Base", mode "memory"
        prompt = svc.build_prompt(trigger)
        assert "Knowledge Base" in prompt

    def test_comment_with_slide_includes_slide_title(self, tmp_path):
        svc = make_service(tmp_path)
        trigger = SAMPLE_TRIGGERS[0]
        slide = {"title": "Latar Belakang", "presenter_notes": ""}
        prompt = svc.build_prompt(trigger, slide)
        assert "Latar Belakang" in prompt

    def test_memory_with_slide_includes_slide_title(self, tmp_path):
        svc = make_service(tmp_path)
        trigger = SAMPLE_TRIGGERS[3]
        slide = {"title": "Knowledge Base & Retrieval", "presenter_notes": ""}
        prompt = svc.build_prompt(trigger, slide)
        assert "Knowledge Base & Retrieval" in prompt

    def test_fallback_when_no_topic(self, tmp_path):
        svc = make_service(tmp_path)
        trigger = {"id": "tx", "patterns": [], "topic": "", "mode": "comment", "slide_ids": []}
        result = svc.build_prompt(trigger, None)
        assert isinstance(result, str) and len(result) > 0

    def test_unknown_mode_returns_string(self, tmp_path):
        svc = make_service(tmp_path)
        trigger = {"id": "tx", "patterns": [], "topic": "Topik", "mode": "xyz", "slide_ids": []}
        result = svc.build_prompt(trigger)
        assert isinstance(result, str) and len(result) > 0

    def test_all_modes_return_non_empty(self, tmp_path):
        svc = make_service(tmp_path)
        slide = {"title": "Slide Test", "presenter_notes": "Catatan penting."}
        for mode in ("comment", "question", "memory"):
            trigger = {"id": "tx", "patterns": [], "topic": "Topik", "mode": mode, "slide_ids": []}
            result = svc.build_prompt(trigger, slide)
            assert result, f"mode '{mode}' returned empty string"

    def test_build_prompt_returns_string_always(self, tmp_path):
        svc = make_service(tmp_path)
        for trigger in SAMPLE_TRIGGERS:
            result = svc.build_prompt(trigger, None)
            assert isinstance(result, str) and result


class TestNewModes:
    def _svc(self, tmp_path):
        return make_service(tmp_path, triggers=[])

    def _t(self, mode, topic="Topik"):
        return {"id": "tx", "patterns": [], "topic": topic, "mode": mode, "slide_ids": []}

    def test_witness_includes_topic(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.build_prompt(self._t("witness", "Dunia Tenri"))
        assert "Dunia Tenri" in result

    def test_gentle_objection_includes_sanggah_phrase(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.build_prompt(self._t("gentle_objection"))
        assert "tidak begitu ji" in result or "sedikit tidak setuju" in result

    def test_gentle_objection_includes_topic(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.build_prompt(self._t("gentle_objection", "Arsip dan Data"))
        assert "Arsip dan Data" in result

    def test_debate_uses_knowledge_base_language(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.build_prompt(self._t("debate", "AI dan diagnosis"))
        assert "knowledge base" in result
        assert "Spesifik" in result

    def test_clarification_includes_topic(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.build_prompt(self._t("clarification", "We Tenriabeng"))
        assert "We Tenriabeng" in result

    def test_short_comment_includes_topic(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.build_prompt(self._t("short_comment", "Alur Suara"))
        assert "Alur Suara" in result

    def test_grounding_check_mentions_no_fabrication(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.build_prompt(self._t("grounding_check"))
        assert "mengarang" in result

    def test_closing_memory_mentions_ingatan(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.build_prompt(self._t("closing_memory"))
        assert "ingatan" in result

    def test_all_new_modes_return_non_empty(self, tmp_path):
        svc = self._svc(tmp_path)
        for mode in ("witness", "gentle_objection", "clarification", "short_comment",
                     "grounding_check", "closing_memory", "debate"):
            result = svc.build_prompt(self._t(mode))
            assert result, f"mode '{mode}' returned empty string"


class TestSuggestedIntent:
    def _svc(self, tmp_path):
        return make_service(tmp_path, triggers=[])

    def test_intent_takes_precedence_over_mode(self, tmp_path):
        svc = self._svc(tmp_path)
        trigger = {
            "id": "tx", "patterns": [], "topic": "Batas Teknologi",
            "mode": "gentle_objection",
            "suggested_response_intent": "Tahan klaim teknologi yang terlalu optimistis.",
            "slide_ids": [],
        }
        result = svc.build_prompt(trigger)
        assert "Tahan klaim teknologi" in result

    def test_intent_includes_topic_as_context(self, tmp_path):
        svc = self._svc(tmp_path)
        trigger = {
            "id": "tx", "patterns": [], "topic": "Batas Teknologi",
            "mode": "gentle_objection",
            "suggested_response_intent": "Instruksi spesifik di sini.",
            "slide_ids": [],
        }
        result = svc.build_prompt(trigger)
        assert "Batas Teknologi" in result

    def test_intent_includes_slide_title(self, tmp_path):
        svc = self._svc(tmp_path)
        trigger = {
            "id": "tx", "patterns": [], "topic": "Topik",
            "mode": "comment",
            "suggested_response_intent": "Instruksi dari trigger.",
            "slide_ids": [],
        }
        slide = {"title": "Slide Aktif", "presenter_notes": ""}
        result = svc.build_prompt(trigger, slide)
        assert "Slide Aktif" in result

    def test_empty_intent_falls_back_to_mode(self, tmp_path):
        svc = self._svc(tmp_path)
        trigger = {
            "id": "tx", "patterns": [], "topic": "La Galigo",
            "mode": "comment",
            "suggested_response_intent": "",
            "slide_ids": [],
        }
        result = svc.build_prompt(trigger)
        assert "La Galigo" in result
