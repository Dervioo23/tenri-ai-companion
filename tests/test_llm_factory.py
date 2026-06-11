"""Shared LLM provider factory (BUG-09)."""

from unittest.mock import patch

from app.services.llm_factory import build_llm_service
from app.services.groq_service import GroqService
from app.services.gemini_service import GeminiService


def test_factory_returns_groq_for_groq_provider() -> None:
    with patch("app.services.llm_factory.Config.LLM_PROVIDER", "groq"):
        assert isinstance(build_llm_service(), GroqService)


def test_factory_returns_gemini_for_gemini_provider() -> None:
    with patch("app.services.llm_factory.Config.LLM_PROVIDER", "gemini"):
        assert isinstance(build_llm_service(), GeminiService)


def test_factory_reuses_passed_groq_service_for_groq_provider() -> None:
    existing = GroqService()
    with patch("app.services.llm_factory.Config.LLM_PROVIDER", "groq"):
        assert build_llm_service(existing) is existing


def test_factory_ignores_passed_groq_when_provider_is_gemini() -> None:
    existing = GroqService()
    with patch("app.services.llm_factory.Config.LLM_PROVIDER", "gemini"):
        assert isinstance(build_llm_service(existing), GeminiService)
