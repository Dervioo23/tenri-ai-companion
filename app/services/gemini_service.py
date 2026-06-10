import logging

from app.config import Config

logger = logging.getLogger("AICompanion.GeminiService")

OFFLINE_FALLBACK_RESPONSE = "[Offline Mode] Maaf, koneksi ke Gemini API tidak aktif. Silakan konfigurasi GEMINI_API_KEY di file .env."


class GeminiService:
    """Gemini LLM adapter using the Google Gen AI SDK."""

    provider_name = "gemini"

    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model = Config.GEMINI_MODEL
        self.client = None
        self._types = None

        if not self.api_key:
            logger.warning("Gemini API key not provided. Running in offline/mock mode for LLM.")
            return

        try:
            from google import genai
            from google.genai import types

            self._types = types
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Gemini client initialized successfully.")
        except ImportError as e:
            logger.warning(f"google-genai is not installed. Gemini is unavailable: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")

    def get_response(self, messages: list) -> str:
        """Send a blocking Gemini request and return text."""
        if not self.client:
            logger.warning("Gemini client not initialized. Returning fallback response.")
            return OFFLINE_FALLBACK_RESPONSE

        try:
            logger.info(f"Sending request to Gemini using model: {self.model}")
            system_instruction, contents = self._convert_messages(messages)
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=self._build_config(system_instruction, Config.LLM_MAX_TOKENS),
            )
            response_text = (getattr(response, "text", "") or "").strip()
            if not response_text:
                logger.warning("Gemini returned empty content.")
                return OFFLINE_FALLBACK_RESPONSE
            logger.info("Successfully received response from Gemini.")
            return response_text

        except Exception as e:
            return self._handle_error(e, "Gemini API call")

    def get_response_streaming(self, messages: list) -> str:
        """Call Gemini with generate_content_stream and return assembled text."""
        if not self.client:
            return OFFLINE_FALLBACK_RESPONSE

        try:
            parts = []
            for delta in self.stream_response_chunks(messages):
                if delta:
                    parts.append(delta)
            response_text = "".join(parts).strip()
            if not response_text:
                logger.warning("Gemini streaming returned empty content.")
                return OFFLINE_FALLBACK_RESPONSE
            logger.info("Successfully received streaming response from Gemini.")
            return response_text
        except Exception as e:
            logger.warning(f"Gemini streaming failed, falling back to standard call: {e}")
            return self.get_response(messages)

    def stream_response_chunks(self, messages: list, max_tokens: int | None = None):
        """Yield raw text chunks from Gemini streaming."""
        system_instruction, contents = self._convert_messages(messages)
        stream = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=self._build_config(system_instruction, max_tokens or Config.LLM_MAX_TOKENS),
        )
        for chunk in stream:
            delta = (getattr(chunk, "text", "") or "")
            if delta:
                yield delta

    def _build_config(self, system_instruction: str, max_tokens: int):
        kwargs = {
            "temperature": 0.7,
            "max_output_tokens": max_tokens,
        }
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        return self._types.GenerateContentConfig(**kwargs)

    def _convert_messages(self, messages: list) -> tuple[str, list]:
        """Convert OpenAI-style messages into Gemini contents.

        Gemini expects "user" and "model" roles. System messages are moved into
        system_instruction so Tenri's persona/rules stay authoritative.
        """
        system_parts: list[str] = []
        contents: list[dict] = []

        for message in messages or []:
            role = (message.get("role") or "user").lower()
            content = str(message.get("content") or "").strip()
            if not content:
                continue

            if role == "system":
                system_parts.append(content)
                continue

            gemini_role = "model" if role == "assistant" else "user"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": content}],
            })

        if not contents:
            contents.append({"role": "user", "parts": [{"text": ""}]})

        return "\n\n".join(system_parts), contents

    def _handle_error(self, error: Exception, context: str) -> str:
        err_str = str(error)
        lowered = err_str.lower()
        if "429" in err_str or "quota" in lowered or "rate" in lowered:
            logger.warning(f"Gemini rate/quota limit: {err_str}")
            return "[Offline Mode] Batas kuota Gemini tercapai atau request sedang dibatasi. Coba lagi beberapa saat."

        logger.error(f"Error during {context}: {error}", exc_info=True)
        return f"[Error] Terjadi kesalahan saat menghubungi Gemini: {err_str}"
