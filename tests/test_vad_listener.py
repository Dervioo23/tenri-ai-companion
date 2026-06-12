"""Tests for VadListener (TAHAP 1) — no audio device or ONNX model required."""

import sys
import time
from unittest.mock import MagicMock, patch

import numpy as np
import speech_recognition as sr

from app.services.vad_listener import VadListener


def _listener(tmp_path):
    """VadListener with model path pointing at a missing file (so _vad stays None)."""
    speech = MagicMock()
    speech.microphone_available = True
    with patch("app.services.vad_listener.Config.SILERO_VAD_MODEL_PATH", tmp_path / "missing.onnx"):
        return VadListener(speech)


def _frames(n=20):
    return [np.zeros(512, dtype=np.int16) for _ in range(n)]


def test_usable_false_when_model_missing(tmp_path):
    vl = _listener(tmp_path)
    assert vl.usable is False


def test_usable_false_when_no_microphone(tmp_path):
    vl = _listener(tmp_path)
    vl._speech_service.microphone_available = False
    assert vl.usable is False


def test_start_returns_false_when_not_usable(tmp_path):
    vl = _listener(tmp_path)
    assert vl.start() is False


def test_handle_utterance_queues_normalized_text(tmp_path):
    vl = _listener(tmp_path)
    vl._speech_service._groq_client = object()
    vl._speech_service._transcribe_with_groq.return_value = "halo tenri"
    vl._speech_service.normalize_transcription.return_value = "halo tenri"

    vl._handle_utterance(_frames())

    assert vl.get(timeout=0.1) == "halo tenri"
    assert vl.last_record_seconds > 0


def test_handle_utterance_drops_unknown_value(tmp_path):
    vl = _listener(tmp_path)
    vl._speech_service._groq_client = object()
    vl._speech_service._transcribe_with_groq.side_effect = sr.UnknownValueError()

    vl._handle_utterance(_frames())

    assert vl.get(timeout=0.1) is None


def test_handle_utterance_skips_empty_normalized(tmp_path):
    vl = _listener(tmp_path)
    vl._speech_service._groq_client = object()
    vl._speech_service._transcribe_with_groq.return_value = "   "
    vl._speech_service.normalize_transcription.return_value = ""

    vl._handle_utterance(_frames())

    assert vl.get(timeout=0.1) is None


def test_get_timeout_returns_none(tmp_path):
    vl = _listener(tmp_path)
    assert vl.get(timeout=0.05) is None


def test_mute_unmute_noop_when_unavailable(tmp_path):
    vl = _listener(tmp_path)
    vl.mute()
    vl.unmute()
    assert vl.available is False


def test_start_sets_available_synchronously(tmp_path, monkeypatch):
    """available must be True the instant start() returns, so the main loop never
    races into sequential capture and fights for the mic (regression guard)."""
    vl = _listener(tmp_path)
    vl._vad = MagicMock()
    vl._vad.probability.return_value = 0.0  # silence → endpointer stays idle
    vl._speech_service.microphone_available = True
    vl._speech_service.device_index = None

    fake_stream = MagicMock()
    fake_stream.read.side_effect = lambda *a, **k: (time.sleep(0.001), b"\x00\x00" * 512)[1]
    fake_pa = MagicMock()
    fake_pa.open.return_value = fake_stream
    fake_pyaudio = MagicMock()
    fake_pyaudio.PyAudio.return_value = fake_pa
    fake_pyaudio.paInt16 = 8
    monkeypatch.setitem(sys.modules, "pyaudio", fake_pyaudio)

    try:
        assert vl.start() is True
        assert vl.available is True          # synchronous, not set later by the thread
        fake_pa.open.assert_called_once()
    finally:
        vl.stop()
    assert vl.available is False


def test_start_returns_false_when_stream_open_fails(tmp_path, monkeypatch):
    vl = _listener(tmp_path)
    vl._vad = MagicMock()
    vl._speech_service.microphone_available = True
    vl._speech_service.device_index = None

    fake_pa = MagicMock()
    fake_pa.open.side_effect = OSError("device busy")
    fake_pyaudio = MagicMock()
    fake_pyaudio.PyAudio.return_value = fake_pa
    fake_pyaudio.paInt16 = 8
    monkeypatch.setitem(sys.modules, "pyaudio", fake_pyaudio)

    assert vl.start() is False
    assert vl.available is False


def test_start_returns_false_when_stream_never_delivers_frame(tmp_path, monkeypatch):
    vl = _listener(tmp_path)
    vl._vad = MagicMock()
    vl._speech_service.microphone_available = True
    vl._speech_service.device_index = None

    fake_stream = MagicMock()
    fake_stream.read.side_effect = OSError("no audio frames")
    fake_pa = MagicMock()
    fake_pa.open.return_value = fake_stream
    fake_pyaudio = MagicMock()
    fake_pyaudio.PyAudio.return_value = fake_pa
    fake_pyaudio.paInt16 = 8
    monkeypatch.setitem(sys.modules, "pyaudio", fake_pyaudio)

    with patch("app.services.vad_listener.Config.SILERO_VAD_STARTUP_TIMEOUT", 0.01):
        assert vl.start() is False

    assert vl.available is False
    fake_stream.close.assert_called()
