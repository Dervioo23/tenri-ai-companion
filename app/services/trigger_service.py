import json
import logging
import re

from app.config import BASE_DIR

logger = logging.getLogger("AICompanion.TriggerService")

PRESENTATION_DIR = BASE_DIR / "app" / "presentation"
TRIGGERS_PATH = PRESENTATION_DIR / "triggers.json"


class TriggerService:
    def __init__(self):
        self._triggers: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not TRIGGERS_PATH.exists():
            logger.info("triggers.json not found. Ambient triggers disabled.")
            return
        try:
            with open(TRIGGERS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._triggers = data if isinstance(data, list) else []
            logger.info(f"Loaded {len(self._triggers)} ambient triggers.")
        except Exception as e:
            logger.warning(f"Failed to load triggers.json: {e}")

    # ------------------------------------------------------------------ state

    def is_active(self) -> bool:
        return bool(self._triggers)

    def total(self) -> int:
        return len(self._triggers)

    def all_triggers(self) -> list:
        return list(self._triggers)

    # ------------------------------------------------------------------ detection

    def detect(self, text: str) -> dict | None:
        """Return the first trigger whose whole word/phrase appears in text."""
        lowered = text.lower()
        for trigger in self._triggers:
            for pattern in trigger.get("patterns", []):
                normalized = str(pattern).lower().strip()
                if normalized and re.search(
                    rf"(?<!\w){re.escape(normalized)}(?!\w)",
                    lowered,
                ):
                    logger.info(
                        f"Ambient trigger '{trigger.get('id')}' fired (pattern: '{pattern}')"
                    )
                    return trigger
        return None

    # ------------------------------------------------------------------ prompt

    def build_prompt(self, trigger: dict, slide: dict | None = None) -> str:
        """Build an instruction prompt for Tenri based on the matched trigger.

        If the trigger carries a 'suggested_response_intent', that intent is used
        as the primary instruction with topic/slide context prepended.
        Otherwise falls through to mode-based templates.
        """
        topic = trigger.get("topic", "")
        mode = trigger.get("mode", "comment")
        slide_title = slide.get("title", "") if slide else ""
        intent = trigger.get("suggested_response_intent", "").strip()

        # Intent-first: treat suggested_response_intent as the authoritative instruction
        if intent:
            parts = []
            if topic:
                parts.append(f"Topik: '{topic}'")
            if slide_title:
                parts.append(f"Slide: '{slide_title}'")
            prefix = (", ".join(parts) + ". ") if parts else ""
            return prefix + intent

        # Mode-based templates
        if mode == "comment" and topic:
            base = f"Beri komentar singkat dan natural tentang topik '{topic}'"
            if slide_title:
                base += f" dalam konteks slide '{slide_title}'"
            return base + ". Maksimal 2 kalimat."

        if mode == "question" and topic:
            return (
                f"Ajukan satu pertanyaan retoris singkat yang relevan dengan topik "
                f"'{topic}' untuk audiens. Maksimal 1 kalimat."
            )

        if mode == "memory" and topic:
            base = f"Hubungkan topik '{topic}' dengan konteks presentasi saat ini"
            if slide_title:
                base += f", khususnya slide '{slide_title}'"
            return base + ". Maksimal 2 kalimat."

        if mode == "witness" and topic:
            return (
                f"Berikan kesaksian personal singkat sebagai seseorang yang pernah ada di sana, "
                f"tentang '{topic}'. Maksimal 2 kalimat."
            )

        if mode == "gentle_objection":
            base = f"Sanggah dengan sangat lembut tentang '{topic}'" if topic else "Sanggah dengan sangat lembut"
            return (
                base + ". Gunakan frasa seperti 'tidak begitu ji' atau "
                "'saya perlu sedikit tidak setuju'. Maksimal 2 kalimat."
            )

        if mode == "debate":
            base = f"Kamu punya konteks dari knowledge base tentang '{topic}'." if topic else \
                   "Kamu punya konteks dari knowledge base."
            return (
                base + " Gunakan fakta itu untuk menantang atau memperkuat klaim yang baru "
                "disampaikan. Sebutkan dari mana data itu. Maksimal 2 kalimat. Spesifik."
            )

        if mode == "clarification":
            base = f"Klarifikasi singkat tentang '{topic}'" if topic else "Berikan klarifikasi singkat"
            return base + " tanpa menghentikan alur presentasi. Maksimal 2 kalimat."

        if mode == "short_comment":
            base = f"Beri komentar sangat singkat tentang '{topic}'" if topic else "Beri komentar sangat singkat"
            return base + ". Jika tidak benar-benar perlu, lebih baik diam. Maksimal 1 kalimat."

        if mode == "grounding_check":
            base = f"Akui batas pengetahuanmu tentang '{topic}' dengan lembut" if topic else "Akui batas pengetahuanmu dengan lembut"
            return base + ". Jangan mengarang fakta. Maksimal 2 kalimat."

        if mode == "closing_memory":
            base = f"Beri satu kalimat penutup yang berbobot tentang ingatan dan tanggung jawab manusia, terkait '{topic}'." if topic else "Beri satu kalimat penutup yang berbobot tentang ingatan dan tanggung jawab manusia."
            return base

        _fallbacks = {
            "comment":    "Beri komentar singkat dan natural tentang situasi saat ini. Maksimal 2 kalimat.",
            "question":   "Ajukan satu pertanyaan retoris singkat untuk audiens. Maksimal 1 kalimat.",
            "memory":     "Hubungkan konteks saat ini dengan topik yang sebelumnya dibahas. Maksimal 2 kalimat.",
            "witness":    "Berikan kesaksian personal singkat sebagai seseorang yang pernah menunggu. Maksimal 2 kalimat.",
            "gentle_objection": "Sanggah dengan lembut menggunakan 'tidak begitu ji'. Maksimal 2 kalimat.",
            "debate": "Gunakan konteks yang kamu punya untuk menantang klaim. Spesifik. Maksimal 2 kalimat.",
            "clarification":    "Berikan klarifikasi singkat. Maksimal 2 kalimat.",
            "short_comment":    "Beri komentar sangat singkat jika perlu. Maksimal 1 kalimat.",
            "grounding_check":  "Akui batas pengetahuanmu. Jangan mengarang fakta. Maksimal 2 kalimat.",
            "closing_memory":   "Beri satu kalimat penutup tentang ingatan dan tanggung jawab manusia.",
        }
        return _fallbacks.get(mode, "Beri komentar singkat. Maksimal 2 kalimat.")
