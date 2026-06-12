import json
import logging
from datetime import datetime
from pathlib import Path

from app.config import Config

logger = logging.getLogger("AICompanion.SessionLogger")

LOGS_DIR = Config.LOGS_DIR


class SessionLogger:
    def __init__(self):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
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
        metrics: dict | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "user": user_input,
            "tenri": response,
            "sources": sources or [],
            "slide": slide_title,
        }
        # Per-turn latency metrics (wait/record/stt/retrieval/llm/tts/playback) for
        # offline analysis via scripts/report_latency.py. Only attached to full
        # response turns; ambient/interruption turns omit it.
        if metrics:
            record["metrics"] = metrics
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write session log: {e}")
