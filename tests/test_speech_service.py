import logging
from unittest.mock import MagicMock, patch

from app.services import speech_service as speech_service_module
from app.services.speech_service import SpeechService
import pytest
import speech_recognition as sr


def test_background_energy_threshold_caps_unrealistic_configuration() -> None:
    assert SpeechService.background_energy_threshold(447, 1200) == 715


def test_background_energy_threshold_keeps_configured_ceiling() -> None:
    assert SpeechService.background_energy_threshold(600, 700) == 700


def test_background_energy_threshold_has_noise_floor() -> None:
    assert SpeechService.background_energy_threshold(0, 700) == 300


def test_speech_service_exists() -> None:
    service = SpeechService()
    assert isinstance(service.microphone_available, bool)


def test_parse_invalid_device_index_falls_back_to_default() -> None:
    assert SpeechService._parse_device_index("not-a-number") is None


def test_microphone_source_reports_failed_coreaudio_stream_without_cleanup_mask() -> None:
    microphone = MagicMock()
    microphone.stream = None
    microphone.__enter__.return_value = microphone

    with patch(
        "app.services.speech_service.sr.Microphone",
        return_value=microphone,
    ):
        with pytest.raises(OSError, match="CoreAudio could not open"):
            with SpeechService.microphone_source(None):
                pass

    microphone.__exit__.assert_not_called()


def test_microphone_source_closes_opened_stream() -> None:
    microphone = MagicMock()
    stream = MagicMock()
    audio = MagicMock()
    microphone.stream = stream
    microphone.audio = audio
    microphone.__enter__.return_value = microphone

    with patch(
        "app.services.speech_service.sr.Microphone",
        return_value=microphone,
    ):
        with SpeechService.microphone_source(2) as source:
            assert source is microphone

    stream.close.assert_called_once_with()
    audio.terminate.assert_called_once_with()
    assert microphone.stream is None
    microphone.__exit__.assert_not_called()


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
        ("Tengri, kamu dengar saya?", "Tenri, kamu dengar saya?"),
        ("Oke Hendri jelaskan arsip ini", "Tenri jelaskan arsip ini"),
        ("Ten ri tolong lanjut", "Tenri tolong lanjut"),
        ("Hendri Hendri", "Tenri"),
        ("Tenri Tengri", "Tenri"),
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


# ------------------------------------------------------------------ ambiguous closing phrase (BUG-02)

import struct


def _voiced_audio(seconds: float = 1.0, amplitude: int = 1000, rate: int = 16000) -> sr.AudioData:
    """Build non-silent AudioData that passes _validate_audio_quality (RMS/duration)."""
    n = int(rate * seconds)
    frames = struct.pack(f"<{n}h", *([amplitude] * n))
    return sr.AudioData(frames, rate, 2)


class _Seg:
    def __init__(self, no_speech_prob: float, avg_logprob: float):
        self.no_speech_prob = no_speech_prob
        self.avg_logprob = avg_logprob


class _VerboseResult:
    def __init__(self, text: str, segments: list):
        self.text = text
        self.segments = segments


class _FakeTranscriptions:
    def __init__(self, verbose_result=None, verbose_exc=None, text_result=None):
        self._verbose_result = verbose_result
        self._verbose_exc = verbose_exc
        self._text_result = text_result

    def create(self, **kwargs):
        if kwargs.get("response_format") == "verbose_json":
            if self._verbose_exc is not None:
                raise self._verbose_exc
            return self._verbose_result
        return self._text_result


class _FakeGroqClient:
    def __init__(self, transcriptions: _FakeTranscriptions):
        self.audio = type("_A", (), {"transcriptions": transcriptions})()


def _service_with_fake_groq(transcriptions: _FakeTranscriptions) -> SpeechService:
    service = SpeechService()
    service._groq_client = _FakeGroqClient(transcriptions)
    return service


def test_terima_kasih_kept_when_confident_speech() -> None:
    """Low no_speech_prob → 'terima kasih' is genuine speech, must pass through (BUG-02)."""
    fake = _FakeTranscriptions(
        verbose_result=_VerboseResult("Terima kasih", [_Seg(no_speech_prob=0.1, avg_logprob=-0.2)])
    )
    service = _service_with_fake_groq(fake)

    result = service._transcribe_with_groq(_voiced_audio())

    assert result.strip().lower() == "terima kasih"


def test_terima_kasih_filtered_when_no_segments() -> None:
    """No confidence signal (empty segments) → ambiguous phrase filtered as precaution."""
    fake = _FakeTranscriptions(verbose_result=_VerboseResult("terima kasih", []))
    service = _service_with_fake_groq(fake)

    with pytest.raises(sr.UnknownValueError):
        service._transcribe_with_groq(_voiced_audio())


def test_terima_kasih_filtered_on_text_format_fallback() -> None:
    """verbose_json unavailable → text fallback has no confidence → ambiguous phrase filtered."""
    fake = _FakeTranscriptions(
        verbose_exc=RuntimeError("verbose_json unsupported"),
        text_result="terima kasih",
    )
    service = _service_with_fake_groq(fake)

    with pytest.raises(sr.UnknownValueError):
        service._transcribe_with_groq(_voiced_audio())


def test_hard_hallucination_filtered_even_when_confident() -> None:
    """Pure video artifacts ('thanks for watching') stay filtered regardless of confidence."""
    fake = _FakeTranscriptions(
        verbose_result=_VerboseResult(
            "thanks for watching", [_Seg(no_speech_prob=0.1, avg_logprob=-0.2)]
        )
    )
    service = _service_with_fake_groq(fake)

    with pytest.raises(sr.UnknownValueError):
        service._transcribe_with_groq(_voiced_audio())
