from unittest.mock import MagicMock, patch, call

from app.core.interaction_loop import InteractionLoop, _STATIC_TTS_PHRASES
from app.state import AppState


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

    with patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True):
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

    with patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", False):
        loop._prewarm_tts_cache()

    loop.elevenlabs_service.text_to_speech.assert_not_called()
    assert not hasattr(loop, "_prewarm_thread")


def test_prewarm_tts_cache_skips_when_client_is_none() -> None:
    loop = InteractionLoop.__new__(InteractionLoop)
    loop.elevenlabs_service = MagicMock()
    loop.elevenlabs_service.client = None

    with patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True):
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

    with patch("app.core.interaction_loop.Config.VOICE_OUTPUT_ENABLED", True):
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
