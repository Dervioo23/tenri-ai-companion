"""Privacy-safe JSONL tracing for pipeline stage events."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from app.config import Config
from app.pipeline.events import PipelineEvent

logger = logging.getLogger("AICompanion.PipelineTrace")

_SENSITIVE_KEYS = frozenset({
    "text",
    "transcript",
    "user",
    "user_input",
    "response",
    "prompt",
})


class PipelineTraceWriter:
    def __init__(self, enabled: bool | None = None, logs_dir: Path | None = None) -> None:
        self.enabled = Config.PIPELINE_TRACE_ENABLED if enabled is None else enabled
        self._file = None
        self._path: Path | None = None
        if not self.enabled:
            return
        directory = logs_dir or Config.LOGS_DIR
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self._path = directory / f"pipeline_{timestamp}.jsonl"
        try:
            self._file = open(self._path, "a", encoding="utf-8")
        except OSError as error:
            self.enabled = False
            logger.warning("Pipeline trace disabled: %s", error)

    @property
    def path(self) -> Path | None:
        return self._path

    def handle(self, event: PipelineEvent) -> None:
        if not self.enabled or self._file is None:
            return
        payload = {
            key: value
            for key, value in event.payload.items()
            if key.lower() not in _SENSITIVE_KEYS
        }
        record = {
            "timestamp": datetime.now().isoformat(),
            "event": event.type.value,
            "turn_id": event.turn_id,
            "monotonic": round(event.created_at, 6),
            "payload": payload,
        }
        try:
            self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._file.flush()
        except OSError as error:
            logger.warning("Pipeline trace write failed: %s", error)

    def close(self) -> None:
        if self._file is not None:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None
