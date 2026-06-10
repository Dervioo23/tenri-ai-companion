import logging
import re
from typing import Optional

logger = logging.getLogger("AICompanion.QueryRewriter")

_SKIP_CAPITALIZED: frozenset[str] = frozenset({
    "Tenri", "Saya", "Anda", "Yang", "Dari", "Dengan", "Untuk", "Dalam",
    "Pada", "Atau", "Jika", "Dan", "Tapi", "Namun", "Ketika", "Karena",
    "Bahwa", "Mereka", "Kita", "Kami", "Sebuah", "Setiap", "Setelah",
    "Sebelum", "Meskipun", "Tetapi", "Sebagai", "Ini", "Itu", "Ada",
    "Juga", "Sudah", "Bisa", "Akan", "Lebih", "Bukan", "Tidak", "Salah",
    "Satu", "Dua", "Tiga", "Oleh", "Atas", "Bagi", "Tanpa", "Antara",
    "Selain", "Serta", "Hingga", "Sampai", "Selama", "Ketiga", "Begitu",
    "Seperti", "Bahkan", "Maka", "Bila", "Apabila", "Sehingga",
    "Walaupun", "Adapun", "Apalagi", "Artinya", "Misalnya",
})

_ANAPHOR_PHRASES: tuple[str, ...] = (
    "tadi kamu bilang soal",
    "tadi kamu bilang tentang",
    "tadi kamu bilang",
    "yang tadi kamu bilang",
    "yang baru saja kamu bilang",
    "yang barusan kamu bilang",
    "yang dimaksud tadi",
    "hal yang tadi dibahas",
    "yang tadi dibahas",
    "yang tadi disebutkan",
    "yang baru saja disebutkan",
    "yang baru saja dibahas",
    "yang baru saja",
    "yang barusan",
    "yang tadi",
    "hal tersebut",
    "soal tersebut",
    "soal itu tadi",
    "hal itu tadi",
)

_ELABORATION_PHRASES: tuple[str, ...] = (
    "lebih detail",
    "lebih lanjut",
    "lebih lengkap",
    "lebih dalam",
    "jelaskan lebih",
    "ceritakan lebih",
    "tolong jelaskan lebih",
    "gimana lebih",
    "bagaimana lebih",
    "kasih tau lebih",
    "beritahu lebih",
)

_SLIDE_REFERENCE_PHRASES: tuple[str, ...] = (
    "slide ini", "slide tersebut", "bagian ini", "materi ini", "poin ini",
    "hal ini", "yang di slide", "slide pertama", "slide kedua", "slide ketiga",
    "slide berikutnya", "slide sebelumnya",
)

_GENERIC_QUESTION_PHRASES: frozenset[str] = frozenset({
    "apa kabar",
    "kamu apa kabar",
    "bagaimana kabarmu",
    "gimana kabarmu",
    "siapa kamu",
    "kamu bisa apa",
    "lagi apa",
})

_DOMAIN_HINTS: frozenset[str] = frozenset({
    "ai", "kecerdasan", "buatan", "machine", "learning", "deep", "model",
    "data", "algoritma", "neural", "arsip", "naskah", "lontara", "museum",
    "galigo", "bugis", "makassar", "sawerigading", "tenriabeng",
    "digitalisasi", "pelestarian", "pengetahuan", "teknologi", "presentasi",
    "slide", "dokumen", "paper", "materi", "mengarsipkan",
})


class QueryRewriter:
    """Build safer RAG search queries from presenter utterances.

    The important rule: active slide context is not appended blindly. It is used
    only when the utterance refers to the slide, is a vague follow-up, or has a
    project/domain anchor. Generic questions stay generic so retrieval can
    correctly return no context.
    """

    def rewrite(
        self,
        query: str,
        slide: Optional[dict],
        history: list,
    ) -> str:
        query_lower = query.lower().strip()
        if self._is_generic_question(query_lower):
            return query

        slide_terms: list[str] = []
        if slide:
            title = slide.get("title", "")
            if title:
                slide_terms.append(title)
            slide_terms.extend(slide.get("topics", []))

        is_vague = self._is_vague(query_lower) or self._is_too_short_and_unspecific(
            query, query_lower
        )

        if not is_vague:
            if slide_terms and self._should_enrich_with_slide(query, query_lower, slide_terms):
                return f"{query} {' '.join(slide_terms)}"
            return query

        history_entities = self._extract_entities_from_history(history)
        query_entities = self._extract_entities_from_text(query)

        seen: set[str] = set()
        all_terms: list[str] = []
        for term in slide_terms + history_entities + query_entities:
            key = term.lower()
            if key not in seen:
                seen.add(key)
                all_terms.append(term)

        if not all_terms:
            return query

        rewritten = " ".join(all_terms)
        logger.info(
            "QueryRewriter vague rewrite: '%s' -> '%s'",
            query[:60],
            rewritten[:80],
        )
        return rewritten

    def _is_vague(self, query_lower: str) -> bool:
        for phrase in _ANAPHOR_PHRASES:
            if phrase in query_lower:
                return True
        for phrase in _ELABORATION_PHRASES:
            if phrase in query_lower:
                return True
        return False

    def _mentions_slide(self, query_lower: str) -> bool:
        return any(phrase in query_lower for phrase in _SLIDE_REFERENCE_PHRASES)

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()

    def _is_generic_question(self, query_lower: str) -> bool:
        return self._normalize(query_lower) in _GENERIC_QUESTION_PHRASES

    def _has_domain_hint(self, text_lower: str) -> bool:
        tokens = set(self._normalize(text_lower).split())
        return bool(tokens & _DOMAIN_HINTS)

    def _has_overlap_with_slide_terms(self, query_lower: str, slide_terms: list[str]) -> bool:
        query_tokens = set(self._normalize(query_lower).split())
        slide_tokens: set[str] = set()
        for term in slide_terms:
            slide_tokens.update(self._normalize(str(term)).split())
        ignored = {"ini", "itu", "yang", "dan", "di", "ke"}
        return bool((query_tokens & slide_tokens) - ignored)

    def _should_enrich_with_slide(self, query: str, query_lower: str, slide_terms: list[str]) -> bool:
        if self._is_generic_question(query_lower):
            return False
        if self._mentions_slide(query_lower):
            return True
        if self._has_overlap_with_slide_terms(query_lower, slide_terms):
            return True
        if self._has_domain_hint(query_lower):
            return True
        return bool(self._extract_entities_from_text(query))

    def _is_too_short_and_unspecific(self, query: str, query_lower: str) -> bool:
        tokens = [
            t for t in re.sub(r"[^\w\s]", " ", query_lower).split() if len(t) > 2
        ]
        if len(tokens) > 3:
            return False
        for word in query.split():
            cleaned = re.sub(r"[^\w]", "", word)
            if cleaned and cleaned[0].isupper() and len(cleaned) > 2 and cleaned not in _SKIP_CAPITALIZED:
                return False
        return len(tokens) <= 2

    def _extract_entities_from_history(self, history: list) -> list[str]:
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                return self._extract_entities_from_text(msg.get("content", ""))
        return []

    def _extract_entities_from_text(self, text: str) -> list[str]:
        results: list[str] = []
        seen: set[str] = set()
        for word in text.split():
            cleaned = re.sub(r"[^\w]", "", word)
            if (
                len(cleaned) >= 4
                and cleaned[0].isupper()
                and cleaned not in _SKIP_CAPITALIZED
                and cleaned.lower() not in seen
            ):
                seen.add(cleaned.lower())
                results.append(cleaned)
        return results[:6]
