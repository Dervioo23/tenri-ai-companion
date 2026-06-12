from app.services.background_listener import BackgroundListener


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
