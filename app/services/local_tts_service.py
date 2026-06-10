import asyncio
import socket
import sys
import uuid
import logging
from app.config import Config

logger = logging.getLogger("AICompanion.LocalTTSService")

# Microsoft's Edge TTS endpoint (speech.platform.bing.com) juga terkena masalah NAT64
# yang sama dengan ElevenLabs: ISP mengembalikan alamat IPv6 via NAT64, tapi Windows
# gagal menyelesaikan koneksi TLS. Paksa IPv4 untuk host Bing/Microsoft.
_orig_getaddrinfo_edge = socket.getaddrinfo

def _edge_tts_force_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    if host and ("bing.com" in str(host) or "microsoft.com" in str(host)):
        try:
            results = _orig_getaddrinfo_edge(host, port, socket.AF_INET, type, proto, flags)
            if results:
                return results
        except Exception:
            pass
    return _orig_getaddrinfo_edge(host, port, family, type, proto, flags)

socket.getaddrinfo = _edge_tts_force_ipv4


class LocalTTSService:
    """Fallback TTS menggunakan edge-tts (Microsoft Azure Neural TTS, gratis, tanpa API key).

    Diaktifkan saat LOCAL_TTS_ENABLED=true. Requires:
        pip install edge-tts

    Suara Indonesia yang tersedia:
        id-ID-GadisNeural  (perempuan, default)
        id-ID-ArdiNeural   (laki-laki)

    Dikonfigurasi via LOCAL_TTS_VOICE di .env. Fallback ke ElevenLabs hanya jika
    ElevenLabs tidak menghasilkan audio (error, rate limit, atau client=None).
    Jika keduanya gagal, Tenri diam — tidak crash.
    """

    def __init__(self) -> None:
        self.available = False
        self._voice = Config.LOCAL_TTS_VOICE or "id-ID-GadisNeural"

        if not Config.LOCAL_TTS_ENABLED:
            logger.info("Local TTS disabled (LOCAL_TTS_ENABLED=false).")
            return

        try:
            import edge_tts  # noqa: F401 — cukup pastikan library terpasang
            self.available = True
            logger.info(f"Local TTS (edge-tts) ready — voice: {self._voice}")
        except ImportError:
            logger.warning(
                "edge-tts tidak terinstall — local fallback nonaktif. "
                "Install dengan: pip install edge-tts"
            )

    def synthesize(self, text: str) -> str | None:
        """Generate audio dari teks menggunakan edge-tts. Return path MP3 atau None."""
        if not self.available:
            return None

        cleaned = text.strip()
        if not cleaned:
            return None

        Config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        out_path = Config.TEMP_DIR / f"local_tts_{uuid.uuid4().hex[:8]}.mp3"

        try:
            async def _generate() -> None:
                import edge_tts
                communicate = edge_tts.Communicate(cleaned, self._voice)
                await communicate.save(str(out_path))

            # Windows ProactorEventLoop (default asyncio) gagal pada SSL tertentu
            # dengan WinError 64. SelectorEventLoop kompatibel dengan semua host TTS.
            if sys.platform == "win32":
                loop = asyncio.SelectorEventLoop()
                try:
                    loop.run_until_complete(_generate())
                finally:
                    loop.close()
            else:
                asyncio.run(_generate())

            logger.info(f"Edge TTS: {out_path.name} ({len(cleaned)} chars, voice={self._voice})")
            return str(out_path)

        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}")
            return None
