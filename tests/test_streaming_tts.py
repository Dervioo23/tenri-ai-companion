"""Tests for StreamingTTS (TAHAP 2) — no real network or audio device."""

import base64
import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from app.services.streaming_tts import StreamingTTS


def _svc() -> StreamingTTS:
    """A StreamingTTS instance with streaming forced available (no real deps)."""
    svc = StreamingTTS.__new__(StreamingTTS)
    svc.api_key = "test-key"
    svc.voice_id = "voice-1"
    svc._ws_ok = True
    svc.available = True
    svc._rate = 22050
    svc.last_playback_seconds = 0.0
    StreamingTTS._circuit_open_until = 0.0
    return svc


# ------------------------------------------------------------------ pure helpers

@pytest.mark.parametrize(
    ("fmt", "rate"),
    [("pcm_22050", 22050), ("pcm_16000", 16000), ("pcm_44100", 44100), ("garbage", 22050)],
)
def test_parse_rate(fmt, rate):
    assert StreamingTTS._parse_rate(fmt) == rate


def test_build_uri_contains_voice_model_and_format():
    svc = _svc()
    with patch("app.services.streaming_tts.Config.ELEVENLABS_MODEL", "eleven_flash_v2_5"), \
         patch("app.services.streaming_tts.Config.ELEVENLABS_STREAM_OUTPUT_FORMAT", "pcm_22050"), \
         patch("app.services.streaming_tts.Config.ELEVENLABS_STREAM_AUTO_MODE", True), \
         patch("app.services.streaming_tts.Config.ELEVENLABS_STREAM_INACTIVITY_TIMEOUT", 20), \
         patch("app.services.streaming_tts.Config.APP_LANGUAGE", "id"):
        uri = svc._build_uri()
    assert uri.startswith("wss://api.elevenlabs.io/v1/text-to-speech/voice-1/stream-input")
    assert "model_id=eleven_flash_v2_5" in uri
    assert "output_format=pcm_22050" in uri
    assert "auto_mode=true" in uri
    assert "inactivity_timeout=20" in uri
    assert "language_code=id" in uri
    assert "optimize_streaming_latency" not in uri


def test_bos_message_keeps_language_in_uri_not_payload():
    svc = _svc()
    with patch("app.services.streaming_tts.Config.APP_LANGUAGE", "id"):
        msg = svc._bos_message()
    assert "language_code" not in msg
    assert "voice_settings" in msg


def test_bos_message_omits_language_for_bilingual():
    svc = _svc()
    with patch("app.services.streaming_tts.Config.APP_LANGUAGE", "bilingual"):
        msg = svc._bos_message()
    assert "language_code" not in msg


# ------------------------------------------------------------------ speak guards

def test_speak_returns_false_when_unavailable():
    svc = _svc()
    svc.available = False
    assert svc.speak("halo") is False


def test_speak_returns_false_on_empty_text():
    svc = _svc()
    assert svc.speak("   ") is False
    assert svc.speak("[Offline Mode]") is False


def test_speak_swallows_errors_and_returns_false():
    svc = _svc()
    with patch.object(svc, "_run", side_effect=RuntimeError("boom")):
        assert svc.speak("halo tenri") is False


def test_speak_skips_network_while_circuit_is_open():
    svc = _svc()
    StreamingTTS._circuit_open_until = float("inf")
    with patch.object(svc, "_run") as run:
        assert svc.speak("halo tenri") is False
    run.assert_not_called()


# ------------------------------------------------------------------ websocket session

class _FakeWS:
    def __init__(self, messages):
        self._messages = messages
        self.sent = []

    async def send(self, m):
        self.sent.append(m)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        self._it = iter(self._messages)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


def test_session_plays_pcm_and_fires_first_audio_callback(monkeypatch):
    svc = _svc()

    pcm = b"\x01\x02\x03\x04"
    messages = [
        json.dumps({"audio": base64.b64encode(pcm).decode(), "isFinal": False}),
        json.dumps({"audio": None, "isFinal": True}),
    ]
    captured_ws = {}

    def _connect(*args, **kwargs):
        assert kwargs["proxy"] is None
        ws = _FakeWS(messages)
        captured_ws["ws"] = ws
        return ws

    fake_websockets = MagicMock()
    fake_websockets.connect = _connect

    fake_stream = MagicMock()
    fake_pa = MagicMock()
    fake_pa.open.return_value = fake_stream
    fake_pyaudio = MagicMock()
    fake_pyaudio.PyAudio.return_value = fake_pa
    fake_pyaudio.paInt16 = 8

    monkeypatch.setitem(sys.modules, "websockets", fake_websockets)
    monkeypatch.setitem(sys.modules, "pyaudio", fake_pyaudio)

    first_audio_calls = []
    played = svc.speak("halo tenri", on_first_audio=lambda: first_audio_calls.append(1))

    assert played is True
    # PCM was written to the output stream
    fake_stream.write.assert_called_once_with(pcm)
    # first-audio callback fired exactly once
    assert len(first_audio_calls) == 1
    assert svc.last_playback_seconds >= 0.0
    # protocol: BOS (voice_settings) + text + EOS
    sent = [json.loads(m) for m in captured_ws["ws"].sent]
    assert "voice_settings" in sent[0]
    assert sent[1]["text"].strip() == "halo tenri"
    assert sent[-1]["text"] == ""
    # output stream cleaned up
    fake_stream.close.assert_called_once()
    fake_pa.terminate.assert_called_once()
