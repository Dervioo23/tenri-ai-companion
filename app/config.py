import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file. utf-8-sig handles Windows files that start with a hidden BOM.
load_dotenv(encoding="utf-8-sig")

BASE_DIR = Path(__file__).resolve().parent.parent


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).strip())
    except ValueError:
        return default

class Config:
    # API Keys
    # LLM provider: "groq" or "gemini"
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    # Optional faster model for live voice turns. Falls back to GROQ_MODEL if empty
    # or if the live model is rejected by the API.
    GROQ_LIVE_MODEL = os.getenv("GROQ_LIVE_MODEL", "").strip()

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
    ACTIVE_LLM_MODEL = GEMINI_MODEL if LLM_PROVIDER == "gemini" else GROQ_MODEL
    
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
    ELEVENLABS_ENABLED = os.getenv("ELEVENLABS_ENABLED", "true").strip().lower() == "true"
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM").strip()
    # eleven_flash_v2_5 = fastest low-latency model for live voice.
    # eleven_multilingual_v2 = higher quality but slower.
    ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5").strip()
    ELEVENLABS_OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_22050_32").strip()
    ELEVENLABS_OPTIMIZE_LATENCY = _get_int("ELEVENLABS_OPTIMIZE_LATENCY", 3)
    ELEVENLABS_VOICE_SPEED = _get_float("ELEVENLABS_VOICE_SPEED", 1.08)
    ELEVENLABS_STABILITY = _get_float("ELEVENLABS_STABILITY", 0.5)
    ELEVENLABS_SIMILARITY_BOOST = _get_float("ELEVENLABS_SIMILARITY_BOOST", 0.65)
    ELEVENLABS_USE_SPEAKER_BOOST = os.getenv("ELEVENLABS_USE_SPEAKER_BOOST", "false").strip().lower() == "true"
    # TAHAP 2 — WebSocket streaming TTS: putar PCM begitu chunk pertama tiba, bukan
    # menunggu file MP3 utuh. Butuh `websockets`. Fallback otomatis ke REST/edge-tts
    # bila gagal. Default false agar tak mengubah perilaku.
    ELEVENLABS_STREAMING = os.getenv("ELEVENLABS_STREAMING", "false").strip().lower() == "true"
    # PCM tanpa biaya decode MP3. Format: pcm_16000 / pcm_22050 / pcm_24000 / pcm_44100.
    ELEVENLABS_STREAM_OUTPUT_FORMAT = os.getenv("ELEVENLABS_STREAM_OUTPUT_FORMAT", "pcm_22050").strip()
    ELEVENLABS_CONNECT_TIMEOUT = _get_float("ELEVENLABS_CONNECT_TIMEOUT", 4.0)
    ELEVENLABS_READ_TIMEOUT = _get_float("ELEVENLABS_READ_TIMEOUT", 12.0)
    ELEVENLABS_CIRCUIT_BREAKER_SECONDS = _get_float("ELEVENLABS_CIRCUIT_BREAKER_SECONDS", 60.0)
    TTS_PREWARM_ENABLED = os.getenv("TTS_PREWARM_ENABLED", "false").strip().lower() == "true"
    
    # App General settings
    APP_LANGUAGE = os.getenv("APP_LANGUAGE", "id").strip().lower()
    # Recognized single-language ISO 639-1 hints. "bilingual" is an auto mode:
    # TTS sends no language_code (multilingual model auto-detects) and STT uses the
    # Indonesian-first default. Unknown values are treated like "bilingual".
    _SUPPORTED_LANGUAGES = frozenset({"id", "en"})
    
    # Feature Toggles
    VOICE_INPUT_ENABLED = os.getenv("VOICE_INPUT_ENABLED", "false").strip().lower() == "true"
    VOICE_OUTPUT_ENABLED = os.getenv("VOICE_OUTPUT_ENABLED", "false").strip().lower() == "true"
    VISION_ENABLED = os.getenv("VISION_ENABLED", "false").strip().lower() == "true"
    # True  = tekan Enter sebelum bicara (aman dari aktivasi palsu)
    # False = auto-listen terus; Tenri aktif ketika kata panggil terdeteksi
    PUSH_TO_TALK_ENABLED = os.getenv("PUSH_TO_TALK_ENABLED", "true").strip().lower() == "true"
    # Daftar kata panggil yang mengaktifkan Tenri di mode auto-listen
    WAKE_WORDS = [
        w.strip().lower()
        for w in os.getenv(
            "WAKE_WORDS",
            "tenri,halo tenri,hallo tenri,hai tenri,hi tenri,oke tenri,ok tenri,hey tenri,eh tenri"
        ).split(",")
        if w.strip()
    ]
    # True = pakai streaming LLM + sentence-level TTS pipeline (lebih cepat)
    # LLM_STREAMING is the new generic flag; GROQ_STREAMING remains supported for compatibility.
    LLM_STREAMING = os.getenv(
        "LLM_STREAMING",
        os.getenv("GROQ_STREAMING", "true"),
    ).strip().lower() == "true"
    GROQ_STREAMING = LLM_STREAMING
    # True = paksa max 1 kalimat + max_tokens 80 untuk demo live (potong TTS latency ~60%)
    LIVE_RESPONSE_MODE = os.getenv("LIVE_RESPONSE_MODE", "false").strip().lower() == "true"
    # True = use a compact system prompt for voice/live turns.
    LIVE_PROMPT_MODE = os.getenv("LIVE_PROMPT_MODE", "false").strip().lower() == "true"
    # True = safer defaults for live demos: stricter mic gate and shorter recordings.
    DEMO_SAFE_MODE = os.getenv("DEMO_SAFE_MODE", "true").strip().lower() == "true"
    # Local TTS (edge-tts) — fallback saat ElevenLabs tidak tersedia
    # Requires: pip install edge-tts  (tanpa model download, gratis, butuh internet)
    LOCAL_TTS_ENABLED = os.getenv("LOCAL_TTS_ENABLED", "false").strip().lower() == "true"
    LOCAL_TTS_ENGINE = os.getenv("LOCAL_TTS_ENGINE", "auto").strip().lower()
    LOCAL_TTS_TIMEOUT_SECONDS = _get_float("LOCAL_TTS_TIMEOUT_SECONDS", 8.0)
    LOCAL_TTS_SAPI_VOICE = os.getenv("LOCAL_TTS_SAPI_VOICE", "").strip()
    # Suara Indonesia: id-ID-GadisNeural (perempuan) / id-ID-ArdiNeural (laki-laki)
    LOCAL_TTS_VOICE = os.getenv("LOCAL_TTS_VOICE", "id-ID-GadisNeural").strip()
    # True = BackgroundListener aktif (continuous capture + IntentClassifier routing)
    # False = sequential listen_and_transcribe() seperti sebelumnya
    VAD_ENABLED = os.getenv("VAD_ENABLED", "true").strip().lower() == "true"
    # True = aktifkan BOW centroid classifier sebagai fallback untuk kasus AMBIENT ambigu.
    # Menangkap kalimat penjelasan pendek (< 15 kata) yang terlewat oleh threshold rule-based.
    LOCAL_INTENT_CLASSIFIER = os.getenv("LOCAL_INTENT_CLASSIFIER", "true").strip().lower() == "true"
    LLM_MAX_TOKENS = _get_int("LLM_MAX_TOKENS", 200)
    RESPONSE_MAX_SENTENCES = _get_int("RESPONSE_MAX_SENTENCES", 4)
    LIVE_RESPONSE_MAX_CHARS = _get_int("LIVE_RESPONSE_MAX_CHARS", 260)
    
    # Speech settings
    MIC_DEVICE_INDEX = os.getenv("MIC_DEVICE_INDEX", "").strip()
    # 800 is safer for live demos with speaker output in the same room.
    # Lower values make Tenri more likely to hear room noise or her own TTS.
    _SAFE_SPEECH_ENERGY_THRESHOLD = 700 if DEMO_SAFE_MODE else 650
    _SAFE_SPEECH_PHRASE_TIME_LIMIT = 6.0 if DEMO_SAFE_MODE else 8.0
    _SAFE_STT_AUDIO_HARD_LIMIT = 6.0 if DEMO_SAFE_MODE else 8.0
    SPEECH_ENERGY_THRESHOLD = _get_int("SPEECH_ENERGY_THRESHOLD", _SAFE_SPEECH_ENERGY_THRESHOLD)
    SPEECH_DYNAMIC_ENERGY = os.getenv("SPEECH_DYNAMIC_ENERGY", "true").strip().lower() == "true"
    # STT engine: "groq" uses Groq Whisper (more accurate), "google" uses Google Speech Recognition
    SPEECH_STT_ENGINE = os.getenv("SPEECH_STT_ENGINE", "groq").strip().lower()
    GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo").strip()
    # After Tenri answers directly, user can follow up for this many seconds without wake word
    CONVERSATION_WINDOW = _get_float("CONVERSATION_WINDOW", 30.0)
    SPEECH_PAUSE_THRESHOLD = _get_float("SPEECH_PAUSE_THRESHOLD", 1.1)
    SPEECH_PHRASE_THRESHOLD = _get_float("SPEECH_PHRASE_THRESHOLD", 0.45)
    SPEECH_NON_SPEAKING_DURATION = _get_float("SPEECH_NON_SPEAKING_DURATION", 0.5)
    SPEECH_TIMEOUT = _get_float("SPEECH_TIMEOUT", _get_float("SPEECH_TIMEOUT_SECONDS", 7.0))
    SPEECH_PHRASE_TIME_LIMIT = _get_float("SPEECH_PHRASE_TIME_LIMIT", _SAFE_SPEECH_PHRASE_TIME_LIMIT)
    SPEECH_STT_AUDIO_HARD_LIMIT = _get_float("SPEECH_STT_AUDIO_HARD_LIMIT", _SAFE_STT_AUDIO_HARD_LIMIT)
    SPEECH_AMBIENT_NOISE_DURATION = _get_float("SPEECH_AMBIENT_NOISE_DURATION", 0.8)
    AUDIO_PLAYBACK_TIMEOUT = _get_float("AUDIO_PLAYBACK_TIMEOUT", 60.0)

    # Silero VAD (TAHAP 1) — neural endpointing menggantikan gerbang energi.
    # True = pakai VadListener (capture PyAudio + Silero ONNX). Butuh onnxruntime
    # dan model di SILERO_VAD_MODEL_PATH. Jika gagal, otomatis fallback ke
    # BackgroundListener berbasis energi. Default false agar tak mengubah perilaku.
    SILERO_VAD_ENABLED = os.getenv("SILERO_VAD_ENABLED", "false").strip().lower() == "true"
    # Probabilitas suara untuk membuka (start) dan menutup (end) ucapan — histeresis.
    SILERO_VAD_START_PROB = _get_float("SILERO_VAD_START_PROB", 0.5)
    SILERO_VAD_END_PROB = _get_float("SILERO_VAD_END_PROB", 0.35)
    # Hening berturut sebelum ucapan dianggap selesai (pengganti pause_threshold 1.1s).
    SILERO_VAD_HANGOVER_MS = _get_int("SILERO_VAD_HANGOVER_MS", 500)
    # Ucapan lebih pendek dari ini dibuang sebagai blip/noise.
    SILERO_VAD_MIN_SPEECH_MS = _get_int("SILERO_VAD_MIN_SPEECH_MS", 250)
    # Audio sebelum onset yang ikut disertakan agar awal kata tak terpotong.
    SILERO_VAD_PREROLL_MS = _get_int("SILERO_VAD_PREROLL_MS", 200)
    # Waktu maksimum menunggu frame pertama. Jika stream terbuka tetapi tidak
    # mengirim audio, listener dianggap gagal dan kembali ke BackgroundListener.
    SILERO_VAD_STARTUP_TIMEOUT = _get_float("SILERO_VAD_STARTUP_TIMEOUT", 1.5)
    # Diagnostik: cetak heartbeat (~3s) berisi max prob & amplitudo mic ke log.
    # Aktifkan sementara untuk memastikan VAD menerima audio & menyeberang ambang.
    SILERO_VAD_DEBUG = os.getenv("SILERO_VAD_DEBUG", "false").strip().lower() == "true"

    # Paths
    PROMPTS_DIR = BASE_DIR / "app" / "prompts"
    DATA_DIR = BASE_DIR / "app" / "data"
    LOGS_DIR = DATA_DIR / "logs"
    
    ASSETS_DIR = BASE_DIR / "assets"
    AUDIO_DIR = ASSETS_DIR / "audio"
    RESPONSES_DIR = AUDIO_DIR / "responses"
    TEMP_DIR = AUDIO_DIR / "temp"
    TTS_CACHE_DIR = AUDIO_DIR / "tts_cache"
    SNAPSHOTS_DIR = ASSETS_DIR / "images" / "camera_snapshots"
    MODELS_DIR = ASSETS_DIR / "models"
    SILERO_VAD_MODEL_PATH = MODELS_DIR / "silero_vad.onnx"

    @classmethod
    def tts_language_code(cls) -> str | None:
        """ISO 639-1 code to send to ElevenLabs, or None to let the multilingual
        model auto-detect. 'bilingual'/unknown -> None so the request is not
        rejected with HTTP 400 and all audio silenced (BUG-07)."""
        return cls.APP_LANGUAGE if cls.APP_LANGUAGE in cls._SUPPORTED_LANGUAGES else None

    @classmethod
    def stt_language_code(cls) -> str:
        """Primary language hint for STT. Whisper/Google accept one language; an
        Indonesian-first app maps 'bilingual'/unknown to 'id' instead of 'en'."""
        return "en" if cls.APP_LANGUAGE == "en" else "id"

    @classmethod
    def validate_critical_configs(cls):
        """Validate crucial configurations and raise descriptive warnings or errors."""
        warnings = []
        errors = []

        if cls.LLM_PROVIDER not in {"groq", "gemini"}:
            errors.append("LLM_PROVIDER must be either 'groq' or 'gemini'.")

        if cls.APP_LANGUAGE not in (cls._SUPPORTED_LANGUAGES | {"bilingual"}):
            warnings.append(
                f"APP_LANGUAGE='{cls.APP_LANGUAGE}' tidak dikenal. Gunakan 'id', 'en', "
                "atau 'bilingual'. Tenri memakai mode auto (TTS auto-detect, STT Indonesia)."
            )

        if cls.LLM_PROVIDER == "groq" and not cls.GROQ_API_KEY:
            warnings.append("GROQ_API_KEY is missing. Tenri will run in offline/mock text mode until you add it.")

        if cls.LLM_PROVIDER == "gemini" and not cls.GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY is missing. Tenri will run in offline/mock text mode until you add it.")

        if cls.SPEECH_STT_ENGINE == "groq" and not cls.GROQ_API_KEY:
            warnings.append("GROQ_API_KEY is missing for Groq Whisper STT. Switch SPEECH_STT_ENGINE=google or add a Groq key.")
            
        if cls.VOICE_OUTPUT_ENABLED and cls.ELEVENLABS_ENABLED and not cls.ELEVENLABS_API_KEY:
            warnings.append(
                "ELEVENLABS_API_KEY is missing. ElevenLabs cloud TTS will be skipped; "
                "local TTS fallback can still be used if LOCAL_TTS_ENABLED=true."
            )

        if cls.VOICE_OUTPUT_ENABLED and not cls.ELEVENLABS_ENABLED and not cls.LOCAL_TTS_ENABLED:
            warnings.append(
                "VOICE_OUTPUT_ENABLED=true but ElevenLabs and local TTS are both disabled. "
                "Tenri will show text without voice."
            )
            
        return errors, warnings
