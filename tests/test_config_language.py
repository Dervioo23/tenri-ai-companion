"""Language-handling helpers on Config (BUG-07)."""

import pytest

from app.config import Config


@pytest.mark.parametrize(
    ("app_language", "expected"),
    [
        ("id", "id"),
        ("en", "en"),
        ("bilingual", None),   # auto: ElevenLabs multilingual model auto-detects
        ("xx", None),          # unknown → auto, never an invalid language_code
    ],
)
def test_tts_language_code(monkeypatch, app_language, expected) -> None:
    monkeypatch.setattr(Config, "APP_LANGUAGE", app_language)
    assert Config.tts_language_code() == expected


@pytest.mark.parametrize(
    ("app_language", "expected"),
    [
        ("id", "id"),
        ("en", "en"),
        ("bilingual", "id"),   # Indonesian-first default, not a silent "en"
        ("xx", "id"),
    ],
)
def test_stt_language_code(monkeypatch, app_language, expected) -> None:
    monkeypatch.setattr(Config, "APP_LANGUAGE", app_language)
    assert Config.stt_language_code() == expected


def test_validate_warns_on_unknown_language(monkeypatch) -> None:
    monkeypatch.setattr(Config, "APP_LANGUAGE", "klingon")
    _errors, warnings = Config.validate_critical_configs()
    assert any("APP_LANGUAGE" in w for w in warnings)


@pytest.mark.parametrize("app_language", ["id", "en", "bilingual"])
def test_validate_accepts_known_languages(monkeypatch, app_language) -> None:
    monkeypatch.setattr(Config, "APP_LANGUAGE", app_language)
    _errors, warnings = Config.validate_critical_configs()
    assert not any("APP_LANGUAGE" in w for w in warnings)
