"""Input capture boundary for voice and text modes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class CaptureStatus(str, Enum):
    OK = "ok"
    NO_INPUT = "no_input"
    TIMEOUT = "timeout"
    UNKNOWN_AUDIO = "unknown_audio"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class CaptureResult:
    text: str = ""
    status: CaptureStatus = CaptureStatus.NO_INPUT
    source: str = "unknown"
    detail: str = ""
    wait_seconds: float = 0.0
    record_seconds: float = 0.0
    stt_seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status is CaptureStatus.OK and bool(self.text.strip())


class CaptureStage:
    """Capture one utterance without knowing routing, UI, or response logic."""

    def __init__(self, speech_service, listener, text_input: Callable[[str], str] = input):
        self.speech_service = speech_service
        self.listener = listener
        self._text_input = text_input

    def capture(
        self,
        *,
        voice_enabled: bool,
        push_to_talk: bool,
        timeout: float,
        before_push_capture: Callable[[], None] | None = None,
    ) -> CaptureResult:
        if voice_enabled and self.speech_service.microphone_available:
            if push_to_talk:
                if before_push_capture:
                    before_push_capture()
                text, success = self.speech_service.listen_and_transcribe()
                return self._speech_result(text, success, source="push_to_talk")

            if self.listener.available:
                text = self.listener.get(timeout=timeout)
                if text is None:
                    return CaptureResult(
                        status=CaptureStatus.NO_INPUT,
                        source="background_listener",
                        wait_seconds=self.listener.last_wait_seconds,
                    )
                return CaptureResult(
                    text=text,
                    status=CaptureStatus.OK,
                    source="background_listener",
                    wait_seconds=self.listener.last_wait_seconds,
                    record_seconds=self.listener.last_record_seconds,
                    stt_seconds=self.listener.last_stt_seconds,
                )

            text, success = self.speech_service.listen_and_transcribe()
            return self._speech_result(text, success, source="sequential_voice")

        text = self._text_input(">> ").strip()
        return CaptureResult(
            text=text,
            status=CaptureStatus.OK if text else CaptureStatus.NO_INPUT,
            source="text",
        )

    def _speech_result(self, text: str, success: bool, source: str) -> CaptureResult:
        status = CaptureStatus.OK
        if not success:
            if text == "[TIMEOUT]":
                status = CaptureStatus.TIMEOUT
            elif text == "[UNKNOWN_AUDIO]":
                status = CaptureStatus.UNKNOWN_AUDIO
            else:
                status = CaptureStatus.ERROR
        return CaptureResult(
            text=text if success else "",
            status=status,
            source=source,
            detail="" if success else text,
            wait_seconds=self.speech_service.last_wait_seconds,
            record_seconds=self.speech_service.last_record_seconds,
            stt_seconds=self.speech_service.last_transcribe_seconds,
        )
