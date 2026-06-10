from unittest.mock import patch

from app.utils.terminal_ui import TerminalUI


def test_timing_summary_separates_pipeline_metrics() -> None:
    with patch("app.utils.terminal_ui.console.print") as mock_print:
        TerminalUI.print_timing_summary(
            wait_s=1.2,
            record_s=2.3,
            stt_s=0.8,
            retrieval_s=0.1,
            first_voice_s=1.5,
            llm_s=0.6,
            tts_s=1.1,
            audio_playback_s=4.0,
            cycle_s=6.5,
        )

    rendered = str(mock_print.call_args.args[0])
    assert "Wait 1.2s" in rendered
    assert "Record 2.3s" in rendered
    assert "STT 0.8s" in rendered
    assert "Retrieval 0.1s" in rendered
    assert "FirstVoice 1.5s" in rendered
    assert "LLM 0.6s" in rendered
    assert "TTS 1.1s" in rendered
    assert "Audio 4.0s" in rendered
    assert "Cycle 6.5s" in rendered
