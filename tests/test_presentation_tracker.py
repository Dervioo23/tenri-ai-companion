import json
import pytest
from unittest.mock import patch
from app.services.presentation_tracker import PresentationTracker

SAMPLE_SLIDES = [
    {
        "id": 1,
        "title": "Pembukaan",
        "topics": ["tenri", "ai"],
        "presenter_notes": "Perkenalkan Tenri.",
        "triggers": ["mulai", "pembukaan"],
    },
    {
        "id": 2,
        "title": "La Galigo",
        "topics": ["la galigo", "bugis"],
        "presenter_notes": "Jelaskan epos.",
        "triggers": ["la galigo", "bugis"],
    },
    {
        "id": 3,
        "title": "Penutup",
        "topics": ["demo", "penutup"],
        "presenter_notes": "Demo live.",
        "triggers": ["selesai", "penutup"],
    },
]


def make_tracker(tmp_path, slides=None):
    slides_file = tmp_path / "slides.json"
    slides_file.write_text(json.dumps(slides or SAMPLE_SLIDES), encoding="utf-8")
    with patch("app.services.presentation_tracker.SLIDES_PATH", slides_file):
        return PresentationTracker()


class TestLoad:
    def test_loads_slides(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.is_active()
        assert tracker.total() == 3

    def test_missing_file_is_inactive(self, tmp_path):
        with patch("app.services.presentation_tracker.SLIDES_PATH", tmp_path / "missing.json"):
            tracker = PresentationTracker()
        assert not tracker.is_active()

    def test_starts_at_first_slide(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.current_slide()["id"] == 1

    def test_position_at_start(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.position() == (1, 3)


class TestNavigation:
    def test_next_advances(self, tmp_path):
        tracker = make_tracker(tmp_path)
        slide = tracker.next_slide()
        assert slide["id"] == 2

    def test_prev_goes_back(self, tmp_path):
        tracker = make_tracker(tmp_path)
        tracker.next_slide()
        slide = tracker.prev_slide()
        assert slide["id"] == 1

    def test_next_clamps_at_last(self, tmp_path):
        tracker = make_tracker(tmp_path)
        tracker.go_to(3)
        slide = tracker.next_slide()
        assert slide["id"] == 3

    def test_prev_clamps_at_first(self, tmp_path):
        tracker = make_tracker(tmp_path)
        slide = tracker.prev_slide()
        assert slide["id"] == 1

    def test_go_to(self, tmp_path):
        tracker = make_tracker(tmp_path)
        slide = tracker.go_to(3)
        assert slide["id"] == 3

    def test_go_to_out_of_range_clamps_to_last(self, tmp_path):
        tracker = make_tracker(tmp_path)
        slide = tracker.go_to(99)
        assert slide["id"] == 3

    def test_next_updates_position(self, tmp_path):
        tracker = make_tracker(tmp_path)
        tracker.next_slide()
        assert tracker.position() == (2, 3)

    def test_inactive_tracker_returns_none(self, tmp_path):
        with patch("app.services.presentation_tracker.SLIDES_PATH", tmp_path / "missing.json"):
            tracker = PresentationTracker()
        assert tracker.next_slide() is None
        assert tracker.prev_slide() is None
        assert tracker.go_to(1) is None


class TestCommands:
    def test_detect_lanjut(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("lanjut") == "next"

    def test_detect_next_english(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("next") == "next"

    def test_detect_mundur(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("mundur") == "prev"

    def test_detect_goto(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("slide 2") == "goto:2"

    @pytest.mark.parametrize(
        ("utterance", "expected"),
        [
            ("lanjut ke slide ketiga", "goto:3"),
            ("lanjut ke slide kelima", "goto:5"),
            ("lanjut ke slide ketujuh", "goto:7"),
            ("slide kedua", "goto:2"),
            ("slide ke-5", "goto:5"),
            ("slide ke 7", "goto:7"),
            ("pergi ke slide dua belas", "goto:12"),
        ],
    )
    def test_detect_goto_ordinal_takes_priority_over_lanjut(self, tmp_path, utterance, expected):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command(utterance) == expected

    def test_detect_slide_berikutnya_still_next(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("lanjut ke slide berikutnya") == "next"

    def test_detect_no_command(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("ceritakan tentang La Galigo") is None

    def test_handle_next(self, tmp_path):
        tracker = make_tracker(tmp_path)
        tracker.handle_command("next")
        assert tracker.current_slide()["id"] == 2

    def test_handle_prev(self, tmp_path):
        tracker = make_tracker(tmp_path)
        tracker.next_slide()
        tracker.handle_command("prev")
        assert tracker.current_slide()["id"] == 1

    def test_handle_goto(self, tmp_path):
        tracker = make_tracker(tmp_path)
        tracker.handle_command("goto:3")
        assert tracker.current_slide()["id"] == 3


class TestInfoCommands:
    def test_detect_status(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("status") == "status"

    def test_detect_posisi(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("posisi") == "status"

    def test_detect_info_slide(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("info slide") == "status"

    def test_detect_list(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("list") == "list"

    def test_detect_slide_list(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("slide list") == "list"

    def test_detect_daftar_slide(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.detect_command("daftar slide") == "list"

    def test_all_slides_returns_all(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert len(tracker.all_slides()) == 3

    def test_all_slides_is_copy(self, tmp_path):
        tracker = make_tracker(tmp_path)
        slides = tracker.all_slides()
        slides.clear()
        assert tracker.total() == 3

    def test_status_does_not_change_position(self, tmp_path):
        tracker = make_tracker(tmp_path)
        tracker.next_slide()
        tracker.detect_command("status")
        assert tracker.current_slide()["id"] == 2


class TestAutoTrigger:
    def test_trigger_changes_slide(self, tmp_path):
        tracker = make_tracker(tmp_path)
        slide = tracker.detect_trigger("ceritakan tentang la galigo")
        assert slide is not None
        assert slide["id"] == 2

    def test_trigger_no_match_returns_none(self, tmp_path):
        tracker = make_tracker(tmp_path)
        result = tracker.detect_trigger("apa itu machine learning")
        assert result is None

    def test_trigger_skips_current_slide(self, tmp_path):
        tracker = make_tracker(tmp_path)
        # Slide 1 has trigger "mulai" — should NOT fire since we're already on slide 1
        result = tracker.detect_trigger("mulai pembukaan")
        assert result is None

    def test_trigger_updates_current_index(self, tmp_path):
        tracker = make_tracker(tmp_path)
        tracker.detect_trigger("selesai demo penutup")
        assert tracker.current_slide()["id"] == 3


class TestContextFormat:
    def test_format_includes_title(self, tmp_path):
        tracker = make_tracker(tmp_path)
        ctx = tracker.format_context(tracker.current_slide())
        assert "Pembukaan" in ctx

    def test_format_includes_position(self, tmp_path):
        tracker = make_tracker(tmp_path)
        ctx = tracker.format_context(tracker.current_slide())
        assert "[1/3]" in ctx

    def test_format_includes_topics(self, tmp_path):
        tracker = make_tracker(tmp_path)
        ctx = tracker.format_context(tracker.current_slide())
        assert "tenri" in ctx or "ai" in ctx

    def test_format_includes_notes(self, tmp_path):
        tracker = make_tracker(tmp_path)
        ctx = tracker.format_context(tracker.current_slide())
        assert "Perkenalkan" in ctx

    def test_format_none_returns_empty(self, tmp_path):
        tracker = make_tracker(tmp_path)
        assert tracker.format_context(None) == ""

    def test_format_narrative_context_includes_position_and_slide_arc(self, tmp_path):
        tracker = make_tracker(tmp_path)
        tracker.go_to(2)

        narrative = tracker.format_narrative_context()

        assert "slide 2 dari 3" in narrative
        assert "Sudah dibahas: Pembukaan" in narrative
        assert "Slide aktif sekarang: La Galigo" in narrative
        assert "Slide berikutnya: Penutup" in narrative

    def test_format_narrative_context_inactive_returns_empty(self, tmp_path):
        with patch("app.services.presentation_tracker.SLIDES_PATH", tmp_path / "missing.json"):
            tracker = PresentationTracker()
        assert tracker.format_narrative_context() == ""

    def test_enriched_query_adds_topics(self, tmp_path):
        tracker = make_tracker(tmp_path)
        result = tracker.get_enriched_query("siapa ini")
        assert "tenri" in result or "ai" in result

    def test_enriched_query_no_slides(self, tmp_path):
        with patch("app.services.presentation_tracker.SLIDES_PATH", tmp_path / "missing.json"):
            tracker = PresentationTracker()
        assert tracker.get_enriched_query("apa ini") == "apa ini"
