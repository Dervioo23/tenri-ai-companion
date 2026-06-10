import hashlib
import logging
import socket

import requests

from app.config import Config

# ElevenLabs DNS returns a NAT64 address (64:ff9b::/96) on some ISPs, which can
# cause TLS handshake failures on Windows. Force IPv4 for ElevenLabs hosts.
_orig_getaddrinfo = socket.getaddrinfo


def _elevenlabs_force_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    if host and "elevenlabs" in str(host):
        results = _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        if results:
            return results
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _elevenlabs_force_ipv4

logger = logging.getLogger("AICompanion.ElevenLabsService")

_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_TIMEOUT = (5, 20)  # (connect_timeout, read_timeout) - fail fast for live demos


class ElevenLabsService:
    def __init__(self):
        self.api_key = Config.ELEVENLABS_API_KEY
        self.voice_id = Config.ELEVENLABS_VOICE_ID
        # client is truthy when key is available, preserving existing checks.
        self.client = True if self.api_key else None

        if self.api_key:
            logger.info("ElevenLabs service ready (direct REST).")
        else:
            logger.warning("ElevenLabs API key not provided. Voice output will be disabled.")

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
                "language_code": Config.APP_LANGUAGE,
                "voice_settings": {
                    "stability": Config.ELEVENLABS_STABILITY,
                    "similarity_boost": Config.ELEVENLABS_SIMILARITY_BOOST,
                    "style": 0.0,
                    "use_speaker_boost": Config.ELEVENLABS_USE_SPEAKER_BOOST,
                    "speed": Config.ELEVENLABS_VOICE_SPEED,
                },
            }

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                params=params,
                timeout=_TIMEOUT,
            )
            response.raise_for_status()

            Config.TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "wb") as f:
                f.write(response.content)

            logger.info(f"TTS cached: {cache_path.name} ({len(response.content)} bytes)")
            return str(cache_path)

        except requests.exceptions.HTTPError as e:
            logger.error(f"ElevenLabs HTTP error {e.response.status_code}: {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Error during ElevenLabs TTS generation: {e}", exc_info=True)
            return None
