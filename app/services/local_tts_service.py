import asyncio
import logging
import subprocess
import sys
import uuid

from app.config import Config
from app.utils.network import force_ipv4_for_hosts

logger = logging.getLogger("AICompanion.LocalTTSService")

# Edge TTS still needs Microsoft/Bing network access. Keep IPv4 forcing for the
# online fallback, but prefer Windows SAPI first on Windows for a real offline path.
force_ipv4_for_hosts("bing.com", "microsoft.com")


class LocalTTSService:
    """Local TTS fallback.

    Engine behavior:
    - auto: Windows SAPI first on Windows, then edge-tts.
    - sapi: Windows SAPI only, fully offline.
    - edge: edge-tts only, requires internet.
    """

    def __init__(self) -> None:
        self.available = False
        self._voice = Config.LOCAL_TTS_VOICE or "id-ID-GadisNeural"
        self._engine = Config.LOCAL_TTS_ENGINE or "auto"
        self._sapi_available = sys.platform == "win32"
        self._edge_available = False

        if not Config.LOCAL_TTS_ENABLED:
            logger.info("Local TTS disabled (LOCAL_TTS_ENABLED=false).")
            return

        try:
            import edge_tts  # noqa: F401
            self._edge_available = True
            logger.info("Local TTS (edge-tts) ready - voice: %s", self._voice)
        except ImportError:
            logger.warning("edge-tts not installed - online local fallback disabled.")

        if self._sapi_available:
            logger.info("Local TTS (Windows SAPI) ready - offline fallback available.")

        self.available = self._sapi_available or self._edge_available

    @staticmethod
    def _ps_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _synthesize_sapi(self, cleaned: str) -> str | None:
        """Generate WAV audio using Windows SAPI. This works without internet."""
        if not self._sapi_available:
            return None

        Config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        out_path = Config.TEMP_DIR / f"sapi_tts_{uuid.uuid4().hex[:8]}.wav"
        voice = Config.LOCAL_TTS_SAPI_VOICE
        voice_line = ""
        if voice:
            voice_line = (
                f"try {{ $s.SelectVoice({self._ps_quote(voice)}) }} "
                "catch { Write-Output 'SAPI voice not found, using default.' }\n"
            )

        script = (
            "Add-Type -AssemblyName System.Speech\n"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
            "$s.Rate = 1\n"
            "$s.Volume = 100\n"
            f"{voice_line}"
            f"$s.SetOutputToWaveFile({self._ps_quote(str(out_path))})\n"
            f"$s.Speak({self._ps_quote(cleaned)})\n"
            "$s.Dispose()\n"
        )

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=Config.LOCAL_TTS_TIMEOUT_SECONDS,
                creationflags=creationflags,
            )
        except Exception as e:
            logger.warning("Windows SAPI TTS failed: %s", e)
            return None

        if completed.returncode != 0:
            logger.warning("Windows SAPI TTS failed: %s", completed.stderr.strip()[:200])
            return None
        if out_path.exists() and out_path.stat().st_size > 0:
            logger.info("Windows SAPI TTS: %s (%s chars)", out_path.name, len(cleaned))
            return str(out_path)

        logger.warning("Windows SAPI TTS produced no audio.")
        return None

    def _synthesize_edge(self, cleaned: str) -> str | None:
        """Generate MP3 audio using edge-tts. This still requires internet."""
        if not self._edge_available:
            return None

        Config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        out_path = Config.TEMP_DIR / f"edge_tts_{uuid.uuid4().hex[:8]}.mp3"

        try:
            async def _generate() -> None:
                import edge_tts
                communicate = edge_tts.Communicate(cleaned, self._voice)
                await communicate.save(str(out_path))

            if sys.platform == "win32":
                loop = asyncio.SelectorEventLoop()
                try:
                    loop.run_until_complete(_generate())
                finally:
                    loop.close()
            else:
                asyncio.run(_generate())

            logger.info("Edge TTS: %s (%s chars, voice=%s)", out_path.name, len(cleaned), self._voice)
            return str(out_path)

        except Exception as e:
            logger.warning("Edge TTS synthesis failed: %s", e)
            return None

    def synthesize(self, text: str) -> str | None:
        """Generate audio from text using local fallbacks."""
        if not self.available:
            return None

        cleaned = text.strip()
        if not cleaned:
            return None

        engine = self._engine
        if engine not in {"auto", "sapi", "edge"}:
            engine = "auto"

        if engine in {"auto", "sapi"}:
            result = self._synthesize_sapi(cleaned)
            if result or engine == "sapi":
                return result

        if engine in {"auto", "edge"}:
            return self._synthesize_edge(cleaned)

        return None
