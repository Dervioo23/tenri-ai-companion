import logging
import queue
import threading
import time

import speech_recognition as sr

from app.config import Config

logger = logging.getLogger("AICompanion.BackgroundListener")


class BackgroundListener:
    """Continuous audio capture using listen_in_background().

    Transcribed utterances are queued for the main interaction loop. A mute gate
    prevents Tenri from hearing her own TTS playback.
    """

    # Ignore room echo shortly after unmute.
    _POST_UNMUTE_BUFFER: float = 2.2

    def __init__(self, speech_service):
        self._speech_service = speech_service
        self._queue: queue.Queue[tuple[str, dict[str, float]]] = queue.Queue(maxsize=5)
        self._muted = threading.Event()
        self._mute_lock = threading.Lock()
        self._mute_started_at: float | None = None
        self._mute_windows: list[tuple[float, float]] = []
        self._unmute_at: float = 0.0
        self._stop_fn = None
        self.available: bool = False
        self.last_wait_seconds: float = 0.0
        self.last_record_seconds: float = 0.0
        self.last_stt_seconds: float = 0.0

    def start(self) -> bool:
        if not self._speech_service.microphone_available:
            logger.info("BackgroundListener: microphone unavailable, skipped.")
            return False

        recognizer = self._speech_service.recognizer
        mic = sr.Microphone(device_index=self._speech_service.device_index)

        def _callback(r: sr.Recognizer, audio: sr.AudioData) -> None:
            try:
                callback_at = time.monotonic()
                record_seconds = self._speech_service.audio_duration_seconds(audio)
                if self._audio_overlaps_mute_window(record_seconds, callback_at):
                    logger.debug(
                        "BackgroundListener: audio overlapped TTS mute window, ignored "
                        "(record=%.2fs).",
                        record_seconds,
                    )
                    return

                stt_started_at = time.monotonic()
                audio = self._speech_service.cap_audio_for_stt(audio)
                record_seconds = round(self._speech_service.audio_duration_seconds(audio), 2)
                if self._speech_service._groq_client:
                    text = self._speech_service._transcribe_with_groq(audio)
                else:
                    text = self._speech_service._transcribe_with_google(audio)
                stt_seconds = round(time.monotonic() - stt_started_at, 2)

                normalized = self._speech_service.normalize_transcription(text)
                if not normalized:
                    return

                metrics = {
                    "record_s": record_seconds,
                    "stt_s": stt_seconds,
                }
                logger.info(
                    "[BackgroundListener] Captured: '%s' (record=%.2fs stt=%.2fs)",
                    normalized,
                    record_seconds,
                    stt_seconds,
                )

                try:
                    self._queue.put_nowait((normalized, metrics))
                except queue.Full:
                    try:
                        self._queue.get_nowait()
                        self._queue.put_nowait((normalized, metrics))
                        logger.debug("BackgroundListener: queue full, oldest dropped.")
                    except queue.Empty:
                        pass

            except sr.UnknownValueError:
                pass
            except Exception as e:
                logger.debug(f"BackgroundListener transcription error: {e}")

        try:
            self._stop_fn = recognizer.listen_in_background(
                mic,
                _callback,
                phrase_time_limit=Config.SPEECH_PHRASE_TIME_LIMIT,
            )
            self.available = True
            logger.info("BackgroundListener started: continuous capture active.")
            return True
        except Exception as e:
            logger.warning(
                f"BackgroundListener failed to start: {e}. "
                "System will fall back to sequential listen_and_transcribe()."
            )
            return False

    def mute(self) -> None:
        """Disable capture during TTS playback."""
        if self.available:
            now = time.monotonic()
            with self._mute_lock:
                if self._mute_started_at is None:
                    self._mute_started_at = now
            self._muted.set()

    def unmute(self) -> None:
        """Re-enable capture after TTS playback."""
        if self.available:
            now = time.monotonic()
            with self._mute_lock:
                if self._mute_started_at is not None:
                    self._mute_windows.append(
                        (self._mute_started_at, now + self._POST_UNMUTE_BUFFER)
                    )
                    self._mute_started_at = None
                self._prune_mute_windows(now)
            self._unmute_at = now
            self._muted.clear()

    def _prune_mute_windows(self, now: float) -> None:
        """Keep only recent windows that can overlap a future captured phrase."""
        retention = max(Config.SPEECH_PHRASE_TIME_LIMIT, 1.0) + self._POST_UNMUTE_BUFFER
        cutoff = now - retention
        self._mute_windows = [window for window in self._mute_windows if window[1] >= cutoff]

    def _audio_overlaps_mute_window(
        self,
        record_seconds: float,
        callback_at: float | None = None,
    ) -> bool:
        """Return True when captured audio intersects TTS mute/suppression time.

        SpeechRecognition invokes the callback after phrase capture. The capture
        interval is therefore approximated as ``callback_at - duration`` through
        ``callback_at``. This catches TTS audio whose callback arrives only after
        Tenri has already been unmuted.
        """
        end_at = callback_at if callback_at is not None else time.monotonic()
        start_at = end_at - max(0.0, record_seconds)

        with self._mute_lock:
            self._prune_mute_windows(end_at)
            windows = list(self._mute_windows)
            if self._mute_started_at is not None:
                windows.append((self._mute_started_at, float("inf")))

        return any(start_at <= window_end and end_at >= window_start
                   for window_start, window_end in windows)

    def get(self, timeout: float = 7.0) -> str | None:
        """Block until an utterance is available or timeout expires."""
        started_at = time.monotonic()
        try:
            text, metrics = self._queue.get(timeout=timeout)
            self.last_wait_seconds = round(time.monotonic() - started_at, 2)
            self.last_record_seconds = metrics.get("record_s", 0.0)
            self.last_stt_seconds = metrics.get("stt_s", 0.0)
            return text
        except queue.Empty:
            self.last_wait_seconds = round(time.monotonic() - started_at, 2)
            self.last_record_seconds = 0.0
            self.last_stt_seconds = 0.0
            return None

    def get_nowait(self) -> str | None:
        """Return a queued utterance immediately, or None."""
        try:
            text, metrics = self._queue.get_nowait()
            self.last_wait_seconds = 0.0
            self.last_record_seconds = metrics.get("record_s", 0.0)
            self.last_stt_seconds = metrics.get("stt_s", 0.0)
            return text
        except queue.Empty:
            return None

    def stop(self) -> None:
        if self._stop_fn:
            try:
                self._stop_fn(wait_for_stop=False)
            except Exception as e:
                logger.debug(f"BackgroundListener stop error: {e}")
            self._stop_fn = None
        self.available = False
        logger.info("BackgroundListener stopped.")
