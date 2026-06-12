"""Silero VAD (v5) wrapper + speech endpointer.

Two pieces, deliberately separated so the endpointing logic is unit-testable
without an audio device or the ONNX model:

- ``SileroVAD``   : thin onnxruntime wrapper. Feed one 32 ms / 512-sample frame
                    (int16 @ 16 kHz), get back a speech probability in [0, 1].
- ``SpeechEndpointer`` : pure state machine. Feed (probability, frame); it emits
                    the collected frames when an utterance ends (after a hangover
                    of trailing silence), or ``None`` while still listening.

This replaces the energy-threshold endpointing of SpeechRecognition's
``listen_in_background``: speech start/stop is decided by the neural model, not
by a room-dependent energy gate.
"""

from __future__ import annotations

import logging
from collections import deque

import numpy as np

logger = logging.getLogger("AICompanion.SileroVAD")

SAMPLE_RATE = 16000
# Silero v5 requires exactly 512 samples per call at 16 kHz (32 ms).
FRAME_SAMPLES = 512
FRAME_MS = FRAME_SAMPLES * 1000 // SAMPLE_RATE  # 32
# Silero v5 also prepends 64 samples of context (the tail of the previous frame)
# to each call, so the model actually sees 576 samples. Omitting this context
# makes the model classify even loud, clear speech as silence (prob ~0.0).
CONTEXT_SAMPLES = 64


class SileroVAD:
    """onnxruntime wrapper around the Silero VAD v5 model."""

    def __init__(self, model_path) -> None:
        import onnxruntime as ort  # imported lazily so the app runs without it

        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self._session = ort.InferenceSession(
            str(model_path), sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self._sr = np.array(SAMPLE_RATE, dtype=np.int64)
        self.reset()
        logger.info("Silero VAD model loaded: %s", model_path)

    def reset(self) -> None:
        """Clear the recurrent state and rolling context between utterances."""
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros(CONTEXT_SAMPLES, dtype=np.float32)

    def probability(self, frame_int16: np.ndarray) -> float:
        """Speech probability for one 512-sample int16 frame.

        The model input is the 64-sample context carried over from the previous
        frame followed by this frame's 512 samples (576 total). Without this
        context Silero v5 reports ~0.0 for every frame, including clear speech.
        """
        audio = frame_int16.astype(np.float32) / 32768.0
        x = np.concatenate((self._context, audio)).reshape(1, -1)
        out, self._state = self._session.run(
            None, {"input": x, "state": self._state, "sr": self._sr}
        )
        self._context = audio[-CONTEXT_SAMPLES:]
        return float(out[0][0])


class SpeechEndpointer:
    """Pure endpointing state machine over a stream of (probability, frame).

    Hysteresis: opens at ``start_prob``, closes after ``hangover_ms`` of frames
    below ``end_prob``. A pre-roll of recent frames is prepended so the onset of
    speech is not clipped. Utterances shorter than ``min_speech_ms`` are dropped.
    """

    def __init__(
        self,
        start_prob: float = 0.5,
        end_prob: float = 0.35,
        hangover_ms: int = 500,
        min_speech_ms: int = 250,
        preroll_ms: int = 200,
        max_speech_ms: int = 12000,
        frame_ms: int = FRAME_MS,
    ) -> None:
        self.start_prob = start_prob
        self.end_prob = end_prob
        self._frame_ms = max(1, frame_ms)
        self._hangover_frames = max(1, hangover_ms // self._frame_ms)
        self._min_speech_frames = max(1, min_speech_ms // self._frame_ms)
        self._max_frames = max(1, max_speech_ms // self._frame_ms)
        self._preroll: deque = deque(maxlen=max(1, preroll_ms // self._frame_ms))
        self.reset()

    def reset(self) -> None:
        self._collecting = False
        self._frames: list = []
        self._silence_run = 0
        self._speech_frames = 0
        self._preroll.clear()

    @property
    def collecting(self) -> bool:
        return self._collecting

    def push(self, prob: float, frame) -> list | None:
        """Feed one frame. Returns collected frames when an utterance completes."""
        if not self._collecting:
            self._preroll.append(frame)
            if prob >= self.start_prob:
                self._collecting = True
                self._frames = list(self._preroll)
                self._speech_frames = 1
                self._silence_run = 0
            return None

        self._frames.append(frame)

        if prob >= self.end_prob:
            self._speech_frames += 1
            self._silence_run = 0
        else:
            self._silence_run += 1
            if self._silence_run >= self._hangover_frames:
                return self._finish()

        if len(self._frames) >= self._max_frames:
            return self._finish()
        return None

    def _finish(self) -> list | None:
        frames = self._frames
        enough_speech = self._speech_frames >= self._min_speech_frames
        self.reset()
        return frames if enough_speech else None
