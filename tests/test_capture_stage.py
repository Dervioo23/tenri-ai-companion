from unittest.mock import MagicMock

from app.pipeline.capture_stage import CaptureStage, CaptureStatus


def _speech() -> MagicMock:
    speech = MagicMock()
    speech.microphone_available = True
    speech.last_wait_seconds = 0.2
    speech.last_record_seconds = 1.4
    speech.last_transcribe_seconds = 0.6
    return speech


def test_push_to_talk_capture_returns_structured_metrics() -> None:
    speech = _speech()
    speech.listen_and_transcribe.return_value = ("Tenri jelaskan ini", True)
    listener = MagicMock(available=False)
    stage = CaptureStage(speech, listener)
    prompts: list[bool] = []

    result = stage.capture(
        voice_enabled=True,
        push_to_talk=True,
        timeout=7.0,
        before_push_capture=lambda: prompts.append(True),
    )

    assert result.ok
    assert result.source == "push_to_talk"
    assert result.text == "Tenri jelaskan ini"
    assert result.record_seconds == 1.4
    assert prompts == [True]


def test_background_capture_uses_listener_metrics() -> None:
    speech = _speech()
    listener = MagicMock(available=True)
    listener.get.return_value = "Tenri"
    listener.last_wait_seconds = 0.4
    listener.last_record_seconds = 0.8
    listener.last_stt_seconds = 0.3
    stage = CaptureStage(speech, listener)

    result = stage.capture(
        voice_enabled=True,
        push_to_talk=False,
        timeout=5.0,
    )

    assert result.ok
    assert result.source == "background_listener"
    assert result.stt_seconds == 0.3
    listener.get.assert_called_once_with(timeout=5.0)


def test_sequential_voice_maps_unknown_audio_status() -> None:
    speech = _speech()
    speech.listen_and_transcribe.return_value = ("[UNKNOWN_AUDIO]", False)
    stage = CaptureStage(speech, MagicMock(available=False))

    result = stage.capture(
        voice_enabled=True,
        push_to_talk=False,
        timeout=5.0,
    )

    assert not result.ok
    assert result.status is CaptureStatus.UNKNOWN_AUDIO
    assert result.detail == "[UNKNOWN_AUDIO]"


def test_text_capture_is_independent_from_microphone() -> None:
    speech = _speech()
    speech.microphone_available = False
    stage = CaptureStage(speech, MagicMock(), text_input=lambda _prompt: "  Halo Tenri  ")

    result = stage.capture(
        voice_enabled=True,
        push_to_talk=False,
        timeout=5.0,
    )

    assert result.ok
    assert result.source == "text"
    assert result.text == "Halo Tenri"
