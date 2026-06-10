import logging
import time

logger = logging.getLogger("AICompanion.InterruptionPolicy")

_MODE_MAP: dict[str, str] = {
    "slide_change": "comment",
    "slide_change_with_notes": "correction",
    "audience_increase": "question",
    "audience_decrease": "comment",
}


class InterruptionPolicy:
    def __init__(
        self,
        cooldown_seconds: int = 90,
        max_per_session: int = 8,
        enabled: bool = True,
    ):
        self.cooldown_seconds = cooldown_seconds
        self.max_per_session = max_per_session
        self.enabled = enabled
        self._last_interruption: float | None = None
        self._session_count: int = 0
        self._trigger_last_fired: dict[str, float] = {}

    # ------------------------------------------------------------------ checks

    def can_interrupt(self) -> bool:
        if not self.enabled:
            return False
        if self._session_count >= self.max_per_session:
            return False
        if self._last_interruption is None:
            return True
        return (time.time() - self._last_interruption) >= self.cooldown_seconds

    def record_interruption(self) -> None:
        self._last_interruption = time.time()
        self._session_count += 1
        logger.info(f"Interruption recorded. Session total: {self._session_count}")

    def can_interrupt_trigger(self, trigger_id: str, cooldown_seconds: int) -> bool:
        """Check per-trigger cooldown independently of the global cooldown.
        Still respects the global session max and enabled flag."""
        if not self.enabled:
            return False
        if self._session_count >= self.max_per_session:
            return False
        last = self._trigger_last_fired.get(trigger_id)
        if last is None:
            return True
        return (time.time() - last) >= cooldown_seconds

    def record_trigger_interruption(self, trigger_id: str) -> None:
        self._trigger_last_fired[trigger_id] = time.time()
        self._session_count += 1
        logger.info(f"Trigger '{trigger_id}' fired. Session total: {self._session_count}")

    def seconds_until_next(self) -> float:
        if self._last_interruption is None:
            return 0.0
        elapsed = time.time() - self._last_interruption
        return max(0.0, self.cooldown_seconds - elapsed)

    # ------------------------------------------------------------------ mode & prompt

    def suggest_mode(self, trigger: str) -> str:
        return _MODE_MAP.get(trigger, "comment")

    def build_prompt(self, mode: str, slide: dict | None = None) -> str:
        title = slide.get("title", "") if slide else ""
        notes = slide.get("presenter_notes", "") if slide else ""

        if mode == "comment" and title:
            return (
                f"Beri komentar singkat dan natural tentang slide aktif: '{title}'. "
                "Maksimal 2 kalimat."
            )
        if mode == "question" and title:
            return (
                f"Ajukan satu pertanyaan retoris singkat yang relevan dengan slide "
                f"'{title}' untuk audiens. Maksimal 1 kalimat."
            )
        if mode == "correction" and notes:
            return (
                f"Ingatkan presenter secara halus tentang catatan ini: '{notes}'. "
                "Maksimal 2 kalimat."
            )
        if mode == "correction" and title:
            return (
                f"Beri catatan singkat yang relevan untuk slide '{title}'. "
                "Maksimal 2 kalimat."
            )
        if mode == "memory" and title:
            return (
                f"Hubungkan slide '{title}' dengan topik yang sebelumnya dibahas, "
                "secara singkat. Maksimal 2 kalimat."
            )

        _fallbacks = {
            "comment":    "Beri komentar singkat dan natural tentang situasi presentasi. Maksimal 2 kalimat.",
            "question":   "Ajukan satu pertanyaan retoris singkat untuk audiens. Maksimal 1 kalimat.",
            "correction": "Beri catatan singkat yang relevan untuk presenter. Maksimal 2 kalimat.",
            "memory":     "Hubungkan konteks saat ini dengan topik yang sebelumnya dibahas. Maksimal 2 kalimat.",
        }
        return _fallbacks.get(mode, "Beri komentar singkat dan natural. Maksimal 2 kalimat.")
