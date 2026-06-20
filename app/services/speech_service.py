import io
import logging
import math
import re
import struct
import time
import wave
from collections import deque
from contextlib import contextmanager
from typing import Iterator

import speech_recognition as sr
from app.config import Config

logger = logging.getLogger("AICompanion.SpeechService")

_CLIP_EVENT_TIMES: deque[float] = deque(maxlen=12)
_CLIP_WINDOW_SECONDS = 60.0
_CLIP_WARNING_THRESHOLD = 3

# Phrases Whisper hallucinates from silence/background noise (YouTube/video artifacts)
_HALLUCINATION_PHRASES: set[str] = {
    "sub indo by broth3rmax",
    "terima kasih telah menonton",
    "terima kasih sudah menonton",
    "thanks for watching",
    "please subscribe",
    "like dan subscribe",
    "jangan lupa subscribe",
    "subscribe",
    "music",
    "musik",
    "[music]",
    "[musik]",
    "(music)",
    "you",
    "i",
    # Common phrase hallucinations from ambient audio / background noise
    "sampai jumpa",
    "sampai jumpa lagi",
    "selamat tinggal",
    "dadah",
    "bye bye",
    "see you",
    "see you later",
    "good bye",
    "tolong subscribe",
    "jangan lupa like",
}

# Frasa yang sekaligus halusinasi Whisper umum DAN frasa penutup sah dari presenter
# ("terima kasih"/"makasih" menutup conversation window di InteractionLoop). Hanya
# difilter sebagai halusinasi saat kepercayaan audio TIDAK bisa diverifikasi (tidak
# ada segmen / fallback format teks). Saat Whisper memberi no_speech_prob rendah,
# frasa ini diloloskan agar presenter bisa menutup percakapan lewat suara. Lihat BUG-02.
_AMBIGUOUS_HALLUCINATION_PHRASES: frozenset[str] = frozenset({
    "terima kasih",
    "makasih",
})

# Kata pendek yang VALID sebagai respons presenter (tidak difilter meski 1 kata pendek)
_VALID_SHORT_WORDS: frozenset[str] = frozenset({
    "ya", "iya", "oke", "ok", "baik", "siap", "lanjut", "stop",
    "halo", "hai", "hey", "hi", "iya", "tenri", "hmm",
})

TENRI_WAKE_WORD_PATTERN = re.compile(
    r"^\s*(?:(?:oke|ok|halo|hai|hey|baik|permisi)\s+)?"
    r"(?:hendri|hendry|henri|henry|endri|andri|tendri|tendry|tandri|"
    r"tenry|tengri|tengry|ten gri|ten ri|ten li|tenri|tendi|tenderi|teneri|teri)\b",
    re.IGNORECASE,
)

# Catches misspellings of "Tenri" anywhere in the sentence (not just at start).
_TENRI_ANYWHERE_PATTERN = re.compile(
    r"\b(?:hendri|hendry|henri|henry|endri|andri|tendri|tendry|tandri|"
    r"tenry|tengri|tengry|ten gri|ten ri|ten li|tendi|tenderi|teneri|teri)\b",
    re.IGNORECASE,
)

# Kamus koreksi istilah domain: Whisper salah dengar → bentuk kanonik.
# Kunci: huruf kecil semua (matching case-insensitive), nilai: bentuk yang benar.
# Diurutkan panjang descending agar frasa panjang dicocokan duluan sebelum frasa pendek
# yang bisa jadi subfrasa-nya (contoh: "saweri gading" sebelum "gading").
_DOMAIN_GLOSSARY: dict[str, str] = {
    "jelas cut": "jelaskan",
    "jelas kan": "jelaskan",
    "jelas cat": "jelaskan",
    "jelas ket": "jelaskan",
    "jelas ke": "jelaskan",
    # La Galigo — naskah epos Bugis-Makassar
    "la gaigo": "La Galigo",
    "la galligo": "La Galigo",
    "la goligo": "La Galigo",
    "la galiko": "La Galigo",
    "la galibo": "La Galigo",
    "la gali go": "La Galigo",
    "lagaligo": "La Galigo",
    "ela galigo": "I La Galigo",
    # Sawerigading — tokoh utama La Galigo
    "sawe rigading": "Sawerigading",
    "saweri gading": "Sawerigading",
    "sawerigadig": "Sawerigading",
    "sawe ri gading": "Sawerigading",
    "saueri gading": "Sawerigading",
    # tursalahjalan — nama proyek
    "tursa la jalan": "tursalahjalan",
    "tursa lah jalan": "tursalahjalan",
    "tursalah jalan": "tursalahjalan",
    # Lontara — aksara Bugis-Makassar
    "lon tara": "lontara",
    "lontaraq": "lontara",
    # Kota
    "makasar": "Makassar",
    "macassar": "Makassar",
    # We Tenriabeng — tokoh dalam La Galigo
    "we tenri abeng": "We Tenriabeng",
}

# Pre-compiled patterns dengan word-boundary agar tidak mengganti substring di dalam kata lain.
# Diurutkan panjang descending: frasa panjang dicek duluan.
_DOMAIN_GLOSSARY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b" + re.escape(wrong) + r"\b", re.IGNORECASE), correct)
    for wrong, correct in sorted(
        _DOMAIN_GLOSSARY.items(),
        key=lambda kv: len(kv[0]),
        reverse=True,
    )
]


class SpeechService:
    _BACKGROUND_ENERGY_FLOOR = 300
    _BACKGROUND_AMBIENT_MULTIPLIER = 1.6

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = Config.SPEECH_ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold = Config.SPEECH_DYNAMIC_ENERGY
        self.recognizer.pause_threshold = Config.SPEECH_PAUSE_THRESHOLD
        self.recognizer.phrase_threshold = Config.SPEECH_PHRASE_THRESHOLD
        self.recognizer.non_speaking_duration = Config.SPEECH_NON_SPEAKING_DURATION
        self.microphone_available = False
        self.device_index = self._parse_device_index(Config.MIC_DEVICE_INDEX)
        self.microphone_names = []
        self.last_wait_seconds: float = 0.0
        self.last_record_seconds: float = 0.0
        self.last_transcribe_seconds: float = 0.0
        self.last_ambient_seconds: float = 0.0

        # Groq Whisper client — initialized if engine is "groq" and key is available
        self._groq_client = None
        if Config.SPEECH_STT_ENGINE == "groq" and Config.GROQ_API_KEY:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=Config.GROQ_API_KEY)
                logger.info(f"Groq Whisper STT initialized (model: {Config.GROQ_STT_MODEL}).")
            except Exception as e:
                logger.warning(f"Groq Whisper init failed, will fall back to Google STT: {e}")

        try:
            self.microphone_names = sr.Microphone.list_microphone_names()
            if not self.microphone_names:
                logger.warning("No microphone devices found. Fallback to text input.")
                return

            if self.device_index is not None:
                if 0 <= self.device_index < len(self.microphone_names):
                    logger.info(
                        f"Using microphone index {self.device_index}: "
                        f"{self.microphone_names[self.device_index]}"
                    )
                else:
                    logger.warning(
                        f"Configured microphone index {self.device_index} is out of range. "
                        "Using the system default microphone instead."
                    )
                    self.device_index = None
            else:
                logger.info("Using the system default microphone.")

            self.microphone_available = True
            engine_label = "Groq Whisper" if self._groq_client else "Google STT"
            logger.info(f"Speech recognition ready — engine: {engine_label}.")
        except Exception as e:
            logger.warning(
                f"Microphone not available or PyAudio not installed: {e}. Fallback to text input."
            )

    @classmethod
    def background_energy_threshold(cls, ambient_rms: float, configured: int) -> int:
        """Choose a usable fixed threshold without exceeding the configured ceiling."""
        recommended = max(
            cls._BACKGROUND_ENERGY_FLOOR,
            int(max(0.0, ambient_rms) * cls._BACKGROUND_AMBIENT_MULTIPLIER),
        )
        return min(max(1, int(configured)), recommended)

    @staticmethod
    @contextmanager
    def microphone_source(device_index: int | None) -> Iterator[sr.Microphone]:
        """Open a microphone without letting SpeechRecognition mask CoreAudio errors.

        SpeechRecognition 3.16.1 swallows exceptions raised by ``PyAudio.open()``
        inside ``Microphone.__enter__`` and returns an object whose stream is
        ``None``. Its ``__exit__`` then raises ``AttributeError`` while trying to
        close that missing stream, hiding the useful device/permission failure.
        Manage the opened stream directly so the original failure stays visible.
        """
        microphone = sr.Microphone(device_index=device_index)
        source = microphone.__enter__()
        stream = getattr(source, "stream", None)
        if stream is None:
            device_label = "system default" if device_index is None else str(device_index)
            raise OSError(
                "CoreAudio could not open the microphone stream "
                f"(MIC_DEVICE_INDEX={device_label}). Check macOS Microphone permission, "
                "select a valid input device, or leave MIC_DEVICE_INDEX empty."
            )

        try:
            yield source
        finally:
            try:
                stream.close()
            except Exception as exc:
                logger.debug("Microphone stream cleanup failed: %s", exc)
            finally:
                source.stream = None
                audio = getattr(source, "audio", None)
                if audio is not None:
                    try:
                        audio.terminate()
                    except Exception as exc:
                        logger.debug("PyAudio cleanup failed: %s", exc)

    def calibrate_background_energy(self, duration: float = 0.4) -> int:
        """Measure room noise once before continuous listening starts.

        BackgroundListener uses a fixed energy gate. Treat the value from `.env`
        as a ceiling so an accidentally huge value cannot make Tenri deaf.
        """
        configured = max(1, int(Config.SPEECH_ENERGY_THRESHOLD))
        if not self.microphone_available:
            return configured

        try:
            with self.microphone_source(self.device_index) as source:
                chunks = max(1, int(source.SAMPLE_RATE * duration / source.CHUNK))
                sum_squares = 0
                sample_count = 0
                peak = 0
                for _ in range(chunks):
                    data = source.stream.read(source.CHUNK)
                    for (sample,) in struct.iter_unpack("<h", data):
                        absolute = abs(sample)
                        peak = max(peak, absolute)
                        sum_squares += sample * sample
                        sample_count += 1

            ambient_rms = math.sqrt(sum_squares / sample_count) if sample_count else 0.0
            active = self.background_energy_threshold(ambient_rms, configured)
            self.recognizer.energy_threshold = active
            logger.info(
                "Microphone gate calibrated: ambient_rms=%.0f peak=%d configured=%d active=%d",
                ambient_rms,
                peak,
                configured,
                active,
            )
            if peak < 10:
                logger.warning(
                    "Microphone input is nearly silent. Check MIC_DEVICE_INDEX=%s and operating-system microphone permissions.",
                    self.device_index,
                )
            return active
        except Exception as exc:
            self.recognizer.energy_threshold = configured
            logger.warning(
                "Microphone gate calibration failed (%s); using configured threshold %d.",
                exc,
                configured,
            )
            return configured

    @staticmethod
    def audio_duration_seconds(audio: sr.AudioData) -> float:
        """Return approximate audio duration for an AudioData object."""
        sample_rate = getattr(audio, "sample_rate", 0) or 0
        sample_width = getattr(audio, "sample_width", 0) or 0
        frame_data = getattr(audio, "frame_data", b"") or b""
        if sample_rate <= 0 or sample_width <= 0:
            return 0.0
        return len(frame_data) / float(sample_rate * sample_width)

    @staticmethod
    def cap_audio_for_stt(audio: sr.AudioData, max_seconds: float | None = None) -> sr.AudioData:
        """Limit audio sent to STT so endpointing failures do not punish Whisper.

        This is a safety net, not the primary endpointing mechanism. The recorder
        should stop at SPEECH_PHRASE_TIME_LIMIT, but noisy rooms or echo can still
        produce overly long captures. For live presentation, sending a clipped
        8-second utterance is better than making the presenter wait on 22 seconds
        of mostly silence/noise.
        """
        limit = Config.SPEECH_STT_AUDIO_HARD_LIMIT if max_seconds is None else max_seconds
        if limit <= 0:
            return audio

        duration = SpeechService.audio_duration_seconds(audio)
        if duration <= limit:
            return audio

        if not hasattr(audio, "get_segment"):
            logger.warning(
                "Audio exceeds STT hard limit %.1fs but cannot be clipped; duration=%.2fs",
                limit,
                duration,
            )
            return audio

        logger.warning(
            "Audio clipped before STT: %.2fs -> %.2fs. Check mic noise/echo if this repeats.",
            duration,
            limit,
        )
        now = time.monotonic()
        _CLIP_EVENT_TIMES.append(now)
        while _CLIP_EVENT_TIMES and now - _CLIP_EVENT_TIMES[0] > _CLIP_WINDOW_SECONDS:
            _CLIP_EVENT_TIMES.popleft()
        if len(_CLIP_EVENT_TIMES) >= _CLIP_WARNING_THRESHOLD:
            logger.warning(
                "Repeated STT hard-cap clips: %s clips in the last %.0fs. "
                "Raise SPEECH_ENERGY_THRESHOLD to 700, reduce speaker volume, or use earphones.",
                len(_CLIP_EVENT_TIMES),
                _CLIP_WINDOW_SECONDS,
            )
        return audio.get_segment(0, int(limit * 1000))

    @staticmethod
    def _parse_device_index(raw_index: str):
        if not raw_index:
            return None
        try:
            return int(raw_index)
        except ValueError:
            logger.warning(
                f"Invalid MIC_DEVICE_INDEX value '{raw_index}'. Using the system default microphone."
            )
            return None

    @staticmethod
    def _apply_domain_glossary(text: str) -> str:
        """Replace domain-specific mis-transcriptions with their canonical forms."""
        result = text
        for pattern, correct in _DOMAIN_GLOSSARY_PATTERNS:
            result = pattern.sub(correct, result)
        return result

    @staticmethod
    def normalize_transcription(text: str) -> str:
        """Correct common STT mis-hearings: Tenri wake word + domain glossary."""
        # Fix misspelling at start of utterance (wake word context)
        normalized = TENRI_WAKE_WORD_PATTERN.sub("Tenri", text, count=1)
        # Remove duplicate wake words at start ("Tenri Tenri ...")
        normalized = re.sub(
            r"^(Tenri)(?:[\s,]+(?:hendri|hendry|henri|henry|endri|andri|tendri|tendry|"
            r"tandri|tenry|tengri|tengry|ten gri|ten ri|ten li|teri|tenri|tendi|tenderi|teneri)\b)+",
            r"\1",
            normalized,
            flags=re.IGNORECASE,
        )
        # Fix misspellings of Tenri anywhere in the sentence ("oke lanjut Tendi" → "... Tenri")
        normalized = _TENRI_ANYWHERE_PATTERN.sub("Tenri", normalized)
        # Koreksi istilah domain proyek (La Galigo, Sawerigading, tursalahjalan, dst.)
        normalized = SpeechService._apply_domain_glossary(normalized)
        # Clean duplicated STT/echo residue before intent classification and retrieval.
        normalized = SpeechService._remove_repetition_loops(normalized)
        return normalized

    @staticmethod
    def _remove_repetition_loops(text: str) -> str:
        """Collapse Whisper hallucination loops into the first occurrence.

        Handles two patterns:
        1. Comma-separated: "buk, buk, buk" → "buk"
        2. Space-separated phrase: "oke lanjut tenri oke lanjut tenri" → "oke lanjut tenri"

        Whisper (especially turbo) repeats phrases when audio has gema/echo,
        is too long, or has brief silence gaps within a single utterance.
        """
        # Pattern 1: comma-separated repetitions
        segments = [s.strip() for s in re.split(r',\s*', text.strip().rstrip('.!?,')) if s.strip()]
        if len(segments) >= 3:
            seen: set[str] = set()
            unique: list[str] = []
            for seg in segments:
                key = seg.lower()
                if key not in seen:
                    seen.add(key)
                    unique.append(seg)
            if len(unique) < len(segments):
                cleaned = ", ".join(unique)
                logger.info(f"Removed comma-repetition: {len(segments)} → {len(unique)} segments.")
                return cleaned

        # Pattern 2: space-separated phrase repetitions
        # e.g. "oke lanjut tenri oke lanjut tenri oke lanjut tenri" → "oke lanjut tenri"
        words = text.strip().split()
        n = len(words)
        if n >= 4:
            for phrase_len in range(2, n // 2 + 1):
                phrase_lower = [w.lower() for w in words[:phrase_len]]
                i = 0
                repeat_count = 0
                while i + phrase_len <= n:
                    if [w.lower() for w in words[i : i + phrase_len]] == phrase_lower:
                        repeat_count += 1
                        i += phrase_len
                    else:
                        break
                if repeat_count >= 2 and i == n:
                    deduped = " ".join(words[:phrase_len])
                    logger.info(f"Removed phrase-repetition: {repeat_count}× → 1×: {repr(deduped)}")
                    return deduped

        return text

    @staticmethod
    def _validate_audio_quality(
        audio: sr.AudioData,
        min_duration_seconds: float = 0.5,
    ) -> None:
        """Reject audio that is too short or too silent to contain real speech.

        Runs BEFORE any API call to Groq. This is the primary hallucination
        prevention layer — bad audio is blocked here so Whisper never sees it.

        Why duration ≥ 0.5s: SPEECH_PAUSE_THRESHOLD (default 1.1) makes the recognizer
        append trailing silence after speech, so a real utterance is well over
        0.5s. Captures shorter than 0.5s are silence bursts or noise spikes that
        somehow passed the energy gate.

        Why RMS ≥ 150: real speech in a quiet room produces RMS well above 500.
        RMS below 150 means the audio is effectively silent.
        """
        wav_bytes = audio.get_wav_data()
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            duration = wf.getnframes() / float(wf.getframerate())

        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        samples = struct.unpack(f"{len(raw) // 2}h", raw)
        # Sample every Nth element so RMS estimation stays fast even for long audio.
        step = max(1, len(samples) // 2000)
        subset = samples[::step]
        rms = math.sqrt(sum(s * s for s in subset) / len(subset)) if subset else 0.0

        logger.info(f"Audio quality: duration={duration:.2f}s  RMS={rms:.0f}")

        if duration < min_duration_seconds:
            logger.info("Pre-filter: audio too short — skipping transcription.")
            raise sr.UnknownValueError()
        if rms < 150:
            logger.info(f"Pre-filter: audio too quiet (RMS={rms:.0f}) — skipping transcription.")
            raise sr.UnknownValueError()

    def _transcribe_with_groq(
        self,
        audio: sr.AudioData,
        min_duration_seconds: float = 0.5,
    ) -> str:
        """Send captured audio to Groq Whisper for transcription.

        Uses verbose_json to obtain no_speech_prob per segment, which allows
        filtering out hallucinations produced from silence or background noise.
        Falls back to text format if verbose_json is unavailable.
        """
        # Block noise/silence BEFORE sending to API — prevents Whisper hallucinations
        # at the source, not after the fact.
        audio = self.cap_audio_for_stt(audio)
        self._validate_audio_quality(
            audio,
            min_duration_seconds=min_duration_seconds,
        )

        wav_bytes = audio.get_wav_data()
        lang = Config.stt_language_code()
        prompt = (
            "Tenri, halo tenri, oke tenri, hey tenri, hai tenri, lanjut slide, "
            "kecerdasan buatan, machine learning, deep learning, artificial intelligence, "
            "AI, neural network, data, algoritma, model, teknologi, presentasi, slide, "
            "arsip, pengetahuan, digital, "
            "Museum La Galigo, La Galigo, I La Galigo, Sawerigading, We Tenriabeng, "
            "tursalahjalan, lontara, Bugis, Makassar, Sulawesi Selatan, "
            "pelestarian budaya, warisan budaya, naskah, manuskrip"
        )

        # Try verbose_json first to get no_speech_prob for silence detection.
        # confidence_verified flips True only when Whisper returns a positive
        # speech-probability signal; ambiguous closing phrases are kept only then.
        text = ""
        confidence_verified = False
        try:
            result = self._groq_client.audio.transcriptions.create(
                model=Config.GROQ_STT_MODEL,
                file=("audio.wav", io.BytesIO(wav_bytes), "audio/wav"),
                response_format="verbose_json",
                language=lang,
                prompt=prompt,
                temperature=0.0,
            )
            # Check no_speech_prob across all segments
            segments = getattr(result, "segments", None) or []
            if not segments:
                logger.warning("Groq verbose_json returned no segments — confidence filters skipped.")
            if segments:
                probs = []
                logprobs = []
                for seg in segments:
                    p = getattr(seg, "no_speech_prob", None)
                    if p is None and isinstance(seg, dict):
                        p = seg.get("no_speech_prob")
                    if p is not None:
                        probs.append(p)

                    lp = getattr(seg, "avg_logprob", None)
                    if lp is None and isinstance(seg, dict):
                        lp = seg.get("avg_logprob")
                    if lp is not None:
                        logprobs.append(lp)

                if probs:
                    avg_no_speech = sum(probs) / len(probs)
                    logger.info(f"Whisper no_speech_prob={avg_no_speech:.3f}")
                    if avg_no_speech > 0.45:
                        logger.info("Treating as silence (no_speech_prob > 0.45).")
                        raise sr.UnknownValueError()
                    # Low no_speech_prob → genuine speech, not a silence hallucination.
                    confidence_verified = True

                if logprobs:
                    avg_logprob = sum(logprobs) / len(logprobs)
                    logger.info(f"Whisper avg_logprob={avg_logprob:.3f}")
                    if avg_logprob < -1.0:
                        logger.info(
                            f"Low-confidence transcription (avg_logprob={avg_logprob:.3f})"
                            " — treating as noise."
                        )
                        raise sr.UnknownValueError()
            text = (getattr(result, "text", None) or "").strip()
        except sr.UnknownValueError:
            raise
        except Exception as e:
            logger.debug(f"verbose_json failed ({e}), falling back to text format.")
            result2 = self._groq_client.audio.transcriptions.create(
                model=Config.GROQ_STT_MODEL,
                file=("audio.wav", io.BytesIO(wav_bytes), "audio/wav"),
                response_format="text",
                language=lang,
                prompt=prompt,
                temperature=0.0,
            )
            text = str(result2).strip()

        # Filter known hallucination phrases
        cleaned = text.lower().strip().rstrip(".!?,")
        if cleaned in _HALLUCINATION_PHRASES:
            logger.info(f"Filtered Whisper hallucination: {repr(text)}")
            raise sr.UnknownValueError()

        # "terima kasih"/"makasih" are real closing phrases. Only drop them as
        # hallucination when we could NOT verify the audio is confident speech
        # (no segments / text-format fallback). When Whisper reports low
        # no_speech_prob, let them through so the presenter can close by voice (BUG-02).
        if not confidence_verified and cleaned in _AMBIGUOUS_HALLUCINATION_PHRASES:
            logger.info(f"Filtered low-confidence ambiguous phrase: {repr(text)}")
            raise sr.UnknownValueError()

        # Filter short / repeated-syllable hallucinations from noise or echo.
        # Strip per-word punctuation before analysis so "buk, buk" is treated
        # the same as "buk buk".
        raw_words = cleaned.split()
        norm_words = [re.sub(r'[^\w]', '', w) for w in raw_words]
        norm_words = [w for w in norm_words if w]

        if norm_words:
            # Single word ≤4 chars not in valid whitelist → noise
            if (
                len(norm_words) == 1
                and len(norm_words[0]) <= 4
                and norm_words[0] not in _VALID_SHORT_WORDS
            ):
                logger.info(f"Filtered short-syllable hallucination: {repr(text)}")
                raise sr.UnknownValueError()

            # Repeated identical short syllables: "buk buk", "uit uit uit"
            unique_norm = set(norm_words)
            if len(unique_norm) == 1 and len(norm_words) >= 2:
                sole = next(iter(unique_norm))
                if len(sole) <= 5 and sole not in _VALID_SHORT_WORDS:
                    logger.info(f"Filtered repeated-syllable hallucination: {repr(text)}")
                    raise sr.UnknownValueError()

            # Garbled noise: multi-word transcription with standalone single-char words
            # (e.g. "Papa, i tu robot, suwa ciesi"). Real utterances almost never have
            # isolated single-character tokens like "i" or "u" mixed with other words.
            _VALID_SINGLE_CHARS: frozenset[str] = frozenset({'a', 'e', 'o', 'u', 'y'})
            if len(norm_words) >= 4:
                single_char_noise = [
                    w for w in norm_words
                    if len(w) == 1 and w not in _VALID_SINGLE_CHARS
                ]
                if single_char_noise:
                    logger.info(f"Filtered garbled-noise transcription: {repr(text)}")
                    raise sr.UnknownValueError()

        return self._remove_repetition_loops(text)

    def _transcribe_with_google(self, audio: sr.AudioData) -> str:
        """Transcribe captured audio using Google Speech Recognition."""
        audio = self.cap_audio_for_stt(audio)
        lang_code = "en-US" if Config.stt_language_code() == "en" else "id-ID"
        return self.recognizer.recognize_google(audio, language=lang_code)

    def listen_and_transcribe(
        self,
        timeout: float = None,
        phrase_time_limit: float = None,
    ) -> tuple[str, bool]:
        """
        Listen from the microphone and transcribe the speech.
        Returns (transcription_text, success_status).
        """
        if not self.microphone_available:
            return "", False

        timeout = Config.SPEECH_TIMEOUT if timeout is None else timeout
        phrase_time_limit = Config.SPEECH_PHRASE_TIME_LIMIT if phrase_time_limit is None else phrase_time_limit

        try:
            self.last_wait_seconds = 0.0
            self.last_record_seconds = 0.0
            self.last_transcribe_seconds = 0.0
            self.last_ambient_seconds = 0.0
            with self.microphone_source(self.device_index) as source:
                logger.info("Adjusting for ambient noise...")
                ambient_started_at = time.monotonic()
                self.recognizer.adjust_for_ambient_noise(
                    source,
                    duration=Config.SPEECH_AMBIENT_NOISE_DURATION,
                )
                self.last_ambient_seconds = round(time.monotonic() - ambient_started_at, 2)
                logger.info("Listening for speech...")
                listen_started_at = time.monotonic()
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )

            listen_seconds = time.monotonic() - listen_started_at
            audio = self.cap_audio_for_stt(audio)
            self.last_record_seconds = round(self.audio_duration_seconds(audio), 2)
            self.last_wait_seconds = round(max(0.0, listen_seconds - self.last_record_seconds), 2)
            logger.info(
                "Audio captured: wait=%.2fs record=%.2fs ambient=%.2fs, starting transcription...",
                self.last_wait_seconds,
                self.last_record_seconds,
                self.last_ambient_seconds,
            )

            transcription_started_at = time.monotonic()

            # Primary engine: Groq Whisper (more accurate for Indonesian)
            if self._groq_client:
                try:
                    transcription = self._transcribe_with_groq(audio)
                    engine_used = "Groq Whisper"
                except sr.UnknownValueError:
                    raise  # silence/noise detected by Groq — don't fall back, just report as unrecognized
                except Exception as e:
                    logger.warning(f"Groq Whisper API error ({e}), falling back to Google STT.")
                    transcription = self._transcribe_with_google(audio)
                    engine_used = "Google STT (fallback)"
            else:
                transcription = self._transcribe_with_google(audio)
                engine_used = "Google STT"

            transcription_seconds = time.monotonic() - transcription_started_at
            self.last_transcribe_seconds = round(transcription_seconds, 2)
            normalized = self.normalize_transcription(transcription)
            if normalized != transcription:
                logger.info("Wake word normalized to Tenri.")

            logger.info(
                f'[{engine_used}] Transcribed in {transcription_seconds:.2f}s: "{normalized}"'
            )
            return normalized, True

        except sr.WaitTimeoutError:
            logger.info("Listening timed out. No speech detected.")
            return "[TIMEOUT]", False
        except sr.UnknownValueError:
            logger.warning("Speech Recognition could not understand audio.")
            return "[UNKNOWN_AUDIO]", False
        except sr.RequestError as e:
            logger.error(f"Could not request results from Speech Recognition service; {e}")
            return f"[ERROR: API Offline - {e}]", False
        except Exception as e:
            logger.error(f"Critical error during recording/transcription: {e}", exc_info=True)
            return f"[ERROR: {e}]", False
