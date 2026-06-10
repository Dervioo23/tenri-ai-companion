import logging

from app.services import speech_service as speech_service_module
from app.services.speech_service import SpeechService
import pytest
import speech_recognition as sr


def test_speech_service_exists() -> None:
    service = SpeechService()
    assert isinstance(service.microphone_available, bool)


def test_parse_invalid_device_index_falls_back_to_default() -> None:
    assert SpeechService._parse_device_index("not-a-number") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hendri, kamu dengar saya?", "Tenri, kamu dengar saya?"),
        ("Henry apa kamu siap?", "Tenri apa kamu siap?"),
        ("Endri tolong dengarkan", "Tenri tolong dengarkan"),
        ("Andri jelaskan slide ini", "Tenri jelaskan slide ini"),
        ("Tendry apa kamu dengar?", "Tenri apa kamu dengar?"),
        ("Ten li bantu saya", "Tenri bantu saya"),
        ("Teneri jawab singkat", "Tenri jawab singkat"),
        ("Oke Hendri jelaskan arsip ini", "Tenri jelaskan arsip ini"),
        ("Ten ri tolong lanjut", "Tenri tolong lanjut"),
        ("Hendri Hendri", "Tenri"),
        ("Saya mengenal Hendri di luar konteks ini", "Saya mengenal Tenri di luar konteks ini"),
    ],
)
def test_normalize_transcription_corrects_tenri_wake_word_variants(raw, expected) -> None:
    assert SpeechService.normalize_transcription(raw) == expected


def test_normalize_transcription_corrects_jelaskan_command_variant() -> None:
    assert (
        SpeechService.normalize_transcription("Hai jelas cut slide pertama ini")
        == "Hai jelaskan slide pertama ini"
    )


def test_normalize_transcription_removes_duplicate_phrase_from_echo() -> None:
    assert (
        SpeechService.normalize_transcription(
            "jelaskan slide pertama ini jelaskan slide pertama ini"
        )
        == "jelaskan slide pertama ini"
    )


def test_audio_duration_seconds_reads_audio_data_duration() -> None:
    audio = sr.AudioData(b"\0" * (16000 * 2 * 3), 16000, 2)

    assert SpeechService.audio_duration_seconds(audio) == 3.0


def test_cap_audio_for_stt_trims_audio_longer_than_limit() -> None:
    audio = sr.AudioData(b"\0" * (16000 * 2 * 10), 16000, 2)

    capped = SpeechService.cap_audio_for_stt(audio, max_seconds=4.0)

    assert SpeechService.audio_duration_seconds(capped) == 4.0


def test_cap_audio_for_stt_keeps_audio_within_limit() -> None:
    audio = sr.AudioData(b"\0" * (16000 * 2 * 3), 16000, 2)

    capped = SpeechService.cap_audio_for_stt(audio, max_seconds=4.0)

    assert capped is audio


def test_cap_audio_for_stt_warns_when_hard_cap_repeats(caplog) -> None:
    speech_service_module._CLIP_EVENT_TIMES.clear()
    audio = sr.AudioData(b"\0" * (16000 * 2 * 10), 16000, 2)

    with caplog.at_level(logging.WARNING, logger="AICompanion.SpeechService"):
        for _ in range(3):
            SpeechService.cap_audio_for_stt(audio, max_seconds=4.0)

    assert "Repeated STT hard-cap clips" in caplog.text
    speech_service_module._CLIP_EVENT_TIMES.clear()
