import logging
import re

logger = logging.getLogger("AICompanion.Retrieval")

_PUNCT_RE = re.compile(r"[^\w\s]")

_TOKEN_STOPWORDS: frozenset[str] = frozenset({
    "apa", "apakah", "itu", "ini", "yang", "dan", "atau", "di", "ke", "dari",
    "untuk", "dengan", "bisa", "tolong", "coba", "saya", "kamu", "anda",
    "kita", "kami", "mereka", "lebih", "jelaskan", "ceritakan", "gimana",
    "bagaimana", "kenapa", "mengapa", "siapa", "kapan", "berapa", "tentang",
    "soal", "hal", "tersebut", "tadi", "barusan", "dong", "lagi",
})


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    return [t for t in text.split() if t]


def _content_tokens(text: str) -> list[str]:
    return [t for t in _tokenize(text) if len(t) > 2 and t not in _TOKEN_STOPWORDS]


class RetrievalService:
    def __init__(self, chunks: list):
        self._chunks = chunks
        self._bm25 = None
        if chunks:
            self._build_index(chunks)

    def _build_index(self, chunks: list) -> None:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank-bm25 not installed. Retrieval disabled.")
            return

        corpus = [_tokenize(chunk.get("text", "")) for chunk in chunks]
        self._bm25 = BM25Okapi(corpus)
        logger.info(f"BM25 index built with {len(chunks)} chunks.")

    def search(self, query: str, top_k: int = 3, min_score: float = 0.0) -> list:
        if self._bm25 is None or not self._chunks:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        query_content = set(_content_tokens(query))
        scores = self._bm25.get_scores(tokens)
        scored = [
            (float(score), chunk)
            for score, chunk in zip(scores, self._chunks)
            if float(score) > min_score
        ]
        scored.sort(key=lambda item: item[0], reverse=True)

        results = []
        for score, chunk in scored[:top_k]:
            decorated = dict(chunk)
            searchable = " ".join([
                str(chunk.get("title", "")),
                str(chunk.get("heading", "")),
                str(chunk.get("text", "")),
            ])
            chunk_content = set(_content_tokens(searchable))
            decorated["_retrieval_score"] = round(score, 4)
            decorated["_query_overlap"] = len(query_content & chunk_content)
            results.append(decorated)

        if results:
            logger.info(
                f"Retrieved {len(results)} chunks for query length {len(query)} chars."
            )
        return results

    def has_strong_match(self, chunks: list, min_overlap: int = 1) -> bool:
        """Return True when retrieved chunks share enough content words with query."""
        return any(chunk.get("_query_overlap", 0) >= min_overlap for chunk in chunks or [])

    def format_context(self, chunks: list) -> str:
        if not chunks:
            return ""

        lines = []
        for i, chunk in enumerate(chunks, 1):
            source_id = chunk.get("source_id", "unknown-source")
            version = chunk.get("version", "")
            source_type = chunk.get("type", "")
            title = chunk.get("title", "Sumber")
            heading = chunk.get("heading", "")
            text = chunk.get("text", "")
            score = chunk.get("_retrieval_score")
            overlap = chunk.get("_query_overlap")

            source_meta = source_id
            if version:
                source_meta += f"@{version}"
            if source_type:
                source_meta += f" / {source_type}"

            header = f"[{i}] {title} | sumber: {source_meta}"
            if score is not None:
                header += f" | skor: {score}"
            if overlap is not None:
                header += f" | overlap: {overlap}"
            if heading:
                header += f" - {heading}"

            lines.append(f"{header}\n{text}")
        return "\n\n".join(lines)
