import re

# Split only on sentence-ending punctuation that is NOT preceded by a digit.
# This prevents "1.", "2.", "3." in numbered lists from being treated as boundaries.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[!?])\s+|(?<=\D\.)\s+")

# Deteksi sisa penanda list bernomor di akhir hasil trim (contoh: "... dijelaskan: 1.")
_TRAILING_LIST_ITEM_RE = re.compile(r"\s+\d+\.?\s*$")

_LEADING_AI_FILLER_RE = re.compile(
    r"^\s*(?:"
    r"tentu saja|"
    r"pertanyaan yang (?:bagus|menarik)|"
    r"oh iya|"
    r"benar sekali|"
    r"tepat sekali|"
    r"saya menangkap poinnya|"
    r"saya memahami maksudnya|"
    r"kalau dipikir-pikir|"
    r"penting untuk dicatat bahwa|"
    r"dengan kata lain|"
    r"memang benar bahwa|"
    r"berikut adalah|"
    r"sebagai ai|"
    r"sebagai asisten(?: virtual)?"
    r")\s*[:,.!-]?\s*",
    re.IGNORECASE,
)

_AI_PHRASE_REPLACEMENTS = (
    (re.compile(r"\bberdasarkan konteks yang diberikan\b", re.IGNORECASE), "dari konteks yang ada"),
    (re.compile(r"\bberdasarkan informasi yang diberikan\b", re.IGNORECASE), "dari informasi yang ada"),
    (re.compile(r"\bdapat disimpulkan bahwa\b", re.IGNORECASE), ""),
    (re.compile(r"\bsebagai kesimpulan\b", re.IGNORECASE), ""),
    (re.compile(r"\bsecara umum\b", re.IGNORECASE), ""),
    (re.compile(r"\boleh karena itu\b", re.IGNORECASE), "jadi"),
    (re.compile(r"\bdengan demikian\b", re.IGNORECASE), "jadi"),
    (re.compile(r"\bnamun demikian\b", re.IGNORECASE), "tapi"),
)

_MARKDOWN_PREFIX_RE = re.compile(r"^\s*(?:[-*â€¢]+|\d+[.)])\s+")
_MULTISPACE_RE = re.compile(r"\s+")

_STERILE_CLOSING_RE = re.compile(
    r"^(?:"
    r"jadi\s+)?(?:intinya|kesimpulannya|sebagai penutup|yang dapat disimpulkan)\s*[:,.-]?\s*",
    re.IGNORECASE,
)

_TRAILING_SOFTENER_RE = re.compile(
    r"\s+(?:secara umum|pada akhirnya|dalam hal ini)\s*\.?$",
    re.IGNORECASE,
)

_TITLE_LIKE_RE = re.compile(
    r"^(?:"
    r"mengenal|pengenalan|definisi|dasar|teknologi|kecerdasan|"
    r"digitalisasi|arsip|penutup|kesimpulan|latar belakang"
    r")(?:\s+\w+){0,5}\.?$",
    re.IGNORECASE,
)

_TITLE_FALSE_POSITIVE_RE = re.compile(
    r"\b(?:bukan|adalah|merupakan|perlu|harus|membutuhkan|butuh|punya)\b",
    re.IGNORECASE,
)

_AGENDA_SENTENCE_RE = re.compile(
    r"^(?:"
    r"apa itu\b|"
    r"bagaimana\b|"
    r"mengapa\b|"
    r"kenapa\b|"
    r"slide ini (?:akan )?(?:membahas|menjelaskan|mengenalkan)\b|"
    r"pada slide ini kita (?:akan )?(?:membahas|melihat|mengenal)\b"
    r")",
    re.IGNORECASE,
)

_FRAGMENT_START_RE = re.compile(
    r"^(?:"
    r"mengenali|mengambil|memahami|membaca|melihat|menjaga|meniru|"
    r"mengolah|menyimpan|menganalisis|membantu|memberi|membuat|"
    r"belajar|berpikir|menjawab"
    r")\b",
    re.IGNORECASE,
)


def _sentence_split(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _clean_spoken_sentence(sentence: str) -> str:
    cleaned = _MARKDOWN_PREFIX_RE.sub("", sentence.strip())
    cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
    cleaned = _STERILE_CLOSING_RE.sub("", cleaned)
    cleaned = _TRAILING_SOFTENER_RE.sub("", cleaned)
    cleaned = _MULTISPACE_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned).strip()
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def _dedupe_sentences(sentences: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for sentence in sentences:
        key = re.sub(r"[^\w\s]", "", sentence.lower())
        key = _MULTISPACE_RE.sub(" ", key).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(sentence)
    return result


def _merge_sentence_fragments(sentences: list[str]) -> list[str]:
    """Merge list-like fragments that were split into standalone sentences."""
    merged: list[str] = []
    for sentence in sentences:
        if (
            merged
            and _FRAGMENT_START_RE.match(sentence)
            and not merged[-1].endswith(("?", "!"))
        ):
            previous = merged.pop().rstrip(".")
            fragment = sentence[0].lower() + sentence[1:]
            merged.append(f"{previous}, {fragment}")
        else:
            merged.append(sentence)
    return merged


def _drop_slide_reading_sentences(sentences: list[str]) -> list[str]:
    """Drop slide-title or agenda openings that make Tenri sound like a reader."""
    if len(sentences) <= 1:
        return sentences

    result = list(sentences)
    while len(result) > 1:
        first = result[0].strip()
        title_like = (
            _TITLE_LIKE_RE.match(first.rstrip(".!?"))
            and not _TITLE_FALSE_POSITIVE_RE.search(first)
        )
        if title_like or _AGENDA_SENTENCE_RE.match(first):
            result.pop(0)
            continue
        break

    return result or sentences


def trim_response(text: str, max_sentences: int = 3) -> str:
    """Trim text to at most max_sentences sentences.

    Splits on sentence-ending punctuation followed by whitespace.
    Digit-period sequences (numbered list items) are NOT treated as boundaries
    so responses like "Ada tiga konsep: 1. AI ... 2. ML ..." are not cut mid-list.
    """
    if not text:
        return text
    sentences = _SENTENCE_SPLIT_RE.split(text.strip())
    trimmed = " ".join(sentences[:max_sentences])
    # Buang penanda list yang menggantung di akhir
    trimmed = _TRAILING_LIST_ITEM_RE.sub("", trimmed).strip()
    return trimmed


def trim_to_character_budget(text: str, max_chars: int = 0) -> str:
    """Trim spoken response to a live-stage character budget.

    Prefer whole sentences. If the first sentence alone is too long, cut at the
    nearest word boundary and finish with punctuation.
    """
    if not text or max_chars <= 0:
        return text

    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    if stripped.startswith(("[Offline Mode]", "[Error]")):
        return stripped

    sentences = _sentence_split(stripped)
    kept: list[str] = []
    for sentence in sentences:
        candidate = " ".join([*kept, sentence]).strip()
        if len(candidate) <= max_chars:
            kept.append(sentence)
            continue
        break

    if kept:
        return " ".join(kept).strip()

    snippet = stripped[:max_chars].rstrip()
    split_at = snippet.rfind(" ")
    if split_at >= max(24, int(max_chars * 0.65)):
        snippet = snippet[:split_at].rstrip()
    snippet = re.sub(r"[\s,;:.-]+$", "", snippet).strip()
    if snippet and snippet[-1] not in ".!?":
        snippet += "."
    return snippet or stripped[:max_chars].strip()


def humanize_tenri_response(text: str) -> str:
    """Remove assistant-like filler so Tenri sounds more present on stage."""
    if not text:
        return text

    stripped = text.strip()
    if stripped.startswith(("[Offline Mode]", "[Error]")):
        return stripped

    cleaned = _LEADING_AI_FILLER_RE.sub("", stripped)
    for pattern, replacement in _AI_PHRASE_REPLACEMENTS:
        cleaned = pattern.sub(replacement, cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    cleaned = re.sub(r"^\s*[:,.!-]\s*", "", cleaned)
    cleaned = cleaned.strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned or stripped


def format_tenri_voice_response(text: str, max_sentences: int | None = None) -> str:
    """Shape Tenri's answer as spoken stage language.

    This is intentionally conservative: it does not invent new facts or rewrite
    meaning. It removes list/markdown residue, trims sterile academic closings,
    deduplicates repeated sentences, and keeps the arc listenable:
    main idea -> support -> closing line.
    """
    if not text:
        return text

    stripped = text.strip()
    if stripped.startswith(("[Offline Mode]", "[Error]")):
        return stripped

    humanized = humanize_tenri_response(stripped)
    spoken_text = re.sub(r"(^|\s)(?:[-*â€¢]+|\d+[.)])\s+", r"\1", humanized)
    sentences = [_clean_spoken_sentence(s) for s in _sentence_split(spoken_text)]
    sentences = _drop_slide_reading_sentences(sentences)
    sentences = _merge_sentence_fragments(sentences)
    sentences = _dedupe_sentences([s for s in sentences if s])

    if max_sentences is not None and max_sentences > 0:
        sentences = sentences[:max_sentences]

    if not sentences:
        return humanized

    # If the model produced many explanatory sentences, keep a stage-friendly arc:
    # first = main idea, second = strongest support, last = closing line.
    if len(sentences) > 3:
        sentences = [sentences[0], sentences[1], sentences[-1]]

    result = " ".join(sentences)
    result = _MULTISPACE_RE.sub(" ", result).strip()
    return result or humanized

