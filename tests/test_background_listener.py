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
