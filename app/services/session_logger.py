import json
import logging
from datetime import datetime
from pathlib import Path

from app.config import BASE_DIR

logger = logging.getLogger("AICompanion.SessionLogger")

LOGS_DIR = BASE_DIR / "logs"


class SessionLogger:
    def __init__(self):
        LOGS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path: Path = LOGS_DIR / f"session_{timestamp}.jsonl"
        logger.info(f"Session log: {self._path}")

    @property
    def path(self) -> Path:
        return self._path

    def log_exchange(
        self,
        user_input: str,
        response: str,
        sources: list[str] | None = None,
        slide_title: str | None = None,
        mode: str = "normal",
    ) -> None:
        record = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "user": user_input,
            "tenri": response,
            "sources": sources or [],
            "slide": slide_title,
        }
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write session log: {e}")
