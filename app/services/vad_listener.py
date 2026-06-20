"""VadListener — continuous capture with Silero VAD endpointing.

Drop-in replacement for ``BackgroundListener``: same public surface
(``start/stop/mute/unmute/get/get_nowait/available`` + ``last_*_seconds``) so
``InteractionLoop`` can use either without changes.

Pipeline: PyAudio mic stream -> 32 ms frames -> Silero probability ->
SpeechEndpointer -> on utterance end, transcribe via the shared SpeechService
(Groq Whisper or Google) -> push normalized text onto a queue.

Unlike the energy-gated ``listen_in_background``, endpointing here is decided by
the neural model, so ``pause_threshold`` / ``adjust_for_ambient_noise`` / the
room-dependent energy gate no longer apply.
"""

from __future__ import annotations

import logging
import queue
import threading
import time

import numpy as np
import speech_recognition as sr

from app.config import Config
from app.services.silero_vad import (
    FRAME_MS,
    FRAME_SAMPLES,
    SAMPLE_RATE,
    SileroVAD,
    SpeechEndpointer,
)

logger = logging.getLogger("AICompanion.VadListener")


class VadListener:
    # Ignore room echo shortly after unmute (mirrors BackgroundListener).
    _POST_UNMUTE_BUFFER: float = 2.2

    def __init__(self, speech_service):
        self._speech_service = speech_service
        self._queue: queue.Queue[tuple[str, dict[str, float]]] = queue.Queue(maxsize=5)
        self._muted = threading.Event()
        self._unmute_at: float = 0.0
        self._stop = threading.Event()
        self._first_frame = threading.Event()
        self._thread: threading.Thread | None = None
        self._pa = None
        self._stream = None
        self.available: bool = False

        self.last_wait_seconds: float = 0.0
        self.last_record_seconds: float = 0.0
        self.last_stt_seconds: float = 0.0

        # Load the Silero model up front so the caller can fall back cleanly.
        self._vad: SileroVAD | None = None
        try:
            if not Config.SILERO_VAD_MODEL_PATH.exists():
                logger.warning("Silero model not found at %s", Config.SILERO_VAD_MODEL_PATH)
            else:
                self._vad = SileroVAD(Config.SILERO_VAD_MODEL_PATH)
        except Exception as e:
            logger.warning("Silero VAD unavailable: %s", e)
            self._vad = None

    @property
    def usable(self) -> bool:
        """True when the model loaded and a microphone exists."""
        return self._vad is not None and self._speech_service.microphone_available

    def _new_endpointer(self) -> SpeechEndpointer:
        return SpeechEndpointer(
            start_prob=Config.SILERO_VAD_START_PROB,
            end_prob=Config.SILERO_VAD_END_PROB,
            hangover_ms=Config.SILERO_VAD_HANGOVER_MS,
            min_speech_ms=Config.SILERO_VAD_MIN_SPEECH_MS,
            preroll_ms=Config.SILERO_VAD_PREROLL_MS,
            max_speech_ms=int(Config.SPEECH_PHRASE_TIME_LIMIT * 1000),
            frame_ms=FRAME_MS,
        )

    def start(self) -> bool:
        if not self.usable:
            logger.info("VadListener not usable (model or mic missing); skipped.")
            return False
        try:
            import pyaudio
        except Exception as e:
            logger.warning("PyAudio unavailable, VadListener disabled: %s", e)
            return False

        device_index = self._speech_service.device_index
        try:
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=FRAME_SAMPLES,
                input_device_index=device_index if device_index is not None else None,
            )
        except Exception as e:
            logger.warning("VadListener failed to open mic stream: %s", e)
            self._cleanup_audio()
            return False

        # Set available SYNCHRONOUSLY before returning so the main loop never races
        # ahead and falls back to sequential capture (which would fight for the mic).
        self.available = True
        self._stop.clear()
        self._first_frame.clear()
        self._thread = threading.Thread(target=self._capture_loop, name="vad-capture", daemon=True)
        self._thread.start()

        if not self._first_frame.wait(timeout=Config.SILERO_VAD_STARTUP_TIMEOUT):
            logger.warning(
                "VadListener stream opened but delivered no audio frame within %.1fs; "
                "falling back to BackgroundListener.",
                Config.SILERO_VAD_STARTUP_TIMEOUT,
            )
            self._stop.set()
            self._cleanup_audio()
            self._thread.join(timeout=1.0)
            self._thread = None
            self.available = False
            return False

        logger.info("VadListener started: Silero endpointing active.")
        return True

    # ------------------------------------------------------------------ capture

    def _capture_loop(self) -> None:
        endpointer = self._new_endpointer()
        debug = Config.SILERO_VAD_DEBUG
        hb_frames = 0
        hb_max_prob = 0.0
        hb_max_amp = 0
        hb_read_errors = 0
        hb_muted = 0
        try:
            while not self._stop.is_set():
                try:
                    data = self._stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                except Exception as e:
                    logger.debug("VadListener read error: %s", e)
                    hb_read_errors += 1
                    if self._stop.is_set():
                        break
                    continue

                self._first_frame.set()

                # Mute gate: drop frames during TTS playback + post-unmute echo window,
                # and discard any half-collected utterance so Tenri never hears herself.
                if self._muted.is_set() or (time.monotonic() - self._unmute_at) < self._POST_UNMUTE_BUFFER:
                    hb_muted += 1
                    if endpointer.collecting:
                        endpointer.reset()
                        self._vad.reset()
                    continue

                frame = np.frombuffer(data, dtype=np.int16)
                prob = self._vad.probability(frame)

                if debug:
                    hb_frames += 1
                    if prob > hb_max_prob:
                        hb_max_prob = prob
                    amp = int(np.abs(frame).max()) if frame.size else 0
                    if amp > hb_max_amp:
                        hb_max_amp = amp
                    # ~3 s heartbeat (100 frames * 32 ms) so we can see live whether
                    # the mic delivers audio and whether Silero crosses start_prob.
                    if (hb_frames + hb_muted + hb_read_errors) >= 100:
                        logger.info(
                            "[VAD-DEBUG] frames=%d muted=%d read_err=%d | max_prob=%.3f "
                            "max_amp=%d start_prob=%.2f collecting=%s",
                            hb_frames, hb_muted, hb_read_errors, hb_max_prob,
                            hb_max_amp, endpointer.start_prob, endpointer.collecting,
                        )
                        hb_frames = hb_muted = hb_read_errors = 0
                        hb_max_prob = 0.0
                        hb_max_amp = 0

                utterance = endpointer.push(prob, frame)
                if utterance is not None:
                    self._vad.reset()
                    self._handle_utterance(utterance)
        finally:
            logger.info("VadListener capture loop stopped.")

    def _handle_utterance(self, frames: list) -> None:
        stt_started = time.monotonic()
        pcm = np.concatenate(frames).astype(np.int16).tobytes()
        record_seconds = round(len(pcm) / float(SAMPLE_RATE * 2), 2)
        audio = sr.AudioData(pcm, SAMPLE_RATE, 2)

        try:
            if self._speech_service._groq_client:
                text = self._speech_service._transcribe_with_groq(
                    audio,
                    min_duration_seconds=Config.AUTO_LISTEN_MIN_AUDIO_SECONDS,
                )
            else:
                text = self._speech_service._transcribe_with_google(audio)
        except sr.UnknownValueError:
            logger.info(
                "VadListener rejected an utterance during audio/STT quality "
                "checks (record=%.2fs).",
                record_seconds,
            )
            return
        except Exception as e:
            logger.debug("VadListener transcription error: %s", e)
            return

        normalized = self._speech_service.normalize_transcription(text)
        if not normalized:
            return

        stt_seconds = round(time.monotonic() - stt_started, 2)
        metrics = {"record_s": record_seconds, "stt_s": stt_seconds}
        logger.info(
            "[VadListener] Captured: '%s' (record=%.2fs stt=%.2fs)",
            normalized, record_seconds, stt_seconds,
        )
        try:
            self._queue.put_nowait((normalized, metrics))
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait((normalized, metrics))
            except queue.Empty:
                pass

    # ------------------------------------------------------------------ control

    def mute(self) -> None:
        if self.available:
            self._muted.set()

    def unmute(self) -> None:
        if self.available:
            self._unmute_at = time.monotonic()
            self._muted.clear()

    def get(self, timeout: float = 7.0) -> str | None:
        started = time.monotonic()
        try:
            text, metrics = self._queue.get(timeout=timeout)
            self.last_wait_seconds = round(time.monotonic() - started, 2)
            self.last_record_seconds = metrics.get("record_s", 0.0)
            self.last_stt_seconds = metrics.get("stt_s", 0.0)
            return text
        except queue.Empty:
            self.last_wait_seconds = round(time.monotonic() - started, 2)
            self.last_record_seconds = 0.0
            self.last_stt_seconds = 0.0
            return None

    def get_nowait(self) -> str | None:
        try:
            text, metrics = self._queue.get_nowait()
            self.last_wait_seconds = 0.0
            self.last_record_seconds = metrics.get("record_s", 0.0)
            self.last_stt_seconds = metrics.get("stt_s", 0.0)
            return text
        except queue.Empty:
            return None

    def _cleanup_audio(self) -> None:
        try:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
        except Exception:
            pass
        self._stream = None
        try:
            if self._pa is not None:
                self._pa.terminate()
        except Exception:
            pass
        self._pa = None

    def stop(self) -> None:
        self._stop.set()
        # Closing the stream first releases a thread blocked inside stream.read().
        self._cleanup_audio()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.available = False
        logger.info("VadListener stopped.")
