"""Conversation vocabulary for the web backend.

These mirror the constants in ``app/core/interaction_loop.py``. They are copied
here (not imported) because that module pulls in audio dependencies (PyAudio,
pygame, ElevenLabs) that must not be required by the keyless, audio-free backend.

TECH DEBT: a future refactor should extract this vocab into a shared, audio-free
module (e.g. ``app/core/conversation_vocab.py``) imported by both the terminal
loop and this backend, removing the duplication. Kept in sync manually for now.
"""

from __future__ import annotations

import re

from app.config import Config

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

_QUESTION_WORD_RE = re.compile(
    r"\b(?:"
    + "|".join(sorted((re.escape(w) for w in _QUESTION_SUBSTRINGS), key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def has_question_word(text: str) -> bool:
    """True when text contains a '?' or a standalone Indonesian question word."""
    return "?" in text or bool(_QUESTION_WORD_RE.search(text))


CLOSING_PHRASES: frozenset[str] = frozenset({
    "terima kasih", "makasih", "oke makasih", "oke terima kasih",
    "ya makasih", "ya terima kasih", "baik terima kasih", "baik makasih",
    "sudah", "sudah cukup", "cukup", "oke cukup", "ya sudah", "ya cukup",
    "thanks", "thank you", "oke thanks", "oke thank you",
    "mantap terima kasih", "oke mantap", "sip terima kasih",
    "sama sama", "sama-sama", "iya sama sama", "ya sama sama",
    "oke sama sama", "baik sama sama",
    "sekian", "sekian dulu", "segitu dulu", "segini dulu",
    "udahan", "ya udah", "udah deh", "ya udah deh", "oke deh",
    "cukup sekian", "sudah selesai", "selesai sudah",
})

ACKNOWLEDGMENT_PHRASES: frozenset[str] = frozenset({
    "ya", "oke", "ok", "iya", "baik", "mengerti", "paham",
    "siap", "sip", "noted", "got it", "i see",
    "ya oke", "ya ok", "oke baik", "ok baik",
    "ya baik", "iya baik", "iya oke", "iya ok",
    "ya ya", "oke oke", "iya iya",
    "oh oke", "oh ok", "oh iya", "oh ya",
    "hmm", "hm", "mmm",
    "hmm oke", "hmm ok", "hmm ya",
    "hai", "halo", "hey", "hi", "hello",
    "hai tenri", "halo tenri", "hey tenri", "hi tenri",
    "ya saya di sini", "ya saya disini",
    "iya saya di sini", "iya saya disini",
    "saya di sini", "saya disini",
})

AUDIENCE_MARKERS: frozenset[str] = frozenset({
    "teman-teman", "hadirin", "kalian", "semuanya", "semua nya",
    "kawan-kawan", "peserta", "bapak ibu", "ibu bapak",
    "guys", "everyone", "rekan-rekan",
    "selamat pagi", "selamat siang", "selamat sore", "selamat malam",
    "audiens", "penonton", "pemirsa",
    "selamat menikmati", "selamat menyimak",
    "silakan menikmati", "silahkan menikmati",
    "silakan menyimak", "silahkan menyimak",
})

FAREWELL_RESPONSES: list[str] = [
    "Sama-sama.",
    "Senang bisa membantu.",
    "Tentu, sama-sama.",
    "Dengan senang hati.",
    "Baik, saya di sini jika dibutuhkan lagi.",
]

WAKE_ACK_FALLBACK = "Iye, saya di sini."
WAKE_ACK_RESPONSES: tuple[str, ...] = (
    "Saya dengar.",
    "Iye, saya di sini.",
    "Ada, saya dengar.",
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


def is_slide_explanation_request(text: str) -> bool:
    return bool(_SLIDE_EXPLANATION_RE.search(text or ""))


def input_requests_detail(text: str) -> bool:
    return bool(_DETAIL_REQUEST_RE.search(text or ""))


def slide_explanation_query(slide: dict | None, fallback: str) -> str:
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


def filter_slide_explanation_chunks(chunks: list) -> list:
    """Prefer slide/topic sources over persona/project-meta documents."""
    if not chunks:
        return []
    preferred = [
        chunk for chunk in chunks
        if str(chunk.get("source_id", "")).lower()
        not in _SLIDE_EXPLANATION_DEPRIORITIZED_SOURCES
    ]
    return preferred or chunks


def response_caps(user_input: str) -> dict:
    """Sentence/token/char budget for the answer, detail-aware (mirrors the loop)."""
    detail = input_requests_detail(user_input)
    if detail:
        return {
            "max_sentences": Config.DETAIL_RESPONSE_MAX_SENTENCES,
            "max_tokens": Config.DETAIL_RESPONSE_MAX_TOKENS,
            "max_chars": 0,
        }
    return {
        "max_sentences": 1 if Config.LIVE_RESPONSE_MODE else Config.RESPONSE_MAX_SENTENCES,
        "max_tokens": 80 if Config.LIVE_RESPONSE_MODE else Config.LLM_MAX_TOKENS,
        "max_chars": Config.LIVE_RESPONSE_MAX_CHARS,
    }
