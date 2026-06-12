"""Streaming TTS over ElevenLabs WebSocket (TAHAP 2).

Replaces the REST "generate a full MP3 file, then play it" model with a true
pipeline: send the sentence, receive PCM audio chunks, and play each chunk the
instant it arrives via a PyAudio output stream — first sound in ~0.5 s instead of
after a whole MP3 round-trip.

Design notes:
- Output is raw PCM (``pcm_22050`` by default) so there is no MP3 decode cost.
- Keep this opt-in (``ELEVENLABS_STREAMING``). On any failure ``speak`` returns
  False so the caller falls back to the REST path / edge-tts.
- The SHA256 cache and static-phrase pre-warm stay on the REST path; streaming is
  for fresh, dynamic sentences where there is nothing to cache.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys
import time
from urllib.parse import urlencode

from app.config import Config

logger = logging.getLogger("AICompanion.StreamingTTS")

_WS_URL = "wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"


class StreamingTTS:
    _circuit_open_until: float = 0.0

    def __init__(self) -> None:
        self.api_key = Config.ELEVENLABS_API_KEY
        self.voice_id = Config.ELEVENLABS_VOICE_ID

        self._ws_ok = False
        try:
            import websockets  # noqa: F401
            self._ws_ok = True
        except Exception as e:  # pragma: no cover - import guard
            logger.warning("websockets not available; streaming TTS disabled: %s", e)

        self.available = bool(Config.ELEVENLABS_STREAMING and self.api_key and self._ws_ok)
        self._rate = self._parse_rate(Config.ELEVENLABS_STREAM_OUTPUT_FORMAT)
        self.last_playback_seconds = 0.0
        if self.available:
            logger.info("Streaming TTS ready (WebSocket, %s).", Config.ELEVENLABS_STREAM_OUTPUT_FORMAT)

    @staticmethod
    def _parse_rate(fmt: str) -> int:
        """'pcm_22050' -> 22050 (sample rate for the output PyAudio stream)."""
        try:
            return int(fmt.split("_")[1])
        except (IndexError, ValueError):
            return 22050

    def _build_uri(self) -> str:
        params = {
            "model_id": Config.ELEVENLABS_MODEL or "eleven_flash_v2_5",
            "output_format": Config.ELEVENLABS_STREAM_OUTPUT_FORMAT,
            "auto_mode": str(Config.ELEVENLABS_STREAM_AUTO_MODE).lower(),
            "inactivity_timeout": max(5, Config.ELEVENLABS_STREAM_INACTIVITY_TIMEOUT),
        }
        lang = Config.tts_language_code()
        if lang:
            params["language_code"] = lang
        return f"{_WS_URL.format(voice_id=self.voice_id)}?{urlencode(params)}"

    def _bos_message(self) -> dict:
        """Build the begin-of-stream message with voice settings."""
        return {
            "text": " ",
            "voice_settings": {
                "stability": Config.ELEVENLABS_STABILITY,
                "similarity_boost": Config.ELEVENLABS_SIMILARITY_BOOST,
                "use_speaker_boost": Config.ELEVENLABS_USE_SPEAKER_BOOST,
                "speed": Config.ELEVENLABS_VOICE_SPEED,
            },
        }

    @classmethod
    def _circuit_open(cls) -> bool:
        return time.monotonic() < cls._circuit_open_until

    @classmethod
    def _open_circuit(cls, reason: str) -> None:
        seconds = max(0.0, Config.ELEVENLABS_CIRCUIT_BREAKER_SECONDS)
        cls._circuit_open_until = time.monotonic() + seconds
        logger.warning(
            "ElevenLabs streaming disabled for %.0fs after failure: %s",
            seconds,
            reason,
        )

    def speak(self, text: str, on_first_audio=None) -> bool:
        """Stream ``text`` to audio and play it. Returns True if audio was played.

        ``on_first_audio`` (optional) is called once, the instant the first PCM
        chunk is played — used by the caller to time first-voice latency.
        """
        if not self.available:
            return False
        if self._circuit_open():
            logger.info("ElevenLabs streaming circuit open; using fallback TTS.")
            return False
        cleaned = text.replace("[Offline Mode]", "").replace("[Error]", "").strip()
        if not cleaned:
            return False
        self.last_playback_seconds = 0.0
        try:
            played = self._run(cleaned, on_first_audio)
            if played:
                self.__class__._circuit_open_until = 0.0
            return played
        except Exception as e:
            self._open_circuit(str(e))
            logger.warning("Streaming TTS failed (%s); caller falls back to REST.", e)
            return False

    def _run(self, text: str, on_first_audio) -> bool:
        # Windows ProactorEventLoop has SSL quirks; SelectorEventLoop is reliable
        # for TLS WebSocket (same reason local_tts_service uses it for edge-tts).
        if sys.platform == "win32":
            loop = asyncio.SelectorEventLoop()
            try:
                return loop.run_until_complete(self._session(text, on_first_audio))
            finally:
                loop.close()
        return asyncio.run(self._session(text, on_first_audio))

    async def _session(self, text: str, on_first_audio) -> bool:
        import pyaudio
        import websockets

        played = False
        playback_started = 0.0
        pa = pyaudio.PyAudio()
        stream = None
        try:
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=self._rate, output=True)
            async with websockets.connect(
                self._build_uri(),
                additional_headers={"xi-api-key": self.api_key},
                proxy=True if Config.ELEVENLABS_STREAM_USE_PROXY else None,
                open_timeout=Config.ELEVENLABS_CONNECT_TIMEOUT,
                close_timeout=5,
                max_size=None,
            ) as ws:
                await ws.send(json.dumps(self._bos_message()))
                await ws.send(json.dumps({"text": text + " ", "flush": True}))
                await ws.send(json.dumps({"text": ""}))  # end-of-stream

                async for message in ws:
                    data = json.loads(message)
                    audio_b64 = data.get("audio")
                    if audio_b64:
                        pcm = base64.b64decode(audio_b64)
                        if pcm:
                            if not playback_started:
                                playback_started = time.monotonic()
                            if not played and callable(on_first_audio):
                                try:
                                    on_first_audio()
                                except Exception:
                                    pass
                            stream.write(pcm)
                            played = True
                    if data.get("isFinal"):
                        break
        finally:
            try:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
            except Exception:
                pass
            pa.terminate()
            self.last_playback_seconds = (
                max(0.0, time.monotonic() - playback_started)
                if playback_started
                else 0.0
            )
        return played
