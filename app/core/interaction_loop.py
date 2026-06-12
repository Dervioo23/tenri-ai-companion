import concurrent.futures
import random
import re
import threading
import time
import sys
import logging
from app.state import state_manager, AppState
from app.config import Config
from app.core.prompt_builder import PromptBuilder
from app.core.session_memory import SessionMemory
from app.services.groq_service import GroqService
from app.services.elevenlabs_service import ElevenLabsService
from app.services.audio_player import AudioPlayer
from app.services.speech_service import SpeechService
from app.services.vision_service import VisionService
from app.utils.terminal_ui import TerminalUI
from app.utils.file_manager import FileManager
from app.services.document_loader import DocumentLoader
from app.services.retrieval import RetrievalService
from app.services.presentation_tracker import PresentationTracker
from app.services.interruption_policy import InterruptionPolicy
from app.services.trigger_service import TriggerService
from app.services.session_logger import SessionLogger
from app.utils.text_utils import (
    format_tenri_voice_response,
    trim_to_character_budget,
    trim_response,
)
from app.services.intent_classifier import IntentClassifier, Intent
from app.services.background_listener import BackgroundListener
from app.services.local_tts_service import LocalTTSService
from app.services.streaming_tts import StreamingTTS
from app.services.query_rewriter import QueryRewriter
from app.services.answer_verifier import AnswerVerifier

logger = logging.getLogger("AICompanion.InteractionLoop")

_SLIDE_EXPLANATION_DEPRIORITIZED_SOURCES: frozenset[str] = frozenset({
    "tenri-concept",
    "tursalahjalan-world",
    "tenri-dialogue-examples",
})

_QUESTION_SUBSTRINGS: frozenset[str] = frozenset({
    "apa", "kenapa", "mengapa", "bagaimana", "gimana",
    "siapa", "dimana", "kapan", "berapa", "jelaskan",
    "ceritakan", "ketahui", "komentari", "komentar",
    "ulas", "bahas", "tanggapi", "respon", "respons",
})

# Word-boundary matcher for the question words above. Plain substring matching is
# wrong: "apa" appears inside "lapangan"/"harapan"/"siapapun", which would falsely
# flag ambient narration as a question (BUG-03). \b requires whole-token matches.
_QUESTION_WORD_RE = re.compile(
    r"\b(?:"
    + "|".join(sorted((re.escape(w) for w in _QUESTION_SUBSTRINGS), key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def _has_question_word(text: str) -> bool:
    """True when text contains a '?' or a standalone Indonesian question word."""
    return "?" in text or bool(_QUESTION_WORD_RE.search(text))


# Perintah untuk keluar dari loop interaksi; berlaku di semua mode input (A/B/C).
_EXIT_COMMANDS: frozenset[str] = frozenset({"exit", "quit", "keluar"})

# Kata penutup yang menutup conversation window setelah Tenri menjawab.
# Presenter mengucapkan ini untuk memberi tahu Tenri bahwa dialog sudah selesai.
_CLOSING_PHRASES: frozenset[str] = frozenset({
    "terima kasih", "makasih", "oke makasih", "oke terima kasih",
    "ya makasih", "ya terima kasih", "baik terima kasih", "baik makasih",
    "sudah", "sudah cukup", "cukup", "oke cukup", "ya sudah", "ya cukup",
    "thanks", "thank you", "oke thanks", "oke thank you",
    "mantap terima kasih", "oke mantap", "sip terima kasih",
    "sama sama", "sama-sama", "iya sama sama", "ya sama sama",
    "oke sama sama", "baik sama sama",
})

# Frasa pendek yang hanya berupa acknowledgment — tidak perlu respons LLM.
# Berlaku saat dalam conversation window dan bukan panggilan wake word langsung.
_ACKNOWLEDGMENT_PHRASES: frozenset[str] = frozenset({
    "ya", "oke", "ok", "iya", "baik", "mengerti", "paham",
    "siap", "sip", "noted", "got it", "i see",
    "ya oke", "ya ok", "oke baik", "ok baik",
    "ya baik", "iya baik", "iya oke", "iya ok",
    "ya ya", "oke oke", "iya iya",
    "oh oke", "oh ok", "oh iya", "oh ya",
    "hmm", "hm", "mmm",
    "hmm oke", "hmm ok", "hmm ya",
    # Standalone greetings in conversation window — not a meaningful request
    "hai", "halo", "hey", "hi", "hello",
    "hai tenri", "halo tenri", "hey tenri", "hi tenri",
    # Echo sapaan Tenri "Ya, saya di sini."
    "ya saya di sini", "ya saya disini",
    "iya saya di sini", "iya saya disini",
    "saya di sini", "saya disini",
})

# Respons perpisahan Tenri saat presenter menutup dialog.
_FAREWELL_RESPONSES: list[str] = [
    "Sama-sama.",
    "Senang bisa membantu.",
    "Tentu, sama-sama.",
    "Dengan senang hati.",
    "Baik, saya di sini jika dibutuhkan lagi.",
]

_WAKE_ACK_FALLBACK = "Iye, saya di sini."
_WAKE_ACK_RESPONSES: tuple[str, ...] = (
    "Saya dengar.",
    "Iye, saya di sini.",
    "Ada, saya dengar.",
)

_WAKE_ACK_BLOCKLIST_RE = re.compile(
    r"\b(?:"
    r"mari\s+kita|"
    r"slide|"
    r"presenter|"
    r"siap\s+membantu|"
    r"pengenalan\s+teknologi|"
    r"kecerdasan\s+buatan|"
    r"artificial\s+intelligence|"
    r"menjelaskan?|"
    r"membahas|"
    r"berjudul|"
    r"materi|"
    r"mulai\s+dengan"
    r")\b",
    re.IGNORECASE,
)

_SLIDE_EXPLANATION_RE = re.compile(
    r"\b(?:jelaskan|terangkan|paparkan|uraikan|bahas|ulas|ceritakan)\b"
    r".{0,40}\bslide\b|\bslide\b.{0,40}"
    r"\b(?:jelaskan|terangkan|paparkan|uraikan|bahas|ulas|ceritakan)\b",
    re.IGNORECASE,
)

_DETAIL_REQUEST_RE = re.compile(
    r"\b(?:detail|lengkap|panjang|mendalam|lebih\s+jelas|lebih\s+rinci|"
    r"secara\s+rinci|uraian\s+panjang)\b",
    re.IGNORECASE,
)

# Frasa statis yang di-generate TTS saat startup agar langsung tersedia dari cache.
_STATIC_TTS_PHRASES: tuple[str, ...] = (
    "Ya, saya di sini.",
    "Iye, saya di sini.",
    "Saya dengar.",
    "Baik, kita lanjut ke slide berikutnya.",
    *_FAREWELL_RESPONSES,
)

# Penanda bahwa presenter sedang berbicara ke audiens, bukan ke Tenri.
# Jika terdeteksi dalam conversation window, Tenri diam.
_AUDIENCE_MARKERS: frozenset[str] = frozenset({
    "teman-teman", "hadirin", "kalian", "semuanya", "semua nya",
    "kawan-kawan", "peserta", "bapak ibu", "ibu bapak",
    "guys", "everyone", "rekan-rekan",
    "selamat pagi", "selamat siang", "selamat sore", "selamat malam",
    "audiens", "penonton", "pemirsa",
    "selamat menikmati", "selamat menyimak",
    "silakan menikmati", "silahkan menikmati",
    "silakan menyimak", "silahkan menyimak",
})

class InteractionLoop:
    def __init__(self, jarvis_ui=None):
        self._config_errors, self._config_warnings = Config.validate_critical_configs()
        if self._config_errors:
            joined = "; ".join(self._config_errors)
            raise ValueError(f"Invalid Tenri configuration: {joined}")

        # UI & Files foundation
        FileManager.ensure_directories()
        FileManager.cleanup_temp_files()

        # Services Initialization
        self.groq_service = GroqService()
        self.llm_service = self._build_llm_service()
        self.prompt_builder = PromptBuilder()
        self.memory = SessionMemory()
        self.elevenlabs_service = ElevenLabsService()
        self.audio_player = AudioPlayer()
        self.speech_service = SpeechService()
        self.vision_service = VisionService()

        # Eager-load knowledge base for retrieval
        loader = DocumentLoader()
        chunks = loader.load_all_documents()
        self.retrieval = RetrievalService(chunks)
        if chunks:
            logger.info(f"Knowledge base loaded: {len(chunks)} chunks.")

        # Presentation slide tracker
        self.tracker = PresentationTracker()

        # Interruption policy (cooldown 90s, max 8 per session)
        self.policy = InterruptionPolicy()
        self._prev_face_count: int = 0
        self._vision_initialized: bool = False

        # Ambient keyword triggers
        self.trigger_service = TriggerService()

        # Session log (one JSONL file per run)
        self.session_logger = SessionLogger()

        # Intent classifier — routing presenter utterances ke 5 kategori
        self.intent_classifier = IntentClassifier()

        # Local TTS fallback (XTTS v2) — dipakai saat ElevenLabs tidak tersedia
        self.local_tts_service = LocalTTSService()

        # Streaming TTS (WebSocket) — opt-in; plays PCM as it arrives (TAHAP 2).
        self.streaming_tts = StreamingTTS()

        # Query rewriter — converts vague/context-dependent user inputs into
        # focused BM25 search queries using slide context + conversation history.
        self.query_rewriter = QueryRewriter()

        # Answer verifier — grounding check: ensures Tenri's response is supported
        # by retrieved context chunks via BOW cosine similarity.
        self.answer_verifier = AnswerVerifier()

        # Background listener — continuous capture + mute gate saat TTS.
        # Prefer Silero VAD endpointing when enabled & usable; else energy-gated.
        self.bg_listener = self._build_listener()
        if Config.VAD_ENABLED and not Config.PUSH_TO_TALK_ENABLED and Config.VOICE_INPUT_ENABLED:
            self._start_background_listener()

        # Optional JARVIS visual display
        self.jarvis_ui = jarvis_ui

        # Conversation-mode window: after Tenri answers directly, user can follow up
        # without repeating the wake word for CONVERSATION_WINDOW seconds.
        self._conversation_until: float = 0.0

        # Quiet mode: set True when presenter says closing phrase (e.g. "terima kasih").
        # Blocks even questions until presenter explicitly calls "Tenri" again.
        self._quiet_mode: bool = False

        # Timing diagnostics — set by _stream_and_speak after each response
        self._last_llm_seconds: float = 0.0
        self._last_first_voice_seconds: float = 0.0
        self._last_tts_seconds: float = 0.0
        self._last_audio_playback_seconds: float = 0.0
        self._last_wait_seconds: float = 0.0
        self._last_record_seconds: float = 0.0
        self._last_stt_seconds: float = 0.0
        self._last_retrieval_seconds: float = 0.0

        # Last spoken response text — used to strip mic echo in next transcription
        self._last_tenri_response: str = ""

        # Subscribe state changes to terminal updates
        state_manager.register_listener(self._on_state_change)

        # Start background services
        if Config.VISION_ENABLED:
            self.vision_service.start()

        # Pre-warm TTS cache for static phrases in background
        self._prewarm_tts_cache()

        self.running = False

    def _build_llm_service(self):
        """Create the configured LLM provider while keeping Groq available for STT."""
        from app.services.llm_factory import build_llm_service
        return build_llm_service(self.groq_service)

    def _build_listener(self):
        """Pick the capture backend: Silero VAD when enabled & usable, else energy-gated.

        Both expose the same interface, so the rest of the loop is agnostic. Any
        failure to load the VAD model falls back to BackgroundListener.
        """
        if Config.SILERO_VAD_ENABLED:
            try:
                from app.services.vad_listener import VadListener
                listener = VadListener(self.speech_service)
                if listener.usable:
                    logger.info("Capture backend: Silero VAD (VadListener).")
                    return listener
                logger.warning("Silero VAD not usable; falling back to BackgroundListener.")
            except Exception as e:
                logger.warning("Silero VAD init failed (%s); falling back to BackgroundListener.", e)
        return BackgroundListener(self.speech_service)

    def _start_background_listener(self) -> bool:
        """Start continuous capture and recover if the preferred backend is unhealthy."""
        if self.bg_listener.start():
            return True

        if isinstance(self.bg_listener, BackgroundListener):
            return False

        logger.warning(
            "Preferred capture backend failed at startup; switching to BackgroundListener."
        )
        self.bg_listener.stop()
        self.bg_listener = BackgroundListener(self.speech_service)
        return self.bg_listener.start()

    def _llm(self):
        """Return active LLM service; fallback keeps older tests and scripts working."""
        return getattr(self, "llm_service", self.groq_service)

    def _on_state_change(self, old_state, new_state, error_msg):
        """Callback invoked when state manager changes state."""
        TerminalUI.update_state_display(new_state, error_msg)
        if self.jarvis_ui:
            self.jarvis_ui.update_state(new_state.name)

    def _slide_for_ids(self, slide_ids: list) -> dict | None:
        """Return the first slide whose id appears in slide_ids, or None."""
        if not slide_ids or not self.tracker.is_active():
            return None
        for s in self.tracker.all_slides():
            if s.get("id") in slide_ids:
                return s
        return None

    # Minimum BOW cosine similarity to flag whole-input as Tenri's own echo.
    _ECHO_SIM_THRESHOLD: float = 0.5
    # Minimum fraction of input words that must appear in the last response.
    _ECHO_OVERLAP_MIN: float = 0.65
    # Minimum response token count before echo detection triggers (avoids false
    # positives from very short responses like "Iya" or "Baik").
    _ECHO_MIN_RESPONSE_TOKENS: int = 3

    @staticmethod
    def _echo_tokens(text: str) -> list[str]:
        text = text.lower()
        text = re.sub(r"\biye\b", "iya", text)
        text = re.sub(r"\bya\b", "iya", text)
        return [t for t in re.sub(r"[^\w\s]", " ", text).split() if t]

    def _strip_echo(self, user_input: str) -> str:
        """Detect and remove Tenri's own TTS echo from mic-captured transcription.

        Handles two echo patterns:

        Case 1 — Whole-input echo: the entire transcription is the echo
          (e.g. last sentence reverb captured as standalone phrase)
          → discard entirely.

        Case 2 — Prefix echo concatenated with real speech
          (e.g. mic captured echo then user continued speaking in same breath)
          → strip the echo prefix, keep the rest.

        Both cases use token-level overlap so minor STT variants ("di sini" vs
        "disini") are still matched correctly.
        """
        if not self._last_tenri_response or not user_input:
            return user_input

        from app.services.answer_verifier import _cosine_similarity, _tokenize

        raw_input_tokens = self._echo_tokens(user_input)
        raw_response_tokens = self._echo_tokens(self._last_tenri_response)

        # Short response echo, e.g. Tenri says "Iye, ada apa?" and the mic
        # captures "Iya, ada apa? Jelaskan slide pertama ini".
        if raw_input_tokens and raw_response_tokens:
            R_raw = len(raw_response_tokens)
            if len(raw_input_tokens) == R_raw:
                raw_overlap = sum(
                    1 for a, b in zip(raw_input_tokens, raw_response_tokens) if a == b
                ) / R_raw
                if raw_overlap >= 0.75:
                    logger.warning("Short self-echo discarded: '%s...'", user_input[:50])
                    return ""

            if len(raw_input_tokens) > R_raw:
                raw_prefix = raw_input_tokens[:R_raw]
                raw_overlap = sum(
                    1 for a, b in zip(raw_prefix, raw_response_tokens) if a == b
                ) / R_raw
                if raw_overlap >= 0.75:
                    remaining = " ".join(raw_input_tokens[R_raw:])
                    logger.info("Short echo prefix stripped: remaining='%s...'", remaining[:50])
                    return remaining

        input_tokens = _tokenize(user_input)
        response_tokens = _tokenize(self._last_tenri_response)

        if not input_tokens or len(response_tokens) < self._ECHO_MIN_RESPONSE_TOKENS:
            return user_input

        response_token_set = set(response_tokens)
        R = len(response_tokens)

        # Case 1: whole input is the echo
        sim = _cosine_similarity(input_tokens, response_tokens)
        overlap_ratio = sum(1 for t in input_tokens if t in response_token_set) / len(input_tokens)

        if sim >= self._ECHO_SIM_THRESHOLD and overlap_ratio >= self._ECHO_OVERLAP_MIN:
            logger.warning(
                "Self-echo discarded (sim=%.2f, overlap=%.0f%%): '%s...'",
                sim, overlap_ratio * 100, user_input[:50],
            )
            return ""

        # Case 2: echo prefix concatenated with user's real speech
        # Check if the first R tokens of input overlap heavily with the response.
        if len(input_tokens) > R:
            prefix_tokens = input_tokens[:R]
            prefix_overlap = sum(1 for t in prefix_tokens if t in response_token_set) / R
            if prefix_overlap >= self._ECHO_OVERLAP_MIN:
                remaining = " ".join(input_tokens[R:])
                logger.info(
                    "Echo prefix stripped (overlap=%.0f%%): remaining='%s...'",
                    prefix_overlap * 100, remaining[:50],
                )
                return remaining

        return user_input

    def _handle_auto_slide_trigger(self, user_input: str) -> dict | None:
        """Auto-advance slide from trigger keywords and show terminal feedback."""
        if not self.tracker.is_active():
            return None

        auto_slide = self.tracker.detect_trigger(user_input)
        if auto_slide:
            current, total = self.tracker.position()
            TerminalUI.print_slide_change(auto_slide, current, total)
            if self.jarvis_ui:
                self.jarvis_ui.update_slide(self.tracker.format_context(auto_slide))
        return auto_slide

    @staticmethod
    def _input_requests_spoken_response(user_input: str) -> bool:
        """Return True when a slide command also asks Tenri to speak."""
        return _has_question_word(user_input)

    @staticmethod
    def _is_exit_command(user_input: str) -> bool:
        """True when the user asked to quit, in any input mode (A/B/C)."""
        return user_input.strip().lower() in _EXIT_COMMANDS

    @staticmethod
    def _is_slide_explanation_request(user_input: str) -> bool:
        """Detect direct requests like "jelaskan slide ini"."""
        return bool(_SLIDE_EXPLANATION_RE.search(user_input or ""))

    @staticmethod
    def _input_requests_detail(user_input: str) -> bool:
        """Return True when the presenter explicitly asks for a longer answer."""
        return bool(_DETAIL_REQUEST_RE.search(user_input or ""))

    @staticmethod
    def _slide_explanation_query(slide: dict | None, fallback: str) -> str:
        """Build retrieval query from slide substance, not the generic command."""
        if not slide:
            return fallback
        parts = [
            slide.get("subtitle", ""),
            slide.get("title", ""),
            " ".join(slide.get("topics", [])),
            slide.get("presenter_notes", ""),
            slide.get("tenri_role", ""),
        ]
        query = " ".join(p for p in parts if p).strip()
        return query or fallback

    @staticmethod
    def _filter_slide_explanation_chunks(chunks: list) -> list:
        """Prefer slide/topic sources over persona or project-meta documents.

        Persona docs are useful for Tenri's voice, but they pollute "jelaskan
        slide ini" answers when the active slide already has relevant material.
        Keep them only as a fallback if no better chunk was retrieved.
        """
        if not chunks:
            return []

        preferred = [
            chunk for chunk in chunks
            if str(chunk.get("source_id", "")).lower()
            not in _SLIDE_EXPLANATION_DEPRIORITIZED_SOURCES
        ]
        return preferred or chunks

    @staticmethod
    def _live_char_budget(user_input: str) -> int:
        """Normal live turns stay short; explicit detail requests can be longer."""
        if InteractionLoop._input_requests_detail(user_input):
            return 0
        return Config.LIVE_RESPONSE_MAX_CHARS

    def _handle_slide_command(self, user_input: str) -> bool:
        """Handle slide navigation/status commands.

        Returns True when the command was fully handled and the main loop should
        continue. Pure navigation stays silent; navigation plus a direct request
        such as "jelaskan" or "komentari" falls through to the LLM pipeline.
        """
        if not self.tracker.is_active():
            return False

        cmd = self.tracker.detect_command(user_input)
        if cmd == "status":
            slide = self.tracker.current_slide()
            current, total = self.tracker.position()
            TerminalUI.print_slide_status(slide, current, total)
            state_manager.set_state(AppState.IDLE)
            return True

        if cmd == "list":
            current, total = self.tracker.position()
            TerminalUI.print_slide_list(self.tracker.all_slides(), current)
            state_manager.set_state(AppState.IDLE)
            return True

        if not cmd:
            return False

        slide = self.tracker.handle_command(cmd)
        current, total = self.tracker.position()
        TerminalUI.print_slide_change(slide, current, total)
        if self.jarvis_ui and slide:
            self.jarvis_ui.update_slide(self.tracker.format_context(slide))

        if self._input_requests_spoken_response(user_input):
            return False

        logger.info(
            "Slide navigation command handled quietly; no proactive Tenri response."
        )
        state_manager.set_state(AppState.IDLE)
        return True

    @staticmethod
    def _sanitize_wake_ack_response(text: str) -> str:
        """Keep wake-word-only responses short and away from slide content."""
        cleaned = trim_response(text or "", max_sentences=1)
        cleaned = format_tenri_voice_response(cleaned, max_sentences=1).strip()

        if not cleaned:
            return _WAKE_ACK_FALLBACK

        if _WAKE_ACK_BLOCKLIST_RE.search(cleaned):
            logger.info("Wake acknowledgement rejected as too content-like: '%s'", cleaned)
            return _WAKE_ACK_FALLBACK

        if len(cleaned) > 80:
            logger.info("Wake acknowledgement rejected as too long: '%s'", cleaned)
            return _WAKE_ACK_FALLBACK

        return cleaned

    def _build_interruption_context(self, topic: str, slide: dict | None) -> tuple[str, bool]:
        """Retrieve knowledge base context for a proactive interruption."""
        parts = [topic] if topic else []
        if slide:
            parts.append(slide.get("title", ""))
            parts.extend(slide.get("topics", []))

        query = " ".join(p for p in parts if p).strip()
        if not query:
            return "", True

        chunks = self.retrieval.search(query)
        if chunks and not self.retrieval.has_strong_match(chunks):
            logger.info("Interruption retrieval discarded: weak query/source overlap.")
            chunks = []
        context_str = self.retrieval.format_context(chunks) if chunks else ""
        if chunks:
            sources_used = list({c.get("source_id") for c in chunks})
            logger.info(f"Interruption sources used: {sources_used}")
        return context_str, not bool(chunks)

    def _do_interruption(
        self,
        mode: str,
        slide: dict | None,
        prompt: str | None = None,
        trigger_id: str | None = None,
        context_str: str = "",
    ) -> None:
        """Generate and deliver a proactive Tenri interjection."""
        prompt = prompt or self.policy.build_prompt(mode, slide)
        slide_str = self.tracker.format_context(slide) if slide else ""
        narrative_str = self.tracker.format_narrative_context()
        try:
            interruption_started_at = time.monotonic()
            state_manager.set_state(AppState.THINKING)
            with TerminalUI.get_spinner("Tenri sedang nimbrung..."):
                messages = self.prompt_builder.build_messages(
                    user_input=prompt,
                    history=self.memory.get_messages(),
                    slide_str=slide_str,
                    context_str=context_str,
                    narrative_str=narrative_str,
                    no_context=not bool(context_str),
                )
                llm_started_at = time.monotonic()
                if Config.GROQ_STREAMING:
                    response_text = self._llm().get_response_streaming(messages)
                else:
                    response_text = self._llm().get_response(messages)
            logger.info(f"Latency interruption_llm: {time.monotonic() - llm_started_at:.2f}s")

            _max_interruption_sentences = 1 if Config.LIVE_RESPONSE_MODE else 2
            response_text = trim_response(response_text, max_sentences=_max_interruption_sentences)
            response_text = format_tenri_voice_response(
                response_text,
                max_sentences=_max_interruption_sentences,
            )

            if trigger_id:
                self.policy.record_trigger_interruption(trigger_id)
            else:
                self.policy.record_interruption()

            TerminalUI.print_interruption(mode, response_text)
            if self.jarvis_ui:
                self.jarvis_ui.update_response(response_text)
                if slide:
                    self.jarvis_ui.update_slide(self.tracker.format_context(slide))

            slide_title = slide.get("title") if slide else None
            self.session_logger.log_exchange(
                user_input=f"[auto:{mode}] {prompt}",
                response=response_text,
                slide_title=slide_title,
                mode=mode,
            )

            state_manager.set_state(AppState.SPEAKING)
            audio_file = None
            if Config.VOICE_OUTPUT_ENABLED:
                with TerminalUI.get_spinner("Tenri berbicara..."):
                    tts_started_at = time.monotonic()
                    audio_file = self._tts_with_fallback(response_text)
                logger.info(f"Latency interruption_tts: {time.monotonic() - tts_started_at:.2f}s")
            if audio_file:
                self.bg_listener.mute()
                playback_started_at = time.monotonic()
                self.audio_player.play_audio(audio_file)
                self.bg_listener.unmute()
                logger.info(f"Latency interruption_audio_playback: {time.monotonic() - playback_started_at:.2f}s")
            else:
                fallback_started_at = time.monotonic()
                time.sleep(1.5)
                logger.info(f"Latency interruption_voice_fallback_wait: {time.monotonic() - fallback_started_at:.2f}s")
            self._last_tenri_response = response_text
            logger.info(f"Latency interruption_total: {time.monotonic() - interruption_started_at:.2f}s")
            # Sengaja TIDAK buka conversation window setelah proaktif:
            # Tenri yang nimbrung sendiri → presenter balik ke audiens.
            # Kalau presenter mau tindak lanjut, cukup panggil "Tenri" lagi.
        except Exception as e:
            logger.warning(f"Interruption failed: {e}")
        finally:
            state_manager.set_state(AppState.IDLE)

    def _prewarm_tts_cache(self) -> None:
        """Pre-generate TTS audio for static phrases in a background thread.

        Each phrase is passed through text_to_speech() which checks the SHA256 cache
        first — already-cached phrases are returned instantly without an API call.
        New phrases are generated and saved so subsequent runs are instant too.
        Thread is daemon so it never blocks shutdown.
        """
        if not (
            Config.TTS_PREWARM_ENABLED
            and Config.VOICE_OUTPUT_ENABLED
            and self.elevenlabs_service.client is not None
        ):
            return

        def _generate() -> None:
            logger.info(f"Pre-warming TTS cache for {len(_STATIC_TTS_PHRASES)} static phrases...")
            generated = 0
            for phrase in _STATIC_TTS_PHRASES:
                try:
                    result = self.elevenlabs_service.text_to_speech(phrase)
                    if result:
                        generated += 1
                except Exception as e:
                    logger.warning(f"TTS pre-warm failed for '{phrase[:30]}': {e}")
            logger.info(
                f"TTS pre-warm complete: {generated}/{len(_STATIC_TTS_PHRASES)} phrases ready."
            )

        self._prewarm_thread = threading.Thread(
            target=_generate, name="tts-prewarm", daemon=True
        )
        self._prewarm_thread.start()

    def _tts_with_fallback(self, text: str) -> str | None:
        """ElevenLabs first; jika gagal/None, coba local XTTS fallback.

        Returns None jika VOICE_OUTPUT_ENABLED=false atau kedua layanan tidak bisa
        menghasilkan audio (ElevenLabs error + XTTS tidak tersedia).
        """
        if not Config.VOICE_OUTPUT_ENABLED:
            return None

        # Try ElevenLabs first (cache hit → instan, miss → API call)
        if self.elevenlabs_service.client is not None:
            result = self.elevenlabs_service.text_to_speech(text)
            if result:
                return result

        # Fallback: local XTTS (jika tersedia)
        if self.local_tts_service.available:
            logger.info(f"ElevenLabs tidak menghasilkan audio — local TTS fallback: '{text[:40]}'")
            return self.local_tts_service.synthesize(text)

        return None

    # Sentence boundary: punctuation followed by whitespace, OR punctuation at the
    # end of the stream buffer. The end-of-buffer case skips a '.' right after a
    # digit because it may be an incomplete decimal still streaming in (e.g. "3."
    # before the "5" of "3.5" arrives) — defer until more text shows up (BUG-16).
    _SENT_END = re.compile(r'(?<=[.!?])\s+|(?<![0-9]\.)(?<=[.!?])$')
    _SOFT_FIRST_BREAK = re.compile(r"[,;:]\s+|\s+-\s+")
    _SOFT_FIRST_MIN_CHARS = 24
    _HARD_FIRST_MAX_CHARS = 140
    _HARD_FIRST_MIN_CHARS = 80

    @classmethod
    def _extract_stream_segment(cls, buffer: str, allow_soft: bool = False) -> tuple[str | None, str]:
        """Extract a speakable segment from streamed text.

        Sentence endings are preferred. For the first segment only, a comma/colon
        or a long clause is enough so Tenri can start speaking before the model
        finishes a full sentence.
        """
        if allow_soft:
            for match in cls._SOFT_FIRST_BREAK.finditer(buffer):
                if match.start() >= cls._SOFT_FIRST_MIN_CHARS:
                    segment = buffer[: match.start()].strip()
                    rest = buffer[match.end() :]
                    if segment and segment[-1] not in ".!?":
                        segment += "."
                    return segment, rest

        sentence_match = cls._SENT_END.search(buffer)
        if sentence_match:
            return buffer[: sentence_match.start() + 1].strip(), buffer[sentence_match.end() :]

        if not allow_soft:
            return None, buffer

        if len(buffer) >= cls._HARD_FIRST_MAX_CHARS:
            split_at = buffer.rfind(" ", cls._HARD_FIRST_MIN_CHARS, cls._HARD_FIRST_MAX_CHARS)
            if split_at == -1:
                split_at = cls._HARD_FIRST_MAX_CHARS
            segment = buffer[:split_at].strip()
            rest = buffer[split_at:].strip()
            if segment and segment[-1] not in ".!?":
                segment += "."
            return segment, rest

        return None, buffer

    @staticmethod
    def _close_stream(stream, provider: str) -> None:
        """Close a streaming iterator without masking the primary operation."""
        close_stream = getattr(stream, "close", None)
        if not callable(close_stream):
            return
        try:
            close_stream()
        except Exception as close_error:
            logger.warning("Failed to close %s stream: %s", provider, close_error)

    def _stream_and_speak(
        self,
        messages: list,
        max_sentences: int = 2,
        max_chars: int = 0,
        context_str: str = "",
    ) -> str:
        """Sentence-level streaming pipeline.

        Streams LLM tokens → emits complete sentences → TTS each sentence in a
        background thread → plays audio in order.  Sentence 1 audio starts while
        the LLM is still generating sentence 2, cutting perceived latency by ~60%.
        Stream is abandoned after max_sentences are submitted to TTS.

        Falls back to blocking get_response() on any error.
        """
        llm = self._llm()
        if not llm.client:
            return llm.get_response(messages)

        tts_ok = Config.VOICE_OUTPUT_ENABLED and (
            self.elevenlabs_service.client is not None or self.local_tts_service.available
        )
        # TAHAP 2: when streaming TTS is on, each sentence is streamed+played in one
        # serialized worker (max_workers=1) so PCM chunks play in order; the REST
        # path keeps 2 workers to overlap generation. Streaming falls back per
        # sentence to REST/edge inside the worker. getattr keeps older tests that
        # build a partial loop working (same pattern as _llm()).
        _streaming_tts = getattr(self, "streaming_tts", None)
        streaming = tts_ok and _streaming_tts is not None and _streaming_tts.available

        stream = None
        try:
            _t_start = time.monotonic()
            _t_first_sentence: float = 0.0
            _t_first_voice: float = 0.0

            _live_max_tokens = 80 if Config.LIVE_RESPONSE_MODE else Config.LLM_MAX_TOKENS
            stream = llm.stream_response_chunks(messages, max_tokens=_live_max_tokens)

            buffer = ""
            spoken_parts: list[str] = []  # sentences actually submitted to TTS
            sentence_count = 0
            # List of (text, Future[(audio_path | None, tts_generation_seconds)])
            pending: list[tuple[str, concurrent.futures.Future]] = []
            _tts_generation_total = 0.0
            _audio_playback_total = 0.0
            grounding_failed = False

            with concurrent.futures.ThreadPoolExecutor(max_workers=(1 if streaming else 2)) as executor:
                def _remaining_chars() -> int:
                    if max_chars <= 0:
                        return 0
                    current = len(" ".join(spoken_parts))
                    separator = 1 if spoken_parts else 0
                    return max_chars - current - separator

                def _submit_tts(text: str) -> concurrent.futures.Future:
                    if streaming:
                        # Audio is imminent — mute capture now (unmuted after the
                        # playback loop). The worker streams PCM and plays it; on
                        # failure it falls back to REST/edge file playback.
                        self.bg_listener.mute()

                        def _stream_play() -> tuple[bool, float, float]:
                            box = {"first": 0.0}

                            def _on_first() -> None:
                                box["first"] = time.monotonic()

                            ok = self.streaming_tts.speak(text, on_first_audio=_on_first)
                            playback_s = getattr(self.streaming_tts, "last_playback_seconds", 0.0)
                            if not ok:
                                audio_file = self._tts_with_fallback(text)
                                if audio_file:
                                    if not box["first"]:
                                        box["first"] = time.monotonic()
                                    play_started = time.monotonic()
                                    self.audio_player.play_audio(audio_file)
                                    playback_s = time.monotonic() - play_started
                                    ok = True
                            return ok, box["first"], playback_s

                        return executor.submit(_stream_play)
                    if tts_ok:
                        def _generate() -> tuple[str | None, float]:
                            _t0 = time.monotonic()
                            return self._tts_with_fallback(text), time.monotonic() - _t0

                        return executor.submit(_generate)
                    fut: concurrent.futures.Future = concurrent.futures.Future()
                    fut.set_result((None, 0.0))
                    return fut

                def _verify_before_tts(text: str) -> tuple[str, bool]:
                    if not context_str:
                        return text, False
                    verified, overridden = self.answer_verifier.check(text, context_str)
                    if overridden:
                        verified = format_tenri_voice_response(
                            verified,
                            max_sentences=1,
                        )
                        logger.info(
                            "AnswerVerifier: streaming sentence blocked before TTS; "
                            "safe fallback submitted instead."
                        )
                    return verified, overridden

                for delta in stream:
                    delta = delta or ""
                    if not delta:
                        continue
                    buffer += delta

                    segment, buffer = self._extract_stream_segment(
                        buffer,
                        # Grounding must evaluate a complete sentence. A soft
                        # comma/clause break is useful for TTFT only when there
                        # is no retrieved context to verify against.
                        allow_soft=(sentence_count == 0 and not context_str),
                    )
                    if segment:
                        sentence = segment.strip()
                        sentence = format_tenri_voice_response(sentence, max_sentences=1)
                        if max_chars > 0:
                            remaining_chars = _remaining_chars()
                            if remaining_chars <= 8:
                                break
                            sentence = trim_to_character_budget(sentence, remaining_chars)
                        sentence, grounding_failed = _verify_before_tts(sentence)
                        if len(sentence) > 8:
                            if not _t_first_sentence:
                                _t_first_sentence = time.monotonic()
                            pending.append((sentence, _submit_tts(sentence)))
                            spoken_parts.append(sentence)
                            sentence_count += 1
                            if grounding_failed:
                                break
                            if sentence_count >= max_sentences:
                                break  # stop consuming LLM stream
                            if max_chars > 0 and len(" ".join(spoken_parts)) >= max_chars:
                                break  # stop consuming LLM stream — cukup 2 kalimat

                self._close_stream(stream, "LLM")
                stream = None

                # Flush remainder hanya jika masih di bawah batas kalimat
                if not grounding_failed and sentence_count < max_sentences:
                    remainder = buffer.strip()
                    if len(remainder) > 5:
                        if not _t_first_sentence:
                            _t_first_sentence = time.monotonic()
                        remainder = format_tenri_voice_response(remainder, max_sentences=1)
                        if max_chars > 0:
                            remaining_chars = _remaining_chars()
                            if remaining_chars > 8:
                                remainder = trim_to_character_budget(remainder, remaining_chars)
                            else:
                                remainder = ""
                        remainder, grounding_failed = _verify_before_tts(remainder)
                        if len(remainder) > 8:
                            spoken_parts.append(remainder)
                            pending.append((remainder, _submit_tts(remainder)))

                # Play audio in order as each TTS future resolves
                state_manager.set_state(AppState.SPEAKING)
                for _text, future in pending:
                    try:
                        if streaming:
                            # Worker already streamed+played; just record first-voice.
                            played, first_ts, playback_s = future.result(timeout=60)
                            if played and first_ts and not _t_first_voice:
                                _t_first_voice = first_ts
                            _audio_playback_total += playback_s
                            continue
                        audio_file, tts_generation_s = future.result(timeout=30)
                        _tts_generation_total += tts_generation_s
                        if audio_file:
                            if not _t_first_voice:
                                _t_first_voice = time.monotonic()
                            self.bg_listener.mute()
                            _play_started = time.monotonic()
                            self.audio_player.play_audio(audio_file)
                            _audio_playback_total += time.monotonic() - _play_started
                            self.bg_listener.unmute()
                        elif not tts_ok:
                            if not _t_first_voice:
                                _t_first_voice = time.monotonic()
                            time.sleep(0.3)   # minimal pause between sentences
                    except Exception as e:
                        logger.warning(f"TTS sentence failed: {e}")
                self.bg_listener.unmute()  # pastikan unmuted jika ada exception di tengah

                _t_end = time.monotonic()
                self._last_llm_seconds = round((_t_first_sentence - _t_start), 2) if _t_first_sentence else 0.0
                self._last_first_voice_seconds = round((_t_first_voice - _t_start), 2) if _t_first_voice else 0.0
                self._last_tts_seconds = round(_tts_generation_total, 2)
                self._last_audio_playback_seconds = round(_audio_playback_total, 2)
                if self._last_first_voice_seconds:
                    logger.info(f"Latency first_voice: {self._last_first_voice_seconds:.2f}s")
                logger.info(
                    "Latency tts_generation_total: %.2fs audio_playback_total: %.2fs",
                    self._last_tts_seconds,
                    self._last_audio_playback_seconds,
                )

            return trim_to_character_budget(" ".join(spoken_parts).strip(), max_chars)

        except Exception as e:
            logger.warning(f"Streaming pipeline error ({e}), falling back to blocking call.")
            return llm.get_response(messages)
        finally:
            self._close_stream(stream, "LLM")

    def run(self):
        """Starts the interaction loop."""
        TerminalUI.print_welcome_banner()

        TerminalUI.print_setup_status(self._config_errors, self._config_warnings)

        self.running = True
        logger.info("Main interaction loop started.")
        logger.info(
            f"Mode: Provider={Config.LLM_PROVIDER}, VAD={'ON' if self.bg_listener.available else 'OFF (sequential fallback)'}, "
            f"Streaming={Config.GROQ_STREAMING}, LIVE_MODE={Config.LIVE_RESPONSE_MODE}"
        )
        if Config.LIVE_RESPONSE_MODE:
            logger.info("LIVE_RESPONSE_MODE aktif — respons dipaksa max 1 kalimat, max_tokens=80.")

        print("\nSistem aktif. Gunakan Ctrl+C untuk keluar dengan aman.")

        state_manager.set_state(AppState.IDLE)

        if self.tracker.is_active():
            slide = self.tracker.current_slide()
            current, total = self.tracker.position()
            TerminalUI.print_slide_startup(slide, current, total)
            if self.jarvis_ui and slide:
                self.jarvis_ui.update_slide(self.tracker.format_context(slide))

        while self.running:
            try:
                # Vision-based interruption check
                if Config.VISION_ENABLED:
                    v = self.vision_service.get_visual_context()
                    current_faces = v.get("face_count", 0) if v.get("face_detected") else 0
                    if not self._vision_initialized:
                        self._prev_face_count = current_faces
                        self._vision_initialized = True
                    else:
                        if current_faces != self._prev_face_count and self.policy.can_interrupt():
                            trigger = "audience_increase" if current_faces > self._prev_face_count else "audience_decrease"
                            self._do_interruption(self.policy.suggest_mode(trigger), self.tracker.current_slide())
                        self._prev_face_count = current_faces

                # 1. Capture input
                interaction_cycle_started_at = time.monotonic()
                user_input = ""
                self._last_wait_seconds = 0.0
                self._last_record_seconds = 0.0
                self._last_stt_seconds = 0.0
                self._last_retrieval_seconds = 0.0

                if Config.VOICE_INPUT_ENABLED and self.speech_service.microphone_available:
                    if Config.PUSH_TO_TALK_ENABLED:
                        # Mode A: Push-to-talk — tekan Enter, lalu bicara
                        print("\n[Tekan ENTER untuk mulai merekam suara...]", end="")
                        sys.stdin.readline()
                        state_manager.set_state(AppState.LISTENING)
                        user_input, success = self.speech_service.listen_and_transcribe()
                        self._last_wait_seconds = self.speech_service.last_wait_seconds
                        self._last_record_seconds = self.speech_service.last_record_seconds
                        self._last_stt_seconds = self.speech_service.last_transcribe_seconds
                        if not success:
                            if user_input == "[TIMEOUT]":
                                print("Tidak ada suara terdeteksi. Kembali ke mode siaga.")
                            elif user_input == "[UNKNOWN_AUDIO]":
                                print("Suara tidak terdengar jelas. Silakan coba lagi.")
                            else:
                                print(f"Error perekaman: {user_input}")
                            state_manager.set_state(AppState.IDLE)
                            continue
                    else:
                        # Mode B: Auto-listen — VAD queue jika tersedia, sequential jika tidak
                        state_manager.set_state(AppState.LISTENING)
                        if self.bg_listener.available:
                            user_input = self.bg_listener.get(timeout=Config.SPEECH_TIMEOUT)
                            self._last_wait_seconds = self.bg_listener.last_wait_seconds
                            self._last_record_seconds = self.bg_listener.last_record_seconds
                            self._last_stt_seconds = self.bg_listener.last_stt_seconds
                            if user_input is None:
                                # Timeout — tidak ada suara, kembali menunggu
                                state_manager.set_state(AppState.IDLE)
                                continue
                        else:
                            user_input, success = self.speech_service.listen_and_transcribe()
                            self._last_wait_seconds = self.speech_service.last_wait_seconds
                            self._last_record_seconds = self.speech_service.last_record_seconds
                            self._last_stt_seconds = self.speech_service.last_transcribe_seconds
                            if not success:
                                state_manager.set_state(AppState.IDLE)
                                time.sleep(0.5)
                                continue
                else:
                    # Mode C: Teks — fallback jika mic tidak tersedia
                    print("\n[Offline Mic] Ketik pesan Anda di bawah:")
                    user_input = input(">> ").strip()
                    if not user_input:
                        continue

                # Perintah keluar berlaku untuk semua mode input (push-to-talk,
                # auto-listen, dan teks) — bukan hanya Mode B/C seperti sebelumnya.
                if self._is_exit_command(user_input):
                    break

                if not user_input.strip():
                    state_manager.set_state(AppState.IDLE)
                    continue

                # Strip mic echo of Tenri's own last response before any processing
                user_input = self._strip_echo(user_input)
                if not user_input.strip():
                    state_manager.set_state(AppState.IDLE)
                    continue
                normalized_input = self.speech_service.normalize_transcription(user_input)
                if normalized_input != user_input:
                    logger.info("Input normalized after capture.")
                    user_input = normalized_input

                TerminalUI.print_user_message(user_input)
                if self.jarvis_ui:
                    self.jarvis_ui.update_user_input(user_input)
                response_cycle_started_at = time.monotonic()

                # 2. Slide command check - handled before intent/wake-word routing.
                if self._handle_slide_command(user_input):
                    continue

                # 3. Intent classification — routing ucapan presenter ke 5 kategori
                _in_conversation = time.monotonic() < self._conversation_until
                intent_result = self.intent_classifier.classify(
                    user_input,
                    wake_words=Config.WAKE_WORDS,
                    audience_markers=_AUDIENCE_MARKERS,
                    closing_phrases=_CLOSING_PHRASES,
                    in_conversation=_in_conversation,
                    quiet_mode=self._quiet_mode,
                )
                logger.info(f"Intent: {intent_result.intent.value} — {intent_result.reason}")

                # 4. Route berdasarkan intent
                if intent_result.intent == Intent.CLOSING_TENRI:
                    _was_already_quiet = self._quiet_mode
                    self._conversation_until = 0.0
                    self._quiet_mode = True
                    logger.info("Conversation window closed — quiet mode ON.")
                    if not _was_already_quiet:
                        _farewell = random.choice(_FAREWELL_RESPONSES)
                        TerminalUI.print_assistant_response("TENRI", _farewell)
                        if self.jarvis_ui:
                            self.jarvis_ui.update_response(_farewell)
                        state_manager.set_state(AppState.SPEAKING)
                        _farewell_audio = self._tts_with_fallback(_farewell)
                        if _farewell_audio:
                            self.bg_listener.mute()
                            self.audio_player.play_audio(_farewell_audio)
                            self.bg_listener.unmute()
                    state_manager.set_state(AppState.IDLE)
                    continue

                if intent_result.intent == Intent.ASKING_AUDIENCE:
                    logger.info("Audience-directed speech — Tenri diam.")
                    state_manager.set_state(AppState.IDLE)
                    continue

                if intent_result.intent in (Intent.EXPLAINING, Intent.AMBIENT, Intent.NOISE):
                    # EXPLAINING: presenter sedang menjelaskan → pantau trigger, jangan LLM
                    # AMBIENT: tidak ada sinyal jelas → pantau trigger, jangan LLM
                    label = intent_result.intent.value.upper()
                    if self.tracker.is_active():
                        self._handle_auto_slide_trigger(user_input)
                    if intent_result.intent == Intent.NOISE:
                        logger.info("[NOISE] STT noise ignored.")
                    elif self.trigger_service.is_active() and not self._quiet_mode:
                        ambient = self.trigger_service.detect(user_input)
                        if ambient:
                            t_id = ambient.get("id", "")
                            t_cooldown = ambient.get("cooldown_seconds", 90)
                            if self.policy.can_interrupt_trigger(t_id, t_cooldown):
                                matched_slide = self._slide_for_ids(ambient.get("slide_ids", []))
                                if matched_slide is None:
                                    matched_slide = self.tracker.current_slide()
                                topic = ambient.get("topic", "") or " ".join(ambient.get("patterns", []))
                                ctx_str, _ = self._build_interruption_context(topic, matched_slide)
                                self._do_interruption(
                                    ambient["mode"],
                                    matched_slide,
                                    self.trigger_service.build_prompt(ambient, matched_slide),
                                    trigger_id=t_id,
                                    context_str=ctx_str,
                                )
                            else:
                                logger.info(f"[{label}] Ambient trigger matched but cooldown active.")
                        else:
                            logger.info(f"[{label}] No ambient trigger — Tenri monitoring.")
                    elif intent_result.intent == Intent.AMBIENT and Config.VOICE_INPUT_ENABLED:
                        TerminalUI.print_auto_listen_hint(user_input)
                    state_manager.set_state(AppState.IDLE)
                    continue

                # ASKING_TENRI — lanjut ke pipeline LLM
                # Update user_input: hilangkan wake word jika ada
                user_input = intent_result.query if intent_result.query is not None else user_input
                _was_direct_call = intent_result.was_wake_word
                if intent_result.was_wake_word:
                    self._quiet_mode = False

                # Hanya wake word tanpa query: jangan panggil LLM/retrieval.
                # Sapaan harus terasa instan; kecerdasan model baru dipakai saat ada pertanyaan.
                if intent_result.was_wake_word and not user_input.strip():
                    self._conversation_until = time.monotonic() + Config.CONVERSATION_WINDOW
                    _greeting = random.choice(_WAKE_ACK_RESPONSES)
                    _greeting = self._sanitize_wake_ack_response(_greeting)
                    state_manager.set_state(AppState.SPEAKING)
                    if Config.VOICE_OUTPUT_ENABLED:
                        _greet_audio = self._tts_with_fallback(_greeting)
                        if _greet_audio:
                            self.bg_listener.mute()
                            self.audio_player.play_audio(_greet_audio)
                            self.bg_listener.unmute()
                    self._last_tenri_response = _greeting
                    TerminalUI.print_assistant_response("TENRI", _greeting)
                    if self.jarvis_ui:
                        self.jarvis_ui.update_response(_greeting)
                    state_manager.set_state(AppState.IDLE)
                    continue

                _has_question = _has_question_word(user_input)

                # Acknowledgment singkat dalam conversation window → Tenri diam, tidak panggil LLM.
                # Hanya berlaku jika bukan panggilan wake word langsung dan tidak ada kata tanya.
                if not _was_direct_call and not _has_question:
                    _norm_ack = re.sub(r'[^\w\s]', ' ', user_input.lower())
                    _norm_ack = re.sub(r'\s+', ' ', _norm_ack).strip()
                    if _norm_ack in _ACKNOWLEDGMENT_PHRASES:
                        logger.info(f"Acknowledgment dalam conversation window — Tenri diam: '{_norm_ack}'")
                        state_manager.set_state(AppState.IDLE)
                        continue

                # Auto-advance slide dari kata kunci dalam query
                if self.tracker.is_active():
                    self._handle_auto_slide_trigger(user_input)

                # Ambient trigger check untuk ASKING_TENRI
                # Jika ada trigger dan bukan pertanyaan langsung → lakukan interruption, skip LLM
                if self.trigger_service.is_active():
                    ambient = self.trigger_service.detect(user_input)
                    if ambient:
                        t_id = ambient.get("id", "")
                        t_cooldown = ambient.get("cooldown_seconds", 90)
                        trigger_fired = False
                        if self.policy.can_interrupt_trigger(t_id, t_cooldown):
                            matched_slide = self._slide_for_ids(ambient.get("slide_ids", []))
                            if matched_slide is None:
                                matched_slide = self.tracker.current_slide()
                            if not _has_question and not self._quiet_mode:
                                topic = ambient.get("topic", "") or " ".join(ambient.get("patterns", []))
                                ctx_str, _ = self._build_interruption_context(topic, matched_slide)
                                self._do_interruption(
                                    ambient["mode"],
                                    matched_slide,
                                    self.trigger_service.build_prompt(ambient, matched_slide),
                                    trigger_id=t_id,
                                    context_str=ctx_str,
                                )
                            trigger_fired = True
                        in_conv = time.monotonic() < self._conversation_until
                        if not _has_question and (not in_conv or trigger_fired):
                            state_manager.set_state(AppState.IDLE)
                            continue

                # 5. LLM pipeline
                vision_context = self.vision_service.get_visual_context()
                TerminalUI.print_sensory_update(vision_context)
                state_manager.set_state(AppState.THINKING)

                slide = self.tracker.current_slide()
                is_slide_explanation = self._is_slide_explanation_request(user_input)
                if is_slide_explanation:
                    enriched_query = self._slide_explanation_query(slide, user_input)
                    logger.info("Slide explanation route active.")
                else:
                    enriched_query = self.query_rewriter.rewrite(
                        user_input,
                        slide,
                        self.memory.get_messages(),
                    )
                if enriched_query != user_input:
                    logger.info(f"QueryRewriter: '{user_input[:50]}' → '{enriched_query[:80]}'")
                retrieval_started_at = time.monotonic()
                context_chunks = self.retrieval.search(enriched_query)
                if is_slide_explanation:
                    filtered_chunks = self._filter_slide_explanation_chunks(context_chunks)
                    if len(filtered_chunks) != len(context_chunks):
                        logger.info(
                            "Slide explanation retrieval filtered persona/project-meta chunks."
                        )
                    context_chunks = filtered_chunks
                if context_chunks and not self.retrieval.has_strong_match(context_chunks):
                    logger.info("Retrieval discarded: weak query/source overlap.")
                    context_chunks = []
                context_str = self.retrieval.format_context(context_chunks)
                no_context = not bool(context_chunks)
                self._last_retrieval_seconds = round(time.monotonic() - retrieval_started_at, 2)
                logger.info(f"Latency retrieval: {self._last_retrieval_seconds:.2f}s")
                if context_chunks:
                    sources_used = list({c.get("source_id") for c in context_chunks})
                    logger.info(f"Sources used: {sources_used}")
                    TerminalUI.print_retrieval_sources(context_chunks)

                slide_str = self.tracker.format_context(slide) if slide else ""
                narrative_str = self.tracker.format_narrative_context()

                if is_slide_explanation:
                    messages = self.prompt_builder.build_slide_explanation_messages(
                        user_input=user_input,
                        history=self.memory.get_messages(),
                        slide_str=slide_str,
                        context_str=context_str,
                        narrative_str=narrative_str,
                    )
                else:
                    messages = self.prompt_builder.build_messages(
                        user_input=user_input,
                        history=self.memory.get_messages(),
                        vision_context=vision_context,
                        slide_str=slide_str,
                        context_str=context_str,
                        no_context=no_context,
                        narrative_str=narrative_str,
                    )

                self._last_llm_seconds = 0.0
                self._last_first_voice_seconds = 0.0
                self._last_tts_seconds = 0.0
                self._last_audio_playback_seconds = 0.0

                _max_sent = 1 if Config.LIVE_RESPONSE_MODE else Config.RESPONSE_MAX_SENTENCES
                _max_chars = self._live_char_budget(user_input)
                llm_started_at = time.monotonic()
                if Config.GROQ_STREAMING:
                    with TerminalUI.get_spinner("Tenri sedang menjawab..."):
                        response_text = self._stream_and_speak(
                            messages,
                            max_sentences=_max_sent,
                            max_chars=_max_chars,
                            context_str=context_str,
                        )
                    logger.info(f"Latency stream_pipeline: {time.monotonic() - llm_started_at:.2f}s")
                else:
                    with TerminalUI.get_spinner("Tenri sedang memikirkan jawaban..."):
                        response_text = self._llm().get_response(messages)
                    logger.info(f"Latency llm: {time.monotonic() - llm_started_at:.2f}s")

                response_text = format_tenri_voice_response(response_text, max_sentences=_max_sent)
                response_text = trim_response(response_text, max_sentences=_max_sent)
                response_text = trim_to_character_budget(response_text, _max_chars)

                # Streaming verifies each sentence before TTS submission. Blocking
                # mode verifies the complete response here before playback.
                if context_str and not Config.GROQ_STREAMING:
                    _verified, _overridden = self.answer_verifier.check(response_text, context_str)
                    if _overridden:
                        response_text = _verified
                        response_text = format_tenri_voice_response(response_text, max_sentences=_max_sent)
                        response_text = trim_to_character_budget(response_text, _max_chars)
                        logger.info("AnswerVerifier: low grounding detected; fallback applied.")

                self._last_tenri_response = response_text

                self.memory.add_user_message(user_input)
                self.memory.add_assistant_message(response_text)

                if _has_question or _was_direct_call:
                    self._conversation_until = time.monotonic() + Config.CONVERSATION_WINDOW
                    logger.info(f"Conversation window extended for {Config.CONVERSATION_WINDOW:.0f}s.")
                else:
                    remaining = max(0.0, self._conversation_until - time.monotonic())
                    logger.info(f"Conversation window NOT extended (ambient catch). {remaining:.0f}s left.")

                TerminalUI.print_assistant_response("TENRI", response_text)
                if self.jarvis_ui:
                    self.jarvis_ui.update_response(response_text)

                # 6. Non-streaming TTS+playback (streaming menanganinya di dalam _stream_and_speak)
                if not Config.GROQ_STREAMING:
                    state_manager.set_state(AppState.SPEAKING)
                    audio_file = None
                    if Config.VOICE_OUTPUT_ENABLED:
                        with TerminalUI.get_spinner("Mengubah teks menjadi suara..."):
                            tts_started_at = time.monotonic()
                            audio_file = self._tts_with_fallback(response_text)
                        self._last_tts_seconds = round(time.monotonic() - tts_started_at, 2)
                        logger.info(f"Latency tts: {self._last_tts_seconds:.2f}s")
                    if audio_file:
                        self.bg_listener.mute()
                        playback_started_at = time.monotonic()
                        self._last_first_voice_seconds = round(
                            playback_started_at - response_cycle_started_at,
                            2,
                        )
                        logger.info(f"Latency first_voice: {self._last_first_voice_seconds:.2f}s")
                        self.audio_player.play_audio(audio_file)
                        self.bg_listener.unmute()
                        self._last_audio_playback_seconds = round(
                            time.monotonic() - playback_started_at,
                            2,
                        )
                        logger.info(f"Latency audio_playback: {self._last_audio_playback_seconds:.2f}s")
                    else:
                        time.sleep(1.5)
                logger.info(f"Latency response_cycle_total: {time.monotonic() - response_cycle_started_at:.2f}s")

                # Ringkasan timing dicetak SETELAH step 6 agar metrik TTS/FirstVoice/
                # Audio pada jalur non-streaming sudah terisi (bukan 0). Jalur streaming
                # mengisi metrik ini di dalam _stream_and_speak sebelum titik ini.
                _cycle_s = round(time.monotonic() - interaction_cycle_started_at, 1)
                TerminalUI.print_timing_summary(
                    llm_s=self._last_llm_seconds,
                    tts_s=self._last_tts_seconds,
                    cycle_s=_cycle_s,
                    wait_s=self._last_wait_seconds,
                    record_s=self._last_record_seconds,
                    stt_s=self._last_stt_seconds,
                    retrieval_s=self._last_retrieval_seconds,
                    first_voice_s=self._last_first_voice_seconds,
                    audio_playback_s=self._last_audio_playback_seconds,
                )

                # Catat exchange + metrik latensi per-turn SETELAH step 6 agar
                # tts/first_voice/playback terisi untuk mode streaming maupun non-streaming.
                self.session_logger.log_exchange(
                    user_input=user_input,
                    response=response_text,
                    sources=[c.get("source_id") for c in context_chunks],
                    slide_title=slide.get("title") if slide else None,
                    mode="normal",
                    metrics={
                        "wait": self._last_wait_seconds,
                        "record": self._last_record_seconds,
                        "stt": self._last_stt_seconds,
                        "retrieval": self._last_retrieval_seconds,
                        "llm_first": self._last_llm_seconds,
                        "tts_first_voice": self._last_first_voice_seconds,
                        "tts_gen": self._last_tts_seconds,
                        "playback": self._last_audio_playback_seconds,
                        "cycle": _cycle_s,
                    },
                )

                state_manager.set_state(AppState.IDLE)

            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt caught in interaction loop.")
                break
            except Exception as e:
                logger.error(f"Error in interaction loop iteration: {e}", exc_info=True)
                state_manager.set_state(AppState.ERROR, str(e))
                time.sleep(2.0)
                state_manager.set_state(AppState.IDLE)

        self.cleanup()

    def request_stop(self) -> None:
        """Request a cooperative stop from the UI/main thread."""
        self.running = False

    def cleanup(self):
        """Releases hardware resources and performs temp cleanup."""
        self.running = False
        # Detach from the singleton state manager so re-entering "Jalankan Tenri"
        # from the menu does not stack duplicate state listeners.
        state_manager.unregister_listener(self._on_state_change)
        print("\nSedang menghentikan sensor visual dan merilis hardware...")
        self.vision_service.stop()
        self.bg_listener.stop()
        self.audio_player.stop()
        self.elevenlabs_service.close()
        
        print("Membersihkan berkas audio sementara...")
        FileManager.cleanup_temp_files()
        
        print("Sampai jumpa. Tenri dinonaktifkan.\n")
        logger.info("Tenri Companion Terminal shut down.")
