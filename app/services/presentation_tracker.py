import json
import logging
import re
from pathlib import Path

from app.config import BASE_DIR

logger = logging.getLogger("AICompanion.PresentationTracker")

PRESENTATION_DIR = BASE_DIR / "app" / "presentation"
SLIDES_PATH = PRESENTATION_DIR / "slides.json"

_ADVANCE_WORDS = {"lanjut", "next", "selanjutnya", "berikutnya", "maju"}
_BACK_WORDS = {"mundur", "back", "sebelumnya", "kembali", "prev"}
_GOTO_RE = re.compile(r"\bslide\s+(\d+)\b", re.IGNORECASE)
_GOTO_KE_RE = re.compile(r"\bslide\s+ke[-\s]?(\d+)\b", re.IGNORECASE)

_ORDINAL_WORDS: dict[str, int] = {
    "pertama": 1,
    "satu": 1,
    "kesatu": 1,
    "kedua": 2,
    "dua": 2,
    "ketiga": 3,
    "tiga": 3,
    "keempat": 4,
    "empat": 4,
    "kelima": 5,
    "lima": 5,
    "keenam": 6,
    "enam": 6,
    "ketujuh": 7,
    "tujuh": 7,
    "kedelapan": 8,
    "delapan": 8,
    "kesembilan": 9,
    "sembilan": 9,
    "kesepuluh": 10,
    "sepuluh": 10,
    "kesebelas": 11,
    "sebelas": 11,
    "kedua belas": 12,
    "keduabelas": 12,
    "dua belas": 12,
    "duabelas": 12,
}
_ORDINAL_RE = re.compile(
    r"\bslide\s+(?:ke\s+)?(" + "|".join(
        re.escape(word) for word in sorted(_ORDINAL_WORDS, key=len, reverse=True)
    ) + r")\b",
    re.IGNORECASE,
)


class PresentationTracker:
    def __init__(self):
        self._slides: list = []
        self._current_index: int = 0
        self._load()

    def _load(self) -> None:
        if not SLIDES_PATH.exists():
            logger.info("slides.json not found. Presentation mode inactive.")
            return
        try:
            with open(SLIDES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._slides = data if isinstance(data, list) else []
            logger.info(f"Loaded {len(self._slides)} slides.")
        except Exception as e:
            logger.warning(f"Failed to load slides.json: {e}")

    # ------------------------------------------------------------------ state

    def is_active(self) -> bool:
        return bool(self._slides)

    def total(self) -> int:
        return len(self._slides)

    def position(self) -> tuple[int, int]:
        return (self._current_index + 1, len(self._slides))

    def current_slide(self) -> dict | None:
        if not self._slides:
            return None
        return self._slides[self._current_index]

    # ------------------------------------------------------------------ navigation

    def next_slide(self) -> dict | None:
        if not self._slides:
            return None
        if self._current_index < len(self._slides) - 1:
            self._current_index += 1
        return self.current_slide()

    def prev_slide(self) -> dict | None:
        if not self._slides:
            return None
        if self._current_index > 0:
            self._current_index -= 1
        return self.current_slide()

    def go_to(self, slide_number: int) -> dict | None:
        if not self._slides:
            return None
        self._current_index = max(0, min(slide_number - 1, len(self._slides) - 1))
        return self.current_slide()

    # ------------------------------------------------------------------ command detection

    def all_slides(self) -> list:
        return list(self._slides)

    def detect_command(self, text: str) -> str | None:
        """Returns 'next', 'prev', 'goto:N', 'status', 'list', or None."""
        lowered = text.lower().strip()

        # Exact-match info/list commands (checked first to avoid word-level false positives)
        if lowered in {"status", "posisi", "info slide", "slide info"}:
            return "status"
        if lowered in {"list", "slide list", "daftar slide", "semua slide"}:
            return "list"

        match = _GOTO_RE.search(lowered)
        if match:
            return f"goto:{match.group(1)}"
        match = _GOTO_KE_RE.search(lowered)
        if match:
            return f"goto:{match.group(1)}"
        match = _ORDINAL_RE.search(lowered)
        if match:
            ordinal = re.sub(r"\s+", " ", match.group(1).lower()).strip()
            return f"goto:{_ORDINAL_WORDS[ordinal]}"
        words = set(re.split(r"\W+", lowered))
        if words & _ADVANCE_WORDS:
            return "next"
        if words & _BACK_WORDS:
            return "prev"
        return None

    def handle_command(self, command: str) -> dict | None:
        if command == "next":
            return self.next_slide()
        if command == "prev":
            return self.prev_slide()
        if command.startswith("goto:"):
            return self.go_to(int(command.split(":")[1]))
        return None

    # ------------------------------------------------------------------ auto-trigger

    def detect_trigger(self, text: str) -> dict | None:
        """Auto-advance to a slide whose trigger keyword appears in text.
        Only fires if the matching slide is not already current."""
        if not self._slides:
            return None
        lowered = text.lower()
        for i, slide in enumerate(self._slides):
            if i == self._current_index:
                continue
            for trigger in slide.get("triggers", []):
                if trigger.lower() in lowered:
                    self._current_index = i
                    logger.info(
                        f"Auto-triggered slide {i + 1}: '{slide.get('title')}'"
                    )
                    return slide
        return None

    # ------------------------------------------------------------------ context

    def format_context(self, slide: dict | None) -> str:
        if not slide:
            return ""
        current, total = self.position()
        title = slide.get("title", "—")
        topics = slide.get("topics", [])
        notes = slide.get("presenter_notes", "")
        lines = [f"[{current}/{total}] {title}"]
        if topics:
            lines.append(f"Topik: {', '.join(topics)}")
        if notes:
            lines.append(f"Catatan: {notes}")
        return "\n".join(lines)

    def format_narrative_context(self) -> str:
        """Return where the active slide sits in the full presentation arc."""
        if not self.is_active():
            return ""

        current, total = self.position()
        all_slides = self.all_slides()
        current_slide = self.current_slide()
        if not current_slide:
            return ""

        covered_titles = [s.get("title", "?") for s in all_slides[:current - 1]]
        upcoming_titles = [s.get("title", "?") for s in all_slides[current:]]

        parts = [f"Presentasi berjalan: slide {current} dari {total}."]
        if covered_titles:
            parts.append(f"Sudah dibahas: {', '.join(covered_titles)}.")
        parts.append(f"Slide aktif sekarang: {current_slide.get('title', '?')}.")
        if upcoming_titles:
            preview = upcoming_titles[:3]
            ellipsis = "..." if len(upcoming_titles) > 3 else ""
            parts.append(f"Slide berikutnya: {', '.join(preview)}{ellipsis}.")
        return " ".join(parts)

    def get_enriched_query(self, user_input: str) -> str:
        """Append current slide topics to user query for richer BM25 retrieval."""
        slide = self.current_slide()
        if not slide:
            return user_input
        topics = slide.get("topics", [])
        if not topics:
            return user_input
        return f"{user_input} {' '.join(topics)}"
