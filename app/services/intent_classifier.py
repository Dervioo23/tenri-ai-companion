import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("AICompanion.IntentClassifier")


class Intent(Enum):
    ASKING_TENRI = "asking_tenri"
    ASKING_AUDIENCE = "asking_audience"
    CLOSING_TENRI = "closing_tenri"
    EXPLAINING = "explaining"
    NOISE = "noise"
    AMBIENT = "ambient"


@dataclass
class IntentResult:
    intent: Intent
    query: str
    reason: str
    was_wake_word: bool = field(default=False)


_EXPLAIN_OPENERS: frozenset[str] = frozenset({
    "jadi", "jadi itu", "jadi kalau", "jadi sebenarnya",
    "maksudnya", "maksud saya", "maksud dari",
    "artinya", "arti dari", "yang dimaksud",
    "pada dasarnya", "sebenarnya", "sebetulnya",
    "perlu diketahui", "perlu dipahami", "perlu diingat",
    "kalau kita lihat", "kalau kita perhatikan",
    "dalam konteks", "dalam hal ini", "dalam kasus ini",
    "contohnya", "misalnya", "seperti halnya",
    "yang pertama", "yang kedua", "yang ketiga",
    "pertama-tama", "langkah pertama",
    "kita tahu bahwa", "kita bisa lihat",
    "ada beberapa", "terdapat beberapa",
    "berdasarkan", "menurut data",
    "secara singkat", "secara umum", "secara garis besar",
    "di sini kita", "di sini saya akan",
    "hari ini kita", "hari ini saya",
    "nah", "nah jadi", "nah kalau",
})

_AUDIENCE_INVITE: frozenset[str] = frozenset({
    "menurut kalian", "menurut teman-teman", "menurut anda semua",
    "apa pendapat kalian", "bagaimana pendapat kalian",
    "setuju tidak", "betul tidak", "benar tidak",
    "ada yang tahu", "ada yang bisa jawab", "ada yang bisa menjawab",
    "ada pertanyaan", "ada yang mau bertanya",
    "coba pikirkan", "coba bayangkan",
    "kalian pernah", "pernah tidak kalian",
    "siapa yang pernah", "siapa yang tahu",
    "apakah kalian", "apakah teman-teman",
    "raise your hand", "who knows", "any questions",
    "gimana menurut kalian", "gimana menurut teman-teman",
})

_STAGE_TRANSITION_PHRASES: frozenset[str] = frozenset({
    "selamat menikmati",
    "selamat menyimak",
    "silakan menikmati",
    "silahkan menikmati",
    "silakan menyimak",
    "silahkan menyimak",
    "mari kita lanjut",
    "kita lanjut",
    "baik kita lanjut",
    "oke kita lanjut",
    "ok kita lanjut",
    "sekarang kita lanjut",
    "lanjut ke bagian",
    "lanjut ke materi",
    "lanjut ke pembahasan",
    "lanjut pembahasan",
    "baik lanjut",
    "oke lanjut",
    "ok lanjut",
    "saya lanjut",
    "saya akan lanjut",
    "kita masuk ke",
    "sekarang kita masuk",
    "berikutnya kita",
    "baik teman-teman",
    "oke teman-teman",
    "untuk teman-teman",
    "untuk hadirin",
    "untuk audiens",
})

_NOISE_PHRASES: frozenset[str] = frozenset({
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
    "you",
    "i",
    "bye bye",
    "see you",
    "good bye",
})

_QUESTION_WORDS: frozenset[str] = frozenset({
    "apa", "apakah", "kenapa", "mengapa", "bagaimana", "gimana",
    "siapa", "dimana", "di mana", "kapan", "berapa",
    "jelaskan", "ceritakan", "ketahui", "maksudnya", "memangnya",
})

_CLARIFICATION_PATTERNS: frozenset[str] = frozenset({
    "seperti apa",
    "yang mana",
    "bagian mana",
    "maksudnya",
    "maksudnya apa",
    "maksudnya bagaimana",
    "yang dimaksud",
    "yang dibayangkan",
    "contohnya",
    "contohnya apa",
    "contohnya seperti apa",
    "bedanya",
    "bedanya apa",
    "kok bisa",
    "kok begitu",
    "masa begitu",
    "memangnya",
    "berarti",
    "berarti apa",
    "jadi maksudnya",
})

_REFERENCE_FOLLOWUP_TERMS: frozenset[str] = frozenset({
    "itu",
    "tadi",
    "begitu",
    "tersebut",
    "hal itu",
    "bagian itu",
    "yang tadi",
    "yang itu",
    "yang dibayangkan",
    "yang dimaksud",
})

_FOLLOWUP_TO_TENRI_PHRASES: frozenset[str] = frozenset({
    "jelaskan",
    "jelaskan lagi",
    "jelaskan lebih",
    "lebih detail",
    "lebih rinci",
    "lanjutkan penjelasan",
    "lanjutin penjelasan",
    "teruskan",
    "terus gimana",
    "maksudnya",
    "apa maksudnya",
    "contohnya",
    "beri contoh",
    "kasih contoh",
    "jawab",
    "jawab singkat",
    "perjelas",
    "koreksi",
    "bandingkan",
    "simpulkan",
    "ringkas",
    "ulangi",
    *_CLARIFICATION_PATTERNS,
})

_DIRECT_COMMAND_VERBS: frozenset[str] = frozenset({
    "jelaskan",
    "ceritakan",
    "terangkan",
    "perjelas",
    "uraikan",
    "ringkas",
    "simpulkan",
})

_PRESENTATION_TARGET_WORDS: frozenset[str] = frozenset({
    "slide",
    "bagian",
    "materi",
    "poin",
    "topik",
    "halaman",
    "presentasi",
    "pertama",
    "kedua",
    "ketiga",
    "berikutnya",
    "sebelumnya",
})

_EXPLAIN_WORD_THRESHOLD = 15


class IntentClassifier:
    """Rule-first intent router for live presentation speech.

    Tenri should answer only when the utterance is clearly addressed to her:
    explicit wake word, a real question, or a clear follow-up inside the
    conversation window. Presenter narration, stage direction, STT noise, and
    ambiguous fragments are routed to silence/monitoring.
    """

    def __init__(self) -> None:
        self._local: Optional[object] = None
        try:
            from app.config import Config
            if Config.LOCAL_INTENT_CLASSIFIER:
                from app.services.local_intent_classifier import LocalIntentClassifier
                self._local = LocalIntentClassifier()
                logger.info("LocalIntentClassifier loaded as AMBIENT fallback.")
        except Exception as exc:
            logger.warning("LocalIntentClassifier failed to load: %s", exc)

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", text.lower())).strip()

    def _contains_phrase(self, text: str, phrases: frozenset[str]) -> str | None:
        norm = self._normalize(text)
        padded = f" {norm} "
        for phrase in sorted(phrases, key=len, reverse=True):
            phrase_norm = self._normalize(phrase)
            if not phrase_norm:
                continue
            if norm == phrase_norm or f" {phrase_norm} " in padded:
                return phrase
        return None

    def _is_stage_transition(self, text: str) -> str | None:
        return self._contains_phrase(text, _STAGE_TRANSITION_PHRASES)

    def _is_noise(self, text: str) -> str | None:
        norm = self._normalize(text)
        if not norm:
            return "empty"
        noise_phrase = self._contains_phrase(text, _NOISE_PHRASES)
        if noise_phrase:
            return noise_phrase

        words = norm.split()
        if len(words) == 1 and len(words[0]) <= 2:
            return "single tiny token"
        if len(words) >= 2 and len(set(words)) == 1 and len(words[0]) <= 5:
            return "repeated short token"
        return None

    def _has_question_signal(self, text: str) -> bool:
        if "?" in text:
            return True
        norm = self._normalize(text)
        padded = f" {norm} "
        return any(f" {self._normalize(q)} " in padded for q in _QUESTION_WORDS)

    def _has_clarification_pattern(self, text: str) -> bool:
        return self._contains_phrase(text, _CLARIFICATION_PATTERNS) is not None

    def _has_reference_followup(self, text: str) -> bool:
        norm = self._normalize(text)
        words = norm.split()
        if len(words) > 10:
            return False
        return self._contains_phrase(text, _REFERENCE_FOLLOWUP_TERMS) is not None

    def _followup_signal_reason(self, text: str) -> str | None:
        if "?" in text:
            return "question mark"

        norm = self._normalize(text)
        padded = f" {norm} "
        for question in sorted(_QUESTION_WORDS, key=len, reverse=True):
            question_norm = self._normalize(question)
            if question_norm and f" {question_norm} " in padded:
                return f"question word '{question}'"

        clarification = self._contains_phrase(text, _CLARIFICATION_PATTERNS)
        if clarification:
            return f"clarification pattern '{clarification}'"

        norm_words = norm.split()
        if len(norm_words) <= 10:
            reference = self._contains_phrase(text, _REFERENCE_FOLLOWUP_TERMS)
            if reference:
                return f"reference follow-up '{reference}'"

        phrase = self._contains_phrase(text, _FOLLOWUP_TO_TENRI_PHRASES)
        if phrase:
            return f"follow-up phrase '{phrase}'"

        return None

    def _has_followup_signal(self, text: str) -> bool:
        return self._followup_signal_reason(text) is not None

    def _is_direct_presentation_command(self, text: str) -> bool:
        norm_tokens = set(self._normalize(text).split())
        return bool(norm_tokens & _DIRECT_COMMAND_VERBS) and bool(
            norm_tokens & _PRESENTATION_TARGET_WORDS
        )

    def _is_explaining(self, text: str, lower: str, word_count: int) -> IntentResult | None:
        if self._has_question_signal(text) or self._has_clarification_pattern(text):
            return None

        if word_count >= _EXPLAIN_WORD_THRESHOLD and not self._has_question_signal(text):
            opener = next((o for o in _EXPLAIN_OPENERS if lower.startswith(o)), None)
            if opener:
                return IntentResult(
                    Intent.EXPLAINING, text,
                    f"Explanation opener '{opener}' ({word_count} words)"
                )
            return IntentResult(
                Intent.EXPLAINING, text,
                f"Long non-question utterance ({word_count} words)"
            )

        if self._local is not None:
            local_label, local_conf = self._local.predict(text)
            if local_label == "explaining" and local_conf >= self._local.min_confidence:
                return IntentResult(
                    Intent.EXPLAINING, text,
                    f"LocalClassifier:explaining (conf={local_conf:.2f}, {word_count} words)"
                )
        return None

    def _is_closing_phrase(
        self,
        text: str,
        closing_phrases: frozenset[str],
        wake_words: list[str],
    ) -> bool:
        norm = self._normalize(text).rstrip(".!?")

        def _matches(s: str) -> bool:
            return (
                s in closing_phrases
                or any(
                    s == p or s.startswith(p + " ") or s.endswith(" " + p)
                    for p in closing_phrases
                )
            )

        if _matches(norm):
            return True

        for wake in sorted(wake_words, key=len, reverse=True):
            wake_norm = self._normalize(wake)
            if norm.endswith(wake_norm):
                without_wake = norm[: -len(wake_norm)].strip().rstrip(".!?")
                if without_wake and _matches(without_wake):
                    return True
        return False

    def classify(
        self,
        text: str,
        *,
        wake_words: list[str],
        audience_markers: frozenset[str],
        closing_phrases: frozenset[str],
        in_conversation: bool,
        quiet_mode: bool,
    ) -> IntentResult:
        lower = text.lower().strip()
        word_count = len(lower.split())

        has_wake_in_text = any(ww in lower for ww in wake_words)
        if (in_conversation or has_wake_in_text) and self._is_closing_phrase(text, closing_phrases, wake_words):
            return IntentResult(
                Intent.CLOSING_TENRI, text,
                f"Closing phrase: '{self._normalize(text)}'"
            )

        for marker in audience_markers:
            if marker in lower:
                return IntentResult(
                    Intent.ASKING_AUDIENCE, text,
                    f"Audience marker: '{marker}'"
                )

        invite = self._contains_phrase(text, _AUDIENCE_INVITE)
        if invite:
            return IntentResult(
                Intent.ASKING_AUDIENCE, text,
                f"Audience invite: '{invite}'"
            )

        query = self._extract_wake_call(lower, text, wake_words)
        if query is not None:
            return IntentResult(
                Intent.ASKING_TENRI, query,
                "Wake word detected", was_wake_word=True
            )

        stage_phrase = self._is_stage_transition(text)
        if stage_phrase:
            return IntentResult(
                Intent.ASKING_AUDIENCE, text,
                f"Stage transition: '{stage_phrase}'"
            )

        noise_reason = self._is_noise(text)
        if noise_reason:
            return IntentResult(
                Intent.NOISE, text,
                f"STT noise: '{noise_reason}'"
            )

        if quiet_mode:
            return IntentResult(
                Intent.AMBIENT, text,
                "Quiet mode active: wake word required"
            )

        if self._is_direct_presentation_command(text):
            return IntentResult(
                Intent.ASKING_TENRI, text,
                "Direct presentation command"
            )

        if in_conversation:
            followup_reason = self._followup_signal_reason(text)
            if followup_reason:
                return IntentResult(
                    Intent.ASKING_TENRI, text,
                    f"Conversation follow-up signal: {followup_reason}"
                )
            # In conversation mode, short ambiguous presenter-like fragments
            # should stay quiet. Longer explanation-like utterances can still be
            # routed below, but local classifier must not override follow-ups.
            explaining = self._is_explaining(text, lower, word_count)
            if explaining:
                explaining.reason = f"Conversation explanation-like utterance: {explaining.reason}"
                return explaining
            return IntentResult(
                Intent.AMBIENT, text,
                "Conversation ambient: no question/clarification/reference "
                f"signal ({word_count} words)"
            )

        explaining = self._is_explaining(text, lower, word_count)
        if explaining:
            return explaining

        if self._has_question_signal(text):
            return IntentResult(
                Intent.ASKING_TENRI, text,
                "Question bypass: no audience signal detected"
            )

        return IntentResult(
            Intent.AMBIENT, text,
            f"No clear signal ({word_count} words)"
        )

    def _extract_wake_call(self, lower: str, original: str, wake_words: list[str]) -> str | None:
        for wake in sorted(wake_words, key=len, reverse=True):
            if wake in lower:
                idx = lower.find(wake)
                after = original[idx + len(wake):].strip().lstrip(",. !?")
                return after
        return None
