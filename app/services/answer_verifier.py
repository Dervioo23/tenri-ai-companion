import re
import logging

import numpy as np

logger = logging.getLogger("AICompanion.AnswerVerifier")

_GROUNDING_THRESHOLD = 0.25
_FALLBACK_RESPONSE = "Tenri tidak punya informasi spesifik untuk ini."
_PUNCT_RE = re.compile(r"[^\w\s]")
_MIN_TOKEN_LENGTH = 2
_OFFLINE_PREFIX = "[Offline Mode]"
_TOKEN_STOPWORDS: frozenset[str] = frozenset({
    "apa", "apakah", "itu", "ini", "yang", "dan", "atau", "di", "ke", "dari",
    "untuk", "dengan", "bisa", "tolong", "coba", "saya", "kamu", "anda",
    "kita", "kami", "mereka", "lebih", "jelaskan", "ceritakan", "gimana",
    "bagaimana", "kenapa", "mengapa", "siapa", "kapan", "berapa", "tentang",
    "soal", "hal", "tersebut", "tadi", "barusan", "adalah", "dalam", "pada",
    "sebagai", "oleh", "karena", "jadi", "tidak", "bukan", "akan", "dapat",
})


def _tokenize(text: str) -> list[str]:
    cleaned = _PUNCT_RE.sub(" ", text.lower())
    return [
        t for t in cleaned.split()
        if len(t) > _MIN_TOKEN_LENGTH and t not in _TOKEN_STOPWORDS
    ]


def _cosine_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Bag-of-words cosine similarity between two token lists.

    Builds a shared vocabulary, constructs term-frequency vectors, and returns
    the cosine similarity.  Returns 0.0 when either vector is zero-length.
    """
    vocab = {token: i for i, token in enumerate(set(tokens_a + tokens_b))}
    if not vocab:
        return 0.0

    def _bow(tokens: list[str]) -> np.ndarray:
        vec = np.zeros(len(vocab), dtype=np.float32)
        for t in tokens:
            if t in vocab:
                vec[vocab[t]] += 1.0
        return vec

    vec_a = _bow(tokens_a)
    vec_b = _bow(tokens_b)

    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


class AnswerVerifier:
    """Grounding check: verifies that Tenri's response is supported by retrieved context.

    Uses bag-of-words cosine similarity (numpy only — no extra dependencies).
    If similarity < threshold and context was provided, the response is considered
    generative (not grounded) and is replaced with a safe fallback.

    The check is skipped when:
    - context_str is empty (no RAG chunks were retrieved)
    - response_text is empty or already the fallback text
    - response_text starts with "[Offline Mode]" (Groq rate-limit fallback)

    Threshold defaults to _GROUNDING_THRESHOLD (0.25) and is tunable via the
    constructor. A near-grounded relaxation lets responses with >=2 shared terms
    pass slightly below the threshold (see check()).
    """

    def __init__(self, threshold: float = _GROUNDING_THRESHOLD) -> None:
        self.threshold = threshold

    def check(
        self,
        response_text: str,
        context_str: str,
    ) -> tuple[str, bool]:
        """Check whether response_text is grounded in context_str.

        Args:
            response_text: Tenri's generated response (after trim_response).
            context_str:   Formatted context from RetrievalService.format_context().

        Returns:
            (text_to_use, was_overridden):
              - text_to_use is either the original response or the fallback string.
              - was_overridden is True when grounding failed and text was replaced.
        """
        if not context_str or not response_text:
            return response_text, False

        if response_text == _FALLBACK_RESPONSE:
            return response_text, False

        if response_text.startswith(_OFFLINE_PREFIX):
            return response_text, False

        resp_tokens = _tokenize(response_text)
        ctx_tokens = _tokenize(context_str)

        if not resp_tokens or not ctx_tokens:
            return response_text, False

        similarity = _cosine_similarity(resp_tokens, ctx_tokens)
        shared_terms = set(resp_tokens) & set(ctx_tokens)
        logger.debug("Grounding similarity: %.3f (threshold: %.1f)", similarity, self.threshold)

        near_grounded = (
            self.threshold <= 0.5
            and len(shared_terms) >= 2
            and similarity >= self.threshold * 0.75
        )

        if similarity < self.threshold and not near_grounded:
            logger.warning(
                "Low grounding (%.3f < %.1f) — respons mungkin generatif. "
                "Response: '%s...'",
                similarity,
                self.threshold,
                response_text[:60],
            )
            return _FALLBACK_RESPONSE, True

        return response_text, False
