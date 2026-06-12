"""Tests for Silero VAD wrapper + endpointer (TAHAP 1)."""

import numpy as np
import pytest

from app.services.silero_vad import SpeechEndpointer, FRAME_MS


def _frame():
    return np.zeros(4, dtype=np.int16)


class TestSpeechEndpointer:
    def test_no_speech_never_emits(self):
        ep = SpeechEndpointer(hangover_ms=200, frame_ms=FRAME_MS)
        assert all(ep.push(0.05, _frame()) is None for _ in range(50))

    def test_speech_then_silence_emits_once_after_hangover(self):
        ep = SpeechEndpointer(
            start_prob=0.5, end_prob=0.35, hangover_ms=320,
            min_speech_ms=64, preroll_ms=0, frame_ms=32,
        )
        for _ in range(10):
            assert ep.push(0.9, _frame()) is None
        results = [ep.push(0.0, _frame()) for _ in range(10)]  # 320/32 = 10 frames
        emitted = [r for r in results if r is not None]
        assert len(emitted) == 1

    def test_short_blip_below_min_speech_is_dropped(self):
        ep = SpeechEndpointer(
            start_prob=0.5, end_prob=0.35, hangover_ms=64,
            min_speech_ms=320, preroll_ms=0, frame_ms=32,
        )
        ep.push(0.9, _frame())          # 1 speech frame (32ms < 320ms min)
        ep.push(0.0, _frame())          # silence 1
        assert ep.push(0.0, _frame()) is None  # hangover hit, but dropped

    def test_preroll_is_prepended(self):
        ep = SpeechEndpointer(
            start_prob=0.5, end_prob=0.35, hangover_ms=64,
            min_speech_ms=32, preroll_ms=96, frame_ms=32,
        )
        for i in range(3):              # 96/32 = 3 preroll frames
            ep.push(0.1, np.array([i], dtype=np.int16))
        ep.push(0.9, np.array([9], dtype=np.int16))   # onset
        out = ep.push(0.0, _frame()) or ep.push(0.0, _frame())
        assert out is not None
        assert len(out) >= 4            # preroll + onset retained

    def test_collecting_flag_tracks_state(self):
        ep = SpeechEndpointer(start_prob=0.5, frame_ms=32)
        assert ep.collecting is False
        ep.push(0.9, _frame())
        assert ep.collecting is True
        ep.reset()
        assert ep.collecting is False

    def test_max_speech_guard_force_emits(self):
        ep = SpeechEndpointer(
            start_prob=0.5, end_prob=0.35, hangover_ms=100000,
            min_speech_ms=32, preroll_ms=0, max_speech_ms=320, frame_ms=32,
        )
        out = None
        for _ in range(20):             # continuous speech, never silent
            r = ep.push(0.9, _frame())
            if r is not None:
                out = r
                break
        assert out is not None
        assert len(out) <= 11           # capped near 320/32 = 10 frames


class TestSileroVADModel:
    def test_silence_yields_low_probability(self):
        pytest.importorskip("onnxruntime")
        from app.config import Config
        if not Config.SILERO_VAD_MODEL_PATH.exists():
            pytest.skip("silero_vad.onnx not present")
        from app.services.silero_vad import SileroVAD, FRAME_SAMPLES

        vad = SileroVAD(Config.SILERO_VAD_MODEL_PATH)
        silence = np.zeros(FRAME_SAMPLES, dtype=np.int16)
        probs = [vad.probability(silence) for _ in range(5)]

        assert all(0.0 <= p <= 1.0 for p in probs)
        assert max(probs) < 0.3

    def test_reset_clears_state(self):
        pytest.importorskip("onnxruntime")
        from app.config import Config
        if not Config.SILERO_VAD_MODEL_PATH.exists():
            pytest.skip("silero_vad.onnx not present")
        from app.services.silero_vad import SileroVAD, FRAME_SAMPLES

        vad = SileroVAD(Config.SILERO_VAD_MODEL_PATH)
        silence = np.zeros(FRAME_SAMPLES, dtype=np.int16)
        vad.probability(silence)
        vad.reset()
        # After reset, processing still works and returns a valid probability.
        assert 0.0 <= vad.probability(silence) <= 1.0


class TestSileroContextWindow:
    """Regression: Silero v5 needs 64 samples of carried-over context prepended
    to each 512-sample frame (576 total). Without it the model returns ~0.0 for
    even clear speech, so the VadListener captured nothing (silent-VAD bug)."""

    def _stub_vad(self):
        from app.services.silero_vad import SileroVAD, CONTEXT_SAMPLES

        vad = SileroVAD.__new__(SileroVAD)
        vad._sr = np.array(16000, dtype=np.int64)
        seen = {}

        def _run(_out_names, feed):
            seen["input"] = feed["input"]
            return [np.array([[0.7]], dtype=np.float32), feed["state"]]

        vad._session = type("S", (), {"run": staticmethod(_run)})()
        vad.reset()
        return vad, seen, CONTEXT_SAMPLES

    def test_input_is_frame_plus_context(self):
        from app.services.silero_vad import FRAME_SAMPLES

        vad, seen, ctx = self._stub_vad()
        frame = np.arange(FRAME_SAMPLES, dtype=np.int16)
        vad.probability(frame)
        # 512 frame samples + 64 context = 576, shaped (1, 576).
        assert seen["input"].shape == (1, FRAME_SAMPLES + ctx)

    def test_context_carries_tail_of_previous_frame(self):
        from app.services.silero_vad import FRAME_SAMPLES

        vad, seen, ctx = self._stub_vad()
        frame1 = np.full(FRAME_SAMPLES, 1000, dtype=np.int16)
        frame2 = np.zeros(FRAME_SAMPLES, dtype=np.int16)
        vad.probability(frame1)
        vad.probability(frame2)
        # Second call's leading `ctx` samples are frame1's tail (normalized), not zeros.
        leading = seen["input"][0, :ctx]
        assert np.allclose(leading, 1000.0 / 32768.0)

    def test_reset_clears_context(self):
        from app.services.silero_vad import FRAME_SAMPLES

        vad, seen, ctx = self._stub_vad()
        vad.probability(np.full(FRAME_SAMPLES, 1000, dtype=np.int16))
        vad.reset()
        vad.probability(np.zeros(FRAME_SAMPLES, dtype=np.int16))
        assert np.allclose(seen["input"][0, :ctx], 0.0)
