import hashlib
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from app.config import Config
from app.services.elevenlabs_service import ElevenLabsService


def make_service(tmp_path):
    ElevenLabsService._circuit_open_until = 0.0
    service = ElevenLabsService.__new__(ElevenLabsService)
    service.voice_id = "voice-test"
    service.api_key = "test-key"
    service.client = True  # truthy — same as real __init__ when key is present
    return service


def _mock_response():
    resp = MagicMock()
    resp.content = b"audio-bytes"
    resp.raise_for_status.return_value = None
    return resp


def _expected_cache_path(
    tmp_path: Path,
    text: str,
    voice_id: str = "voice-test",
    model: str = "eleven_flash_v2_5",
) -> Path:
    raw = "|".join([
        voice_id,
        model,
        Config.ELEVENLABS_OUTPUT_FORMAT,
        str(Config.ELEVENLABS_OPTIMIZE_LATENCY),
        f"{Config.ELEVENLABS_VOICE_SPEED:.2f}",
        f"{Config.ELEVENLABS_STABILITY:.2f}",
        f"{Config.ELEVENLABS_SIMILARITY_BOOST:.2f}",
        str(Config.ELEVENLABS_USE_SPEAKER_BOOST),
        Config.tts_language_code() or "auto",
        text,
    ])
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return tmp_path / f"{digest}.mp3"


# ------------------------------------------------------------------ log preview

def test_tts_log_preview_without_ellipsis_for_short_text(tmp_path, caplog) -> None:
    service = make_service(tmp_path)

    with patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path):
        with patch("app.services.elevenlabs_service.requests.post", return_value=_mock_response()):
            with caplog.at_level(logging.INFO, logger="AICompanion.ElevenLabsService"):
                result = service.text_to_speech("Halo Tenri")

    assert result is not None
    assert "Generating TTS for: 'Halo Tenri'" in caplog.text
    assert "voice=voice-test" in caplog.text
    assert "Halo Tenri..." not in caplog.text


def test_tts_log_preview_uses_ellipsis_only_for_long_text(tmp_path, caplog) -> None:
    service = make_service(tmp_path)
    text = "123456789012345678901234567890lebih"

    with patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path):
        with patch("app.services.elevenlabs_service.requests.post", return_value=_mock_response()):
            with caplog.at_level(logging.INFO, logger="AICompanion.ElevenLabsService"):
                result = service.text_to_speech(text)

    assert result is not None
    assert "Generating TTS for: '123456789012345678901234567890...'" in caplog.text


# ------------------------------------------------------------------ cache: miss → save

def test_tts_cache_miss_calls_api_and_saves_file(tmp_path) -> None:
    service = make_service(tmp_path)
    text = "Saya Tenri."

    with patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path):
        with patch("app.services.elevenlabs_service.requests.post", return_value=_mock_response()) as mock_post:
            result = service.text_to_speech(text)

    assert result is not None
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["params"]["output_format"] == Config.ELEVENLABS_OUTPUT_FORMAT
    assert kwargs["params"]["optimize_streaming_latency"] == Config.ELEVENLABS_OPTIMIZE_LATENCY
    assert kwargs["json"]["model_id"] == Config.ELEVENLABS_MODEL
    assert kwargs["json"]["voice_settings"]["speed"] == Config.ELEVENLABS_VOICE_SPEED
    assert kwargs["json"]["voice_settings"]["use_speaker_boost"] is Config.ELEVENLABS_USE_SPEAKER_BOOST
    assert Path(result).exists()
    assert Path(result).read_bytes() == b"audio-bytes"


def test_tts_uses_configured_timeout(tmp_path) -> None:
    service = make_service(tmp_path)

    with (
        patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path),
        patch("app.services.elevenlabs_service.Config.ELEVENLABS_CONNECT_TIMEOUT", 3.0),
        patch("app.services.elevenlabs_service.Config.ELEVENLABS_READ_TIMEOUT", 9.0),
        patch("app.services.elevenlabs_service.requests.post", return_value=_mock_response()) as mock_post,
    ):
        service.text_to_speech("Halo Tenri")

    _, kwargs = mock_post.call_args
    assert kwargs["timeout"] == (3.0, 9.0)


def test_tts_timeout_opens_circuit_and_skips_next_uncached_call(tmp_path, caplog) -> None:
    service = make_service(tmp_path)

    with (
        patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path),
        patch("app.services.elevenlabs_service.Config.ELEVENLABS_CIRCUIT_BREAKER_SECONDS", 60.0),
        patch(
            "app.services.elevenlabs_service.requests.post",
            side_effect=requests.exceptions.ReadTimeout("slow network"),
        ) as mock_post,
        caplog.at_level(logging.WARNING, logger="AICompanion.ElevenLabsService"),
    ):
        first = service.text_to_speech("Halo Tenri")
        second = service.text_to_speech("Kalimat lain")

    assert first is None
    assert second is None
    assert mock_post.call_count == 1
    assert "temporarily disabled" in caplog.text


def test_tts_cache_miss_saves_to_sha256_named_file(tmp_path) -> None:
    service = make_service(tmp_path)
    text = "Saya Tenri."

    with patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path):
        with patch("app.services.elevenlabs_service.requests.post", return_value=_mock_response()):
            result = service.text_to_speech(text)

    expected = _expected_cache_path(tmp_path, text)
    assert Path(result) == expected


# ------------------------------------------------------------------ cache: hit → no API call

def test_tts_cache_hit_skips_api_call(tmp_path, caplog) -> None:
    service = make_service(tmp_path)
    text = "Ya, saya di sini."

    # Pre-seed cache
    cache_file = _expected_cache_path(tmp_path, text)
    cache_file.write_bytes(b"cached-audio")

    with patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path):
        with patch("app.services.elevenlabs_service.requests.post") as mock_post:
            with caplog.at_level(logging.INFO, logger="AICompanion.ElevenLabsService"):
                result = service.text_to_speech(text)

    mock_post.assert_not_called()
    assert result == str(cache_file)
    assert "TTS cache hit" in caplog.text


def test_tts_cache_hit_returns_existing_file_content(tmp_path) -> None:
    service = make_service(tmp_path)
    text = "Ya, saya di sini."

    cache_file = _expected_cache_path(tmp_path, text)
    cache_file.write_bytes(b"cached-audio-data")

    with patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path):
        with patch("app.services.elevenlabs_service.requests.post"):
            result = service.text_to_speech(text)

    assert Path(result).read_bytes() == b"cached-audio-data"


def test_tts_cache_different_voice_produces_different_key(tmp_path) -> None:
    service_a = make_service(tmp_path)
    service_a.voice_id = "voice-A"
    service_b = make_service(tmp_path)
    service_b.voice_id = "voice-B"

    key_a = service_a._cache_key("Halo.")
    key_b = service_b._cache_key("Halo.")
    assert key_a != key_b


def test_tts_cache_same_voice_same_text_produces_same_key(tmp_path) -> None:
    service = make_service(tmp_path)
    assert service._cache_key("Halo.") == service._cache_key("Halo.")


# ------------------------------------------------------------------ offline

def test_tts_disabled_by_feature_flag(caplog) -> None:
    with (
        patch("app.services.elevenlabs_service.Config.ELEVENLABS_ENABLED", False),
        patch("app.services.elevenlabs_service.Config.ELEVENLABS_API_KEY", "test-key"),
        caplog.at_level(logging.WARNING, logger="AICompanion.ElevenLabsService"),
    ):
        service = ElevenLabsService()

    assert service.client is None
    assert "ElevenLabs disabled" in caplog.text


def test_tts_returns_none_when_client_is_none(tmp_path) -> None:
    service = make_service(tmp_path)
    service.client = None

    with patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path):
        result = service.text_to_speech("Halo Tenri")

    assert result is None


# ------------------------------------------------------------------ language_code (BUG-07)

def test_tts_payload_sends_language_code_for_known_iso(tmp_path) -> None:
    """APP_LANGUAGE=id → language_code 'id' is sent to ElevenLabs."""
    service = make_service(tmp_path)

    with patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path), \
         patch("app.services.elevenlabs_service.Config.APP_LANGUAGE", "id"), \
         patch("app.services.elevenlabs_service.requests.post", return_value=_mock_response()) as mock_post:
        service.text_to_speech("Halo Tenri")

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["language_code"] == "id"


def test_tts_payload_omits_language_code_for_bilingual(tmp_path) -> None:
    """APP_LANGUAGE=bilingual → language_code omitted (multilingual auto-detect), no HTTP 400."""
    service = make_service(tmp_path)

    with patch("app.services.elevenlabs_service.Config.TTS_CACHE_DIR", tmp_path), \
         patch("app.services.elevenlabs_service.Config.APP_LANGUAGE", "bilingual"), \
         patch("app.services.elevenlabs_service.requests.post", return_value=_mock_response()) as mock_post:
        result = service.text_to_speech("Halo Tenri")

    assert result is not None
    _, kwargs = mock_post.call_args
    assert "language_code" not in kwargs["json"]


def test_tts_cache_key_differs_per_language(tmp_path) -> None:
    """id, en, and bilingual must not collide in the TTS cache."""
    service = make_service(tmp_path)

    with patch("app.services.elevenlabs_service.Config.APP_LANGUAGE", "id"):
        key_id = service._cache_key("Halo.")
    with patch("app.services.elevenlabs_service.Config.APP_LANGUAGE", "en"):
        key_en = service._cache_key("Halo.")
    with patch("app.services.elevenlabs_service.Config.APP_LANGUAGE", "bilingual"):
        key_bi = service._cache_key("Halo.")

    assert len({key_id, key_en, key_bi}) == 3
