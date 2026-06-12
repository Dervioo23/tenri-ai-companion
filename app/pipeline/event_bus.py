"""Bounded event bus used to decouple Tenri runtime stages."""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable

from app.pipeline.events import PipelineEvent, PipelineEventType

logger = logging.getLogger("AICompanion.PipelineEventBus")

EventHandler = Callable[[PipelineEvent], None]
_STOP = object()


class PipelineEventBus:
    """Dispatch events on one worker while isolating subscriber failures."""

    def __init__(self, max_queue_size: int = 128) -> None:
        self._queue: queue.Queue[PipelineEvent | object] = queue.Queue(
            maxsize=max(8, max_queue_size)
        )
        self._subscribers: dict[PipelineEventType | None, list[EventHandler]] = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.dropped_events = 0

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def subscribe(
        self,
        event_type: PipelineEventType | None,
        handler: EventHandler,
    ) -> None:
        """Subscribe to one event type; ``None`` receives every event."""
        with self._lock:
            handlers = self._subscribers.setdefault(event_type, [])
            if handler not in handlers:
                handlers.append(handler)

    def unsubscribe(
        self,
        event_type: PipelineEventType | None,
        handler: EventHandler,
    ) -> None:
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            try:
                handlers.remove(handler)
            except ValueError:
                pass

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._dispatch_loop,
            name="tenri-pipeline-events",
            daemon=True,
        )
        self._thread.start()

    def publish(self, event: PipelineEvent) -> bool:
        """Enqueue an event without blocking the live presentation loop."""
        if not self.running:
            return False
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            self.dropped_events += 1
            logger.warning(
                "Pipeline event queue full; dropping %s (dropped=%d).",
                event.type.value,
                self.dropped_events,
            )
            return False

    def flush(self, timeout: float = 2.0) -> bool:
        deadline = time.monotonic() + max(0.0, timeout)
        while self._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.005)
        return self._queue.unfinished_tasks == 0

    def stop(self, drain: bool = True, timeout: float = 2.0) -> None:
        thread = self._thread
        if not thread:
            return
        if drain:
            self.flush(timeout=timeout)
        self._stop.set()
        try:
            self._queue.put_nowait(_STOP)
        except queue.Full:
            pass
        thread.join(timeout=timeout)
        self._thread = None

    def _dispatch_loop(self) -> None:
        while True:
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                if self._stop.is_set():
                    return
                continue
            try:
                if item is _STOP:
                    return
                self._dispatch(item)
            finally:
                self._queue.task_done()

    def _dispatch(self, event: PipelineEvent) -> None:
        with self._lock:
            handlers = [
                *self._subscribers.get(event.type, []),
                *self._subscribers.get(None, []),
            ]
        for handler in handlers:
            try:
                handler(event)
            except Exception as error:
                logger.warning(
                    "Pipeline subscriber failed for %s: %s",
                    event.type.value,
                    error,
                )
