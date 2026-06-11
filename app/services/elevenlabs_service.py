import hashlib
import logging
import time

import requests

from app.config import Config
from app.utils.network import force_ipv4_for_hosts

# ElevenLabs DNS returns a NAT64 address (64:ff9b::/96) on some ISPs, which can
# cause TLS handshake failures on Windows. Force IPv4 for ElevenLabs hosts.
force_ipv4_for_hosts("elevenlabs")

logger = logging.getLogger("AICompanion.ElevenLabsService")

_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class ElevenLabsService:
    _circuit_open_until: float = 0.0

    def __init__(self):
        self.api_key = Config.ELEVENLABS_API_KEY
        self.voice_id = Config.ELEVENLABS_VOICE_ID
        # client is truthy when key is available, preserving existing checks.
        self.client = True if Config.ELEVENLABS_ENABLED and self.api_key else None

        if not Config.ELEVENLABS_ENABLED:
            logger.warning("ElevenLabs disabled by ELEVENLABS_ENABLED=false.")
        elif self.api_key:
            logger.info("ElevenLabs service ready (direct REST).")
        else:
            logger.warning("ElevenLabs API key not provided. Voice output will be disabled.")

    @classmethod
    def _circuit_open(cls) -> bool:
        return time.monotonic() < cls._circuit_open_until

    @classmethod
    def _open_circuit(cls, reason: str) -> None:
        seconds = max(0.0, Config.ELEVENLABS_CIRCUIT_BREAKER_SECONDS)
        cls._circuit_open_until = time.monotonic() + seconds
        logger.warning(
            "ElevenLabs temporarily disabled for %.0fs after network failure: %s",
            seconds,
            reason,
        )

    def _cache_key(self, text: str) -> str:
        """SHA256 digest of voice/model/settings/text for this exact audio."""
        model_id = Config.ELEVENLABS_MODEL or "eleven_flash_v2_5"
        raw = "|".join([
            self.voice_id,
            model_id,
            Config.ELEVENLABS_OUTPUT_FORMAT,
            str(Config.ELEVENLABS_OPTIMIZE_LATENCY),
            f"{Config.ELEVENLABS_VOICE_SPEED:.2f}",
            f"{Config.ELEVENLABS_STABILITY:.2f}",
            f"{Config.ELEVENLABS_SIMILARITY_BOOST:.2f}",
            str(Config.ELEVENLABS_USE_SPEAKER_BOOST),
            Config.tts_language_code() or "auto",
            text,
        ])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def text_to_speech(self, text: str) -> str | None:
        """Calls ElevenLabs REST API directly and caches generated audio."""
        if not self.client:
            logger.info("ElevenLabs is running in offline/mock mode.")
            return None

        cleaned_text = text.replace("[Offline Mode]", "").replace("[Error]", "").strip()
        if not cleaned_text:
            return None

        preview = cleaned_text[:30] + ("..." if len(cleaned_text) > 30 else "")

        cache_path = Config.TTS_CACHE_DIR / f"{self._cache_key(cleaned_text)}.mp3"
        if cache_path.exists():
            logger.info(f"TTS cache hit: '{preview}'")
            return str(cache_path)

        if self._circuit_open():
            logger.info("ElevenLabs circuit open; skipping cloud TTS for: '%s'", preview)
            return None

        try:
            logger.info(
                "Generating TTS for: '%s' using voice=%s model=%s format=%s speed=%.2f",
                preview,
                self.voice_id,
                Config.ELEVENLABS_MODEL,
                Config.ELEVENLABS_OUTPUT_FORMAT,
                Config.ELEVENLABS_VOICE_SPEED,
            )

            url = _TTS_URL.format(voice_id=self.voice_id)
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }
            params = {
                "output_format": Config.ELEVENLABS_OUTPUT_FORMAT,
            }
            if Config.ELEVENLABS_OPTIMIZE_LATENCY >= 0:
                params["optimize_streaming_latency"] = Config.ELEVENLABS_OPTIMIZE_LATENCY

            model_id = Config.ELEVENLABS_MODEL or "eleven_flash_v2_5"
            payload = {
                "text": cleaned_text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": Config.ELEVENLABS_STABILITY,
                    "similarity_boost": Config.ELEVENLABS_SIMILARITY_BOOST,
                    "style": 0.0,
                    "use_speaker_boost": Config.ELEVENLABS_USE_SPEAKER_BOOST,
                    "speed": Config.ELEVENLABS_VOICE_SPEED,
                },
            }
            # Only send language_code for a recognized ISO 639-1 code. For
            # "bilingual"/unknown, omit it so the multilingual model auto-detects
            # instead of rejecting the request with HTTP 400 (BUG-07).
            lang_code = Config.tts_language_code()
            if lang_code:
                payload["language_code"] = lang_code

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                params=params,
                timeout=(Config.ELEVENLABS_CONNECT_TIMEOUT, Config.ELEVENLABS_READ_TIMEOUT),
            )
            response.raise_for_status()

            Config.TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "wb") as f:
                f.write(response.content)

            logger.info(f"TTS cached: {cache_path.name} ({len(response.content)} bytes)")
            self.__class__._circuit_open_until = 0.0
            return str(cache_path)

        except requests.exceptions.HTTPError as e:
            logger.error(f"ElevenLabs HTTP error {e.response.status_code}: {e.response.text[:200]}")
            return None
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            self._open_circuit(str(e))
            return None
        except requests.exceptions.RequestException as e:
            logger.warning("ElevenLabs request failed: %s", e)
            return None
        except Exception as e:
            logger.error(f"Error during ElevenLabs TTS generation: {e}", exc_info=True)
            return None
