"""Shared factory for selecting the configured LLM provider.

Single source of truth so every entry point (InteractionLoop, rehearsal runner,
scripts) honours LLM_PROVIDER instead of hard-coding one provider.
"""

from app.config import Config
from app.services.groq_service import GroqService
from app.services.gemini_service import GeminiService


def build_llm_service(groq_service=None):
    """Return the LLM provider selected by Config.LLM_PROVIDER.

    Pass an existing GroqService to reuse it: InteractionLoop keeps one around for
    Groq Whisper STT regardless of which LLM provider is active.
    """
    if Config.LLM_PROVIDER == "gemini":
        return GeminiService()
    return groq_service if groq_service is not None else GroqService()
