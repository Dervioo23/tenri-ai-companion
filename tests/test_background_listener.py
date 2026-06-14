from unittest.mock import MagicMock, patch

import speech_recognition as sr

from app.services.background_listener import BackgroundListener


def _speech_service() -> MagicMock:
    service = MagicMock()
    service.microphone_available = True
    service.device_index = None
    service.calibrate_background_energy.return_value = 420
    service.recognizer = MagicMock()
    return service


def test_background_listener_get_exposes_current_utterance_metrics() -> None:
    listener = BackgroundListener(speech_service=object())
    listener._queue.put(("Jelaskan slide pertama ini", {"record_s": 2.4, "stt_s": 0.8}))

    text = listener.get(timeout=0.01)

    assert text == "Jelaskan slide pertama ini"
    assert listener.last_wait_seconds >= 0.0
    assert listener.last_record_seconds == 2.4
    assert listener.last_stt_seconds == 0.8


def test_background_listener_timeout_resets_record_and_stt_metrics() -> None:
    listener = BackgroundListener(speech_service=object())
    listener.last_record_seconds = 2.4
    listener.last_stt_seconds = 0.8

    text = listener.get(timeout=0.01)

    assert text is None
    assert listener.last_wait_seconds >= 0.0
    assert listener.last_record_seconds == 0.0
    assert listener.last_stt_seconds == 0.0


def test_audio_recorded_during_mute_is_rejected_after_unmute_buffer() -> None:
    listener = BackgroundListener(speech_service=object())
    listener.available = True
    listener._mute_started_at = 100.0
    listener._mute_windows = [(100.0, 107.2)]

    # Callback arrives after the post-unmute buffer, but its 5-second recording
    # began inside the mute window: [103.0, 108.0] overlaps [100.0, 107.2].
    assert listener._audio_overlaps_mute_window(5.0, callback_at=108.0)


def test_audio_recorded_fully_after_mute_window_is_allowed() -> None:
    listener = BackgroundListener(speech_service=object())
    listener._mute_windows = [(100.0, 107.2)]

    # Recording interval [108.0, 110.0] starts after suppression ended.
    assert not listener._audio_overlaps_mute_window(2.0, callback_at=110.0)


def test_current_open_mute_window_rejects_audio() -> None:
    listener = BackgroundListener(speech_service=object())
    listener._mute_started_at = 100.0

    assert listener._audio_overlaps_mute_window(1.0, callback_at=101.0)


def test_mute_unmute_records_suppression_window(monkeypatch) -> None:
    listener = BackgroundListener(speech_service=object())
    listener.available = True
    times = iter([100.0, 105.0])
    monkeypatch.setattr("app.services.background_listener.time.monotonic", lambda: next(times))

    listener.mute()
    listener.unmute()

    assert listener._mute_windows == [(100.0, 107.2)]
    assert listener._mute_started_at is None


def test_start_opens_microphone_once_and_reports_ready() -> None:
    service = _speech_service()
    source = MagicMock()
    microphone = MagicMock()
    microphone.__enter__.return_value = source

    def listen_until_stopped(*_args, **_kwargs):
        raise sr.WaitTimeoutError()

    service.recognizer.listen.side_effect = listen_until_stopped
    listener = BackgroundListener(service)

    with patch("app.services.background_listener.sr.Microphone", return_value=microphone) as mic:
        assert listener.start() is True
        listener.stop()

    mic.assert_called_once_with(device_index=None)
    assert listener.available is False


def test_start_is_idempotent_while_capture_thread_is_alive() -> None:
    service = _speech_service()
    listener = BackgroundListener(service)
    listener._thread = MagicMock()
    listener._thread.is_alive.return_value = True

    with patch("app.services.background_listener.sr.Microphone") as microphone:
        assert listener.start() is True

    microphone.assert_not_called()
    service.calibrate_background_energy.assert_not_called()


def test_start_fails_cleanly_when_microphone_context_cannot_open() -> None:
    service = _speech_service()
    microphone = MagicMock()
    microphone.__enter__.side_effect = OSError("CoreAudio denied access")
    listener = BackgroundListener(service)

    with patch("app.services.background_listener.sr.Microphone", return_value=microphone):
        assert listener.start() is False

    assert listener.available is False
    assert listener._thread is None
