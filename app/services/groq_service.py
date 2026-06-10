import logging
from groq import Groq
from app.config import Config

logger = logging.getLogger("AICompanion.GroqService")

OFFLINE_FALLBACK_RESPONSE = "[Offline Mode] Maaf, koneksi ke Groq API tidak aktif. Silakan konfigurasi API Key Anda di file .env."

class GroqService:
    def __init__(self):
        self.api_key = Config.GROQ_API_KEY
        self.model = Config.GROQ_MODEL
        self.client = None
        
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info("Groq client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
        else:
            logger.warning("Groq API key not provided. Running in offline/mock mode for LLM.")

    def _model_candidates(self) -> list[str]:
        candidates = []
        if Config.GROQ_LIVE_MODEL:
            candidates.append(Config.GROQ_LIVE_MODEL)
        candidates.append(self.model)
        deduped = []
        for model in candidates:
            if model and model not in deduped:
                deduped.append(model)
        return deduped

    def get_response(self, messages: list) -> str:
        """
        Sends conversation history to Groq API and returns the character response.
        If Groq API key is missing or calls fail, returns a mock/fallback response.
        """
        if not self.client:
            logger.warning("Groq client not initialized. Returning mock response.")
            return OFFLINE_FALLBACK_RESPONSE

        try:
            last_error = None
            completion = None
            for model in self._model_candidates():
                try:
                    logger.info(f"Sending request to Groq using model: {model}")
                    completion = self.client.chat.completions.create(
                        messages=messages,
                        model=model,
                        temperature=0.7,
                        max_tokens=Config.LLM_MAX_TOKENS,
                    )
                    break
                except Exception as e:
                    last_error = e
                    if model != self.model:
                        logger.warning(f"Groq live model failed ({model}); trying fallback model: {e}")
                        continue
                    raise

            if completion is None and last_error:
                raise last_error

            response_text = (completion.choices[0].message.content or "").strip()
            if not response_text:
                logger.warning("Groq returned empty content.")
                return OFFLINE_FALLBACK_RESPONSE

            logger.info("Successfully received response from Groq.")
            return response_text

        except Exception as e:
            # Tangani rate limit secara khusus — tampilkan pesan bersih, bukan traceback
            err_str = str(e)
            if "rate_limit_exceeded" in err_str or "429" in err_str:
                wait = self._extract_wait_time(err_str)
                msg = f"Batas token harian Groq tercapai. Coba lagi dalam {wait}." if wait else \
                      "Batas token harian Groq tercapai. Coba lagi beberapa saat."
                logger.warning(f"Groq rate limit: {msg}")
                return f"[Offline Mode] {msg}"

            logger.error(f"Error during Groq API call: {e}", exc_info=True)
            return f"[Error] Terjadi kesalahan saat menghubungi otak AI saya: {err_str}"

    def get_response_streaming(self, messages: list) -> str:
        """Calls Groq with stream=True and returns the full assembled response."""
        if not self.client:
            return OFFLINE_FALLBACK_RESPONSE

        try:
            parts = []
            for delta in self.stream_response_chunks(messages):
                if delta:
                    parts.append(delta)
            response_text = "".join(parts).strip()
            if not response_text:
                logger.warning("Groq streaming returned empty content.")
                return OFFLINE_FALLBACK_RESPONSE
            logger.info("Successfully received streaming response from Groq.")
            return response_text

        except Exception as e:
            err_str = str(e)
            if "rate_limit_exceeded" in err_str or "429" in err_str:
                wait = self._extract_wait_time(err_str)
                msg = f"Batas token harian Groq tercapai. Coba lagi dalam {wait}." if wait else \
                      "Batas token harian Groq tercapai. Coba lagi beberapa saat."
                logger.warning(f"Groq rate limit (streaming): {msg}")
                return f"[Offline Mode] {msg}"
            logger.warning(f"Streaming failed, falling back to standard call: {e}")
            return self.get_response(messages)

    def stream_response_chunks(self, messages: list, max_tokens: int | None = None):
        """Yield raw text deltas from Groq stream=True."""
        last_error = None
        for model in self._model_candidates():
            try:
                stream = self.client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=0.7,
                    max_tokens=max_tokens or Config.LLM_MAX_TOKENS,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
                return
            except Exception as e:
                last_error = e
                if model != self.model:
                    logger.warning(f"Groq live streaming model failed ({model}); trying fallback model: {e}")
                    continue
                raise
        if last_error:
            raise last_error

    @staticmethod
    def _extract_wait_time(error_str: str) -> str:
        """Ekstrak waktu tunggu dari pesan rate limit Groq."""
        import re
        m = re.search(r"try again in (\d+m\d+\.\d+s|\d+h\d+m\d+s|\d+m\d+s)", error_str, re.IGNORECASE)
        return m.group(1) if m else ""
