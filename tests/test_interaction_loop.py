from unittest.mock import MagicMock, patch

from app.core.interaction_loop import InteractionLoop, _STATIC_TTS_PHRASES, _WAKE_ACK_RESPONSES
from app.state import AppState
from app.services.background_listener import BackgroundListener


def test_failed_preferred_listener_falls_back_to_background_listener() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.speech_service = MagicMock()
    preferred = MagicMock()
    preferred.start.return_value = False
    loop.bg_listener = preferred

    with patch.object(BackgroundListener, "start", return_value=True) as fallback_start:
        assert loop._start_background_listener() is True

    preferred.stop.assert_called_once_with()
    assert isinstance(loop.bg_listener, BackgroundListener)
    fallback_start.assert_called_once_with()


def test_auto_slide_trigger_prints_slide_change() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    slide = {"id": 2, "title": "Dunia Tenri"}
    loop.tracker = MagicMock()
    loop.tracker.is_active.return_value = True
    loop.tracker.detect_trigger.return_value = slide
    loop.tracker.position.return_value = (2, 8)
    loop.jarvis_ui = None

    with patch("app.core.interaction_loop.TerminalUI.print_slide_change") as print_change:
        result = loop._handle_auto_slide_trigger("museum la galigo")

    assert result == slide
    loop.tracker.detect_trigger.assert_called_once_with("museum la galigo")
    print_change.assert_called_once_with(slide, 2, 8)


def test_auto_slide_trigger_without_match_does_not_print() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.tracker = MagicMock()
    loop.tracker.is_active.return_value = True
    loop.tracker.detect_trigger.return_value = None

    with patch("app.core.interaction_loop.TerminalUI.print_slide_change") as print_change:
        result = loop._handle_auto_slide_trigger("tidak ada keyword")

    assert result is None
    print_change.assert_not_called()


def test_auto_slide_trigger_inactive_tracker_does_not_detect() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.tracker = MagicMock()
    loop.tracker.is_active.return_value = False

    with patch("app.core.interaction_loop.TerminalUI.print_slide_change") as print_change:
        result = loop._handle_auto_slide_trigger("museum la galigo")

    assert result is None
    loop.tracker.detect_trigger.assert_not_called()
    print_change.assert_not_called()


def test_input_requests_spoken_response_recognizes_commentary_request() -> None:
    assert InteractionLoop._input_requests_spoken_response("lanjut Tenri, komentari slide ini")
    assert InteractionLoop._input_requests_spoken_response("next, jelaskan bagian ini")
    assert not InteractionLoop._input_requests_spoken_response("lanjut Tenri")


def test_input_requests_spoken_response_ignores_question_word_inside_other_word() -> None:
    """'apa' inside 'lapangan'/'harapan' must NOT count as a question (BUG-03)."""
    assert not InteractionLoop._input_requests_spoken_response("lanjut ke lapangan utama")
    assert not InteractionLoop._input_requests_spoken_response("next, harapan kita besar")
    assert not InteractionLoop._input_requests_spoken_response("mundur, siapapun boleh maju")


def test_input_requests_spoken_response_detects_standalone_question_words() -> None:
    """Real standalone question words and '?' must still be detected."""
    assert InteractionLoop._input_requests_spoken_response("lanjut, apa maksudnya")
    assert InteractionLoop._input_requests_spoken_response("next berapa jumlahnya")
    assert InteractionLoop._input_requests_spoken_response("mundur, betul begitu?")


def test_is_exit_command_recognizes_quit_words_any_mode() -> None:
    """Exit words must end the loop in any mode, tolerant of case/whitespace (BUG-10)."""
    for word in ["exit", "quit", "keluar", "KELUAR", "  Exit  ", "Quit"]:
        assert InteractionLoop._is_exit_command(word), word


def test_is_exit_command_ignores_non_exit_input() -> None:
    assert not InteractionLoop._is_exit_command("jelaskan slide ini")
    assert not InteractionLoop._is_exit_command("keluarkan datanya")  # bukan kata utuh "keluar"
    assert not InteractionLoop._is_exit_command("")


def test_slide_explanation_request_detects_direct_slide_explain_commands() -> None:
    assert InteractionLoop._is_slide_explanation_request("jelaskan slide ini")
    assert InteractionLoop._is_slide_explanation_request("silahkan jelaskan slide pertama ini")
    assert InteractionLoop._is_slide_explanation_request("slide ini coba kamu terangkan")
    assert not InteractionLoop._is_slide_explanation_request("komentari gagasan ini")


def test_slide_explanation_query_uses_slide_substance() -> None:
    slide = {
        "title": "DEFINISI DASAR",
        "subtitle": "Apa Itu Kecerdasan Buatan?",
        "topics": ["AI", "kognitif"],
        "presenter_notes": "AI meniru fungsi kognitif manusia.",
        "tenri_role": "Koreksi mitos AI.",
    }

    query = InteractionLoop._slide_explanation_query(slide, "jelaskan slide ini")

    assert "Apa Itu Kecerdasan Buatan?" in query
    assert "AI meniru fungsi kognitif manusia" in query
    assert "Koreksi mitos AI" in query
    assert query != "jelaskan slide ini"


def test_slide_explanation_filter_prefers_non_persona_sources() -> None:
    chunks = [
        {"source_id": "tenri-concept", "text": "Tenri adalah companion presentasi."},
        {"source_id": "pengenalan-ai", "text": "AI meniru fungsi kognitif manusia."},
        {"source_id": "tursalahjalan-world", "text": "Museum La Galigo."},
    ]

    result = InteractionLoop._filter_slide_explanation_chunks(chunks)

    assert result == [{"source_id": "pengenalan-ai", "text": "AI meniru fungsi kognitif manusia."}]


def test_slide_explanation_filter_keeps_persona_sources_as_fallback() -> None:
    chunks = [
        {"source_id": "tenri-concept", "text": "Tenri adalah companion presentasi."},
    ]

    assert InteractionLoop._filter_slide_explanation_chunks(chunks) == chunks


def test_live_char_budget_can_be_bypassed_by_detail_request() -> None:
    with patch("app.core.interaction_loop.Config.LIVE_RESPONSE_MAX_CHARS", 260):
        assert InteractionLoop._live_char_budget("jelaskan slide ini") == 260
        assert InteractionLoop._live_char_budget("jelaskan slide ini lebih detail") == 0


def test_handle_slide_command_quiet_navigation_does_not_interrupt() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.tracker = MagicMock()
    loop.tracker.is_active.return_value = True
    loop.tracker.detect_command.return_value = "next"
    slide = {"id": 2, "title": "Definisi Dasar"}
    loop.tracker.handle_command.return_value = slide
    loop.tracker.position.return_value = (2, 12)
    loop.jarvis_ui = None
    loop._do_interruption = MagicMock()

    with (
        patch("app.core.interaction_loop.state_manager.set_state") as set_state,
        patch("app.core.interaction_loop.TerminalUI.print_slide_change") as print_change,
    ):
        handled = loop._handle_slide_command("Lanjut Tenri")

    assert handled is True
    loop.tracker.handle_command.assert_called_once_with("next")
    print_change.assert_called_once_with(slide, 2, 12)
    loop._do_interruption.assert_not_called()
    set_state.assert_called_once_with(AppState.IDLE)


def test_handle_slide_command_with_response_request_falls_through() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.tracker = MagicMock()
    loop.tracker.is_active.return_value = True
    loop.tracker.detect_command.return_value = "next"
    slide = {"id": 2, "title": "Definisi Dasar"}
    loop.tracker.handle_command.return_value = slide
    loop.tracker.position.return_value = (2, 12)
    loop.jarvis_ui = None

    with (
        patch("app.core.interaction_loop.state_manager.set_state") as set_state,
        patch("app.core.interaction_loop.TerminalUI.print_slide_change"),
    ):
        handled = loop._handle_slide_command("Lanjut Tenri, komentari slide ini")

    assert handled is False
    set_state.assert_not_called()


def test_strip_echo_removes_short_tenri_prefix() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop._last_tenri_response = "Iye, ada apa?"

    result = loop._strip_echo("Iya, ada apa? Jelaskan slide pertama ini")

    assert result == "jelaskan slide pertama ini"


def test_strip_echo_discards_short_tenri_echo_only() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop._last_tenri_response = "Ya, saya di sini."

    result = loop._strip_echo("Iya saya di sini")

    assert result == ""


def test_strip_echo_keeps_question_quoting_tenri_with_wake() -> None:
    # Regression: a real follow-up that quotes Tenri's terms AND names her was
    # being discarded whole as echo (overlap 67%), eating the question.
    loop = InteractionLoop.__new__(InteractionLoop)
    loop._last_tenri_response = (
        "Tiga pendekatan utama adalah Supervised Learning, "
        "Unsupervised Learning, dan Reinforcement Learning."
    )
    result = loop._strip_echo("Apa itu Supervised Learning Tenri?")
    assert result == "Apa itu Supervised Learning Tenri?"


def test_strip_echo_keeps_overlapping_question_without_wake() -> None:
    # A question signal alone is enough — Tenri's answers are declarative.
    loop = InteractionLoop.__new__(InteractionLoop)
    loop._last_tenri_response = "Supervised Learning adalah pembelajaran dengan data berlabel."
    result = loop._strip_echo("Apa itu supervised learning?")
    assert result == "Apa itu supervised learning?"


def test_strip_echo_still_discards_declarative_echo() -> None:
    # No wake word, no question signal -> genuine mic bleed is still discarded.
    loop = InteractionLoop.__new__(InteractionLoop)
    loop._last_tenri_response = "Supervised Learning adalah pembelajaran dengan data berlabel."
    result = loop._strip_echo("Supervised learning adalah pembelajaran dengan data berlabel")
    assert result == ""


def test_do_interruption_marks_prompt_as_no_context() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.policy = MagicMock()
    loop.tracker = MagicMock()
    loop.tracker.format_context.return_value = "[1/8] Slide Test"
    loop.tracker.format_narrative_context.return_value = "Presentasi berjalan: slide 1 dari 8."
    loop.prompt_builder = MagicMock()
    loop.prompt_builder.build_messages.return_value = [{"role": "user", "content": "prompt"}]
    loop.memory = MagicMock()
    loop.memory.get_messages.return_value = []
    loop.groq_service = MagicMock()
    loop.groq_service.get_response.return_value = "Respons Tenri."
    loop.groq_service.get_response_streaming.return_value = "Respons Tenri."
    loop.session_logger = MagicMock()
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.audio_player = MagicMock()
    loop.jarvis_ui = None

    slide = {"title": "Slide Test"}

    with (
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.TerminalUI.get_spinner") as spinner,
        patch("app.core.interaction_loop.TerminalUI.print_interruption"),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
        patch("app.core.interaction_loop.time.sleep"),
    ):
        spinner.return_value.__enter__.return_value = None
        spinner.return_value.__exit__.return_value = False
        loop._do_interruption("comment", slide, prompt="Prompt interupsi")

    loop.prompt_builder.build_messages.assert_called_once_with(
        user_input="Prompt interupsi",
        history=[],
        slide_str="[1/8] Slide Test",
        context_str="",
        narrative_str="Presentasi berjalan: slide 1 dari 8.",
        no_context=True,
    )
    loop.policy.record_interruption.assert_called_once()
    loop.session_logger.log_exchange.assert_called_once_with(
        user_input="[auto:comment] Prompt interupsi",
        response="Respons Tenri.",
        slide_title="Slide Test",
        mode="comment",
    )


def test_do_interruption_returns_to_idle_when_thinking_state_raises() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.policy = MagicMock()
    loop.tracker = MagicMock()
    loop.tracker.format_context.return_value = ""
    loop.tracker.format_narrative_context.return_value = ""

    calls = []

    def fake_set_state(state):
        calls.append(state)
        if state == AppState.THINKING:
            raise RuntimeError("listener failed")

    with patch("app.core.interaction_loop.state_manager.set_state", side_effect=fake_set_state):
        loop._do_interruption("comment", None, prompt="Prompt interupsi")

    assert calls == [AppState.THINKING, AppState.IDLE]


def test_build_interruption_context_uses_topic_and_slide_metadata() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.retrieval = MagicMock()
    chunks = [{"source_id": "paper-1", "text": "AI membantu diagnosis spesifik."}]
    loop.retrieval.search.return_value = chunks
    loop.retrieval.format_context.return_value = "[paper-1] AI membantu diagnosis spesifik."

    slide = {"title": "AI dan Diagnosis", "topics": ["kesehatan", "machine learning"]}

    context_str, no_context = loop._build_interruption_context("klaim dokter", slide)

    assert context_str == "[paper-1] AI membantu diagnosis spesifik."
    assert no_context is False
    loop.retrieval.search.assert_called_once_with(
        "klaim dokter AI dan Diagnosis kesehatan machine learning"
    )


def test_build_interruption_context_returns_no_context_without_query() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.retrieval = MagicMock()

    context_str, no_context = loop._build_interruption_context("", None)

    assert context_str == ""
    assert no_context is True
    loop.retrieval.search.assert_not_called()


def test_do_interruption_passes_context_to_prompt_builder() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.policy = MagicMock()
    loop.tracker = MagicMock()
    loop.tracker.format_context.return_value = "[2/8] Slide Data"
    loop.tracker.format_narrative_context.return_value = "Presentasi berjalan: slide 2 dari 8."
    loop.prompt_builder = MagicMock()
    loop.prompt_builder.build_messages.return_value = [{"role": "user", "content": "prompt"}]
    loop.memory = MagicMock()
    loop.memory.get_messages.return_value = []
    loop.groq_service = MagicMock()
    loop.groq_service.get_response.return_value = "Data yang saya punya berbicara sebaliknya."
    loop.session_logger = MagicMock()
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.audio_player = MagicMock()

    slide = {"title": "Slide Data"}

    with (
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.TerminalUI.get_spinner") as spinner,
        patch("app.core.interaction_loop.TerminalUI.print_interruption"),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
        patch("app.core.interaction_loop.time.sleep"),
    ):
        spinner.return_value.__enter__.return_value = None
        spinner.return_value.__exit__.return_value = False
        loop._do_interruption(
            "debate",
            slide,
            prompt="Gunakan data untuk menyanggah.",
            context_str="[paper-1] AI membantu diagnosis spesifik.",
        )

    loop.prompt_builder.build_messages.assert_called_once_with(
        user_input="Gunakan data untuk menyanggah.",
        history=[],
        slide_str="[2/8] Slide Data",
        context_str="[paper-1] AI membantu diagnosis spesifik.",
        narrative_str="Presentasi berjalan: slide 2 dari 8.",
        no_context=False,
    )


# ------------------------------------------------------------------ prewarm TTS cache

def test_prewarm_tts_cache_generates_all_static_phrases() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True
    loop.elevenlabs_service.text_to_speech.return_value = "/cache/audio.mp3"

    with (
        patch("app.core.interaction_loop.Config.TTS_PREWARM_ENABLED", True),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True),
    ):
        with patch("app.core.interaction_loop._STATIC_TTS_PHRASES", ("Halo.", "Oke.")):
            loop._prewarm_tts_cache()
            loop._prewarm_thread.join(timeout=2.0)

    assert loop.elevenlabs_service.text_to_speech.call_count == 2
    calls = [c.args[0] for c in loop.elevenlabs_service.text_to_speech.call_args_list]
    assert "Halo." in calls
    assert "Oke." in calls


def test_prewarm_tts_cache_skips_when_voice_output_disabled() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True

    with (
        patch("app.core.interaction_loop.Config.TTS_PREWARM_ENABLED", True),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
    ):
        loop._prewarm_tts_cache()

    loop.elevenlabs_service.text_to_speech.assert_not_called()
    assert not hasattr(loop, "_prewarm_thread")


def test_prewarm_tts_cache_skips_when_client_is_none() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None

    with (
        patch("app.core.interaction_loop.Config.TTS_PREWARM_ENABLED", True),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True),
    ):
        loop._prewarm_tts_cache()

    loop.elevenlabs_service.text_to_speech.assert_not_called()
    assert not hasattr(loop, "_prewarm_thread")


def test_prewarm_tts_cache_continues_after_single_phrase_failure() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True

    call_count = 0

    def flaky_tts(text):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("API timeout")
        return "/cache/audio.mp3"

    loop.elevenlabs_service.text_to_speech.side_effect = flaky_tts

    with (
        patch("app.core.interaction_loop.Config.TTS_PREWARM_ENABLED", True),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True),
    ):
        with patch("app.core.interaction_loop._STATIC_TTS_PHRASES", ("A.", "B.", "C.")):
            loop._prewarm_tts_cache()
            loop._prewarm_thread.join(timeout=2.0)

    # All 3 were attempted despite the first one failing
    assert loop.elevenlabs_service.text_to_speech.call_count == 3


def test_static_tts_phrases_includes_greeting_and_farewells() -> None:
    assert "Ya, saya di sini." in _STATIC_TTS_PHRASES
    assert "Iye, saya di sini." in _STATIC_TTS_PHRASES
    assert "Saya dengar." in _STATIC_TTS_PHRASES
    assert "Sama-sama." in _STATIC_TTS_PHRASES
    assert "Senang bisa membantu." in _STATIC_TTS_PHRASES
    assert len(_STATIC_TTS_PHRASES) >= 7


def test_prewarm_tts_cache_skips_when_prewarm_disabled() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True

    with (
        patch("app.core.interaction_loop.Config.TTS_PREWARM_ENABLED", False),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True),
    ):
        loop._prewarm_tts_cache()

    loop.elevenlabs_service.text_to_speech.assert_not_called()
    assert not hasattr(loop, "_prewarm_thread")


def test_wake_ack_responses_are_short_and_slide_free() -> None:
    assert _WAKE_ACK_RESPONSES
    for response in _WAKE_ACK_RESPONSES:
        assert len(response) <= 40
        assert "slide" not in response.lower()


def test_sanitize_wake_ack_keeps_short_natural_response() -> None:
    assert InteractionLoop._sanitize_wake_ack_response("Saya dengar.") == "Saya dengar."


def test_sanitize_wake_ack_rejects_slide_like_response() -> None:
    result = InteractionLoop._sanitize_wake_ack_response(
        "Baik, mari kita mulai dengan pengenalan teknologi kecerdasan buatan."
    )

    assert result == "Iye, saya di sini."


def test_sanitize_wake_ack_rejects_long_response() -> None:
    result = InteractionLoop._sanitize_wake_ack_response(
        "Iye, saya di sini dan siap membantu presenter menjelaskan materi slide ini dengan lengkap."
    )

    assert result == "Iye, saya di sini."


# ------------------------------------------------------------------ LIVE_RESPONSE_MODE

def test_do_interruption_trims_to_1_sentence_in_live_mode() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.policy = MagicMock()
    loop.tracker = MagicMock()
    loop.tracker.format_context.return_value = ""
    loop.tracker.format_narrative_context.return_value = ""
    loop.prompt_builder = MagicMock()
    messages = [{"role": "user", "content": "prompt"}]
    loop.prompt_builder.build_messages.return_value = messages
    loop.memory = MagicMock()
    loop.memory.get_messages.return_value = []
    loop.groq_service = MagicMock()
    loop.groq_service.get_response.return_value = "Kalimat pertama. Kalimat kedua."
    loop.session_logger = MagicMock()
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.audio_player = MagicMock()

    with (
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.TerminalUI.get_spinner") as spinner,
        patch("app.core.interaction_loop.TerminalUI.print_interruption"),
        patch("app.core.interaction_loop.Config.GROQ_STREAMING", False),
        patch("app.core.interaction_loop.Config.LIVE_RESPONSE_MODE", True),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
        patch("app.core.interaction_loop.time.sleep"),
        patch("app.core.interaction_loop.trim_response", return_value="Kalimat pertama.") as mock_trim,
    ):
        spinner.return_value.__enter__.return_value = None
        spinner.return_value.__exit__.return_value = False
        loop._do_interruption("comment", None, prompt="Test prompt")

    mock_trim.assert_called_once_with("Kalimat pertama. Kalimat kedua.", max_sentences=1)


def test_do_interruption_trims_to_2_sentences_normally() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.policy = MagicMock()
    loop.tracker = MagicMock()
    loop.tracker.format_context.return_value = ""
    loop.tracker.format_narrative_context.return_value = ""
    loop.prompt_builder = MagicMock()
    messages = [{"role": "user", "content": "prompt"}]
    loop.prompt_builder.build_messages.return_value = messages
    loop.memory = MagicMock()
    loop.memory.get_messages.return_value = []
    loop.groq_service = MagicMock()
    loop.groq_service.get_response.return_value = "Kalimat pertama. Kalimat kedua."
    loop.session_logger = MagicMock()
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.audio_player = MagicMock()

    with (
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.TerminalUI.get_spinner") as spinner,
        patch("app.core.interaction_loop.TerminalUI.print_interruption"),
        patch("app.core.interaction_loop.Config.GROQ_STREAMING", False),
        patch("app.core.interaction_loop.Config.LIVE_RESPONSE_MODE", False),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
        patch("app.core.interaction_loop.time.sleep"),
        patch("app.core.interaction_loop.trim_response", return_value="Kalimat pertama.") as mock_trim,
    ):
        spinner.return_value.__enter__.return_value = None
        spinner.return_value.__exit__.return_value = False
        loop._do_interruption("comment", None, prompt="Test prompt")

    mock_trim.assert_called_once_with("Kalimat pertama. Kalimat kedua.", max_sentences=2)


def test_stream_and_speak_respects_character_budget() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    llm = MagicMock()
    llm.client = True
    llm.stream_response_chunks.return_value = iter([
        (
            "Digitalisasi membantu arsip bertahan lebih lama tetapi tidak otomatis "
            "menjaga konteks sosial yang membuatnya bermakna bagi komunitas. "
            "Audiens perlu melihat teknologi sebagai alat rawat, bukan pengganti ingatan."
        )
    ])
    loop._llm = MagicMock(return_value=llm)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = False
    loop.bg_listener = MagicMock()

    with (
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.time.sleep"),
    ):
        result = loop._stream_and_speak(
            [{"role": "user", "content": "prompt"}],
            max_sentences=3,
            max_chars=90,
        )

    assert len(result) <= 90
    assert result.endswith(".")


def test_stream_and_speak_detail_token_override() -> None:
    """A detail request lifts the live 80-token muzzle to the requested budget."""
    loop = InteractionLoop.__new__(InteractionLoop)
    llm = MagicMock()
    llm.client = True
    llm.stream_response_chunks.return_value = iter(["Penjelasan panjang."])
    loop._llm = MagicMock(return_value=llm)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = False
    loop.bg_listener = MagicMock()

    with (
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
        patch("app.core.interaction_loop.Config.LIVE_RESPONSE_MODE", True),
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.time.sleep"),
    ):
        loop._stream_and_speak(
            [{"role": "user", "content": "prompt"}],
            max_sentences=4,
            max_tokens=240,
        )

    # Live mode would normally cap at 80; the explicit override must win.
    _, kwargs = llm.stream_response_chunks.call_args
    assert kwargs["max_tokens"] == 240


def test_stream_and_speak_uses_streaming_tts_when_available() -> None:
    """With streaming TTS available, sentences stream+play instead of file playback (TAHAP 2)."""
    loop = InteractionLoop.__new__(InteractionLoop)
    llm = MagicMock()
    llm.client = True
    llm.stream_response_chunks.return_value = iter(["Halo, saya Tenri."])
    loop._llm = MagicMock(return_value=llm)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = False
    loop.bg_listener = MagicMock()
    loop.audio_player = MagicMock()
    loop.streaming_tts = MagicMock()
    loop.streaming_tts.available = True
    loop.streaming_tts.speak.return_value = True

    with (
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True),
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.time.sleep"),
    ):
        result = loop._stream_and_speak([{"role": "user", "content": "prompt"}], max_sentences=1)

    assert result == "Halo, saya Tenri."
    loop.streaming_tts.speak.assert_called_once()
    assert loop.streaming_tts.speak.call_args.args[0] == "Halo, saya Tenri."
    loop.audio_player.play_audio.assert_not_called()  # streamed, no file playback


def test_stream_and_speak_closes_stream_after_early_sentence_limit() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    llm = MagicMock()
    llm.client = True
    stream = MagicMock()
    stream.__iter__.return_value = iter([
        "Kalimat pertama selesai. Kalimat kedua tidak perlu diproses."
    ])
    llm.stream_response_chunks.return_value = stream
    loop._llm = MagicMock(return_value=llm)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = False
    loop.bg_listener = MagicMock()

    with (
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.time.sleep"),
    ):
        result = loop._stream_and_speak(
            [{"role": "user", "content": "prompt"}],
            max_sentences=1,
        )

    assert result == "Kalimat pertama selesai."
    stream.close.assert_called_once_with()


def test_streaming_grounding_blocks_sentence_before_tts() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    llm = MagicMock()
    llm.client = True
    llm.stream_response_chunks.return_value = iter([
        "Klaim ini tidak didukung sumber. Kalimat lain juga muncul."
    ])
    loop._llm = MagicMock(return_value=llm)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = False
    loop.answer_verifier = MagicMock()
    loop.answer_verifier.check.return_value = (
        "Tenri tidak punya informasi spesifik untuk ini.",
        True,
    )
    loop._tts_with_fallback = MagicMock(return_value="/tmp/fallback.mp3")
    loop.audio_player = MagicMock()
    loop.bg_listener = MagicMock()

    with (
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True),
        patch("app.core.interaction_loop.state_manager.set_state"),
    ):
        result = loop._stream_and_speak(
            [{"role": "user", "content": "prompt"}],
            max_sentences=2,
            context_str="Sumber hanya membahas arsip La Galigo.",
        )

    assert result == "Tenri tidak punya informasi spesifik untuk ini."
    loop.answer_verifier.check.assert_called_once_with(
        "Klaim ini tidak didukung sumber.",
        "Sumber hanya membahas arsip La Galigo.",
    )
    loop._tts_with_fallback.assert_called_once_with(
        "Tenri tidak punya informasi spesifik untuk ini."
    )
    loop.audio_player.play_audio.assert_called_once_with("/tmp/fallback.mp3")


def test_streaming_grounding_waits_for_complete_sentence() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    llm = MagicMock()
    llm.client = True
    llm.stream_response_chunks.return_value = iter([
        "La Galigo bukan sekadar arsip, ",
        "ia menyimpan ingatan masyarakat Bugis."
    ])
    loop._llm = MagicMock(return_value=llm)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = False
    loop.answer_verifier = MagicMock()
    loop.answer_verifier.check.return_value = (
        "La Galigo bukan sekadar arsip, ia menyimpan ingatan masyarakat Bugis.",
        False,
    )
    loop.bg_listener = MagicMock()

    with (
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.time.sleep"),
    ):
        loop._stream_and_speak(
            [{"role": "user", "content": "prompt"}],
            max_sentences=1,
            context_str="La Galigo menyimpan ingatan masyarakat Bugis.",
        )

    checked_text = loop.answer_verifier.check.call_args.args[0]
    assert checked_text == (
        "La Galigo bukan sekadar arsip, ia menyimpan ingatan masyarakat Bugis."
    )


# ------------------------------------------------------------------ _tts_with_fallback

def test_tts_with_fallback_returns_elevenlabs_result() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True
    loop.elevenlabs_service.text_to_speech.return_value = "/cache/audio.mp3"
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = True

    with patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True):
        result = loop._tts_with_fallback("Halo Tenri")

    assert result == "/cache/audio.mp3"
    loop.local_tts_service.synthesize.assert_not_called()


def test_tts_with_fallback_uses_local_when_elevenlabs_returns_none() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True
    loop.elevenlabs_service.text_to_speech.return_value = None
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = True
    loop.local_tts_service.synthesize.return_value = "/tmp/local.wav"

    with patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True):
        result = loop._tts_with_fallback("Halo Tenri")

    assert result == "/tmp/local.wav"
    loop.local_tts_service.synthesize.assert_called_once_with("Halo Tenri")


def test_tts_with_fallback_uses_local_when_elevenlabs_client_is_none() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = True
    loop.local_tts_service.synthesize.return_value = "/tmp/local.wav"

    with patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True):
        result = loop._tts_with_fallback("Halo Tenri")

    loop.elevenlabs_service.text_to_speech.assert_not_called()
    assert result == "/tmp/local.wav"


def test_tts_with_fallback_returns_none_when_voice_output_disabled() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = True

    with patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False):
        result = loop._tts_with_fallback("Halo Tenri")

    assert result is None
    loop.elevenlabs_service.text_to_speech.assert_not_called()
    loop.local_tts_service.synthesize.assert_not_called()


def test_tts_with_fallback_returns_none_when_both_unavailable() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = True
    loop.elevenlabs_service.text_to_speech.return_value = None
    loop.local_tts_service = MagicMock()
    loop.local_tts_service.available = False

    with patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True):
        result = loop._tts_with_fallback("Halo Tenri")

    assert result is None
    loop.local_tts_service.synthesize.assert_not_called()


def test_do_interruption_uses_streaming_when_enabled() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.policy = MagicMock()
    loop.tracker = MagicMock()
    loop.tracker.format_context.return_value = ""
    loop.tracker.format_narrative_context.return_value = ""
    loop.prompt_builder = MagicMock()
    messages = [{"role": "user", "content": "prompt"}]
    loop.prompt_builder.build_messages.return_value = messages
    loop.memory = MagicMock()
    loop.memory.get_messages.return_value = []
    loop.groq_service = MagicMock()
    loop.groq_service.get_response_streaming.return_value = "Respons streaming."
    loop.session_logger = MagicMock()
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None
    loop.audio_player = MagicMock()

    with (
        patch("app.core.interaction_loop.state_manager.set_state"),
        patch("app.core.interaction_loop.TerminalUI.get_spinner") as spinner,
        patch("app.core.interaction_loop.TerminalUI.print_interruption"),
        patch("app.core.interaction_loop.Config.GROQ_STREAMING", True),
        patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False),
        patch("app.core.interaction_loop.time.sleep"),
    ):
        spinner.return_value.__enter__.return_value = None
        spinner.return_value.__exit__.return_value = False
        loop._do_interruption("comment", None, prompt="Prompt interupsi")

    loop.groq_service.get_response_streaming.assert_called_once_with(messages)
    loop.groq_service.get_response.assert_not_called()


def test_extract_stream_segment_prefers_sentence_boundary() -> None:
    segment, rest = InteractionLoop._extract_stream_segment(
        "AI membaca pola. Ia bukan manusia.",
        allow_soft=True,
    )

    assert segment == "AI membaca pola."
    assert rest == "Ia bukan manusia."


def test_extract_stream_segment_does_not_split_incomplete_decimal() -> None:
    """Buffer ending in 'digit.' is a possible decimal mid-stream — must not split (BUG-16)."""
    segment, rest = InteractionLoop._extract_stream_segment("Angka naik 3.", allow_soft=False)

    assert segment is None
    assert rest == "Angka naik 3."


def test_extract_stream_segment_splits_after_decimal_completes() -> None:
    """Once the decimal and a real sentence end arrive, the full sentence splits."""
    segment, rest = InteractionLoop._extract_stream_segment(
        "Angka naik 3.5 persen. Lalu turun.",
        allow_soft=False,
    )

    assert segment == "Angka naik 3.5 persen."
    assert rest == "Lalu turun."


def test_extract_stream_segment_still_splits_sentence_ending_in_number() -> None:
    """A real sentence ending in 'number.' followed by whitespace still splits."""
    segment, rest = InteractionLoop._extract_stream_segment(
        "Tercatat tahun 2024. Berikutnya naik.",
        allow_soft=False,
    )

    assert segment == "Tercatat tahun 2024."
    assert rest == "Berikutnya naik."


def test_extract_stream_segment_allows_soft_first_clause() -> None:
    segment, rest = InteractionLoop._extract_stream_segment(
        "AI bukan benar-benar berpikir, ia membaca pola dari data.",
        allow_soft=True,
    )

    assert segment == "AI bukan benar-benar berpikir."
    assert rest == "ia membaca pola dari data."


def test_extract_stream_segment_does_not_soft_split_after_first_segment() -> None:
    segment, rest = InteractionLoop._extract_stream_segment(
        "AI bukan benar-benar berpikir, ia membaca pola dari data",
        allow_soft=False,
    )

    assert segment is None
    assert rest == "AI bukan benar-benar berpikir, ia membaca pola dari data"


def test_extract_stream_segment_hard_splits_long_first_clause() -> None:
    text = (
        "Kecerdasan buatan sering terlihat seperti memahami manusia padahal ia sedang "
        "membaca pola statistik dari jejak data yang kita tinggalkan setiap hari tanpa henti"
    )

    segment, rest = InteractionLoop._extract_stream_segment(text, allow_soft=True)

    assert segment is not None
    assert segment.endswith(".")
    assert rest
