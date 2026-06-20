"""Diagnose the microphone selected by Tenri without calling any cloud API."""

from __future__ import annotations

import audioop
import statistics
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pyaudio

from app.config import Config
from app.services.speech_service import SpeechService


def main() -> int:
    service = SpeechService()
    print("Tenri microphone diagnostic")
    print("=" * 32)
    print(f"Configured MIC_DEVICE_INDEX: {Config.MIC_DEVICE_INDEX or '(system default)'}")

    audio = pyaudio.PyAudio()
    try:
        default_info = audio.get_default_input_device_info()
        print(
            "PortAudio default input: "
            f"{int(default_info['index'])} - {default_info['name']}"
        )
        print("\nInput devices:")
        for index in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(index)
            if int(info.get("maxInputChannels", 0)) > 0:
                marker = " [DEFAULT]" if index == int(default_info["index"]) else ""
                print(
                    f"  {index}: {info['name']} "
                    f"(channels={int(info['maxInputChannels'])}, "
                    f"rate={int(info['defaultSampleRate'])}){marker}"
                )
    except Exception as exc:
        print(f"[FAIL] Could not enumerate the default microphone: {exc}")
        return 1
    finally:
        audio.terminate()

    print("\nSpeak clearly for five seconds: 'Halo Tenri, apakah kamu mendengar saya?'")
    rms_values: list[int] = []
    peak = 0
    try:
        with service.microphone_source(service.device_index) as source:
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                data = source.stream.read(source.CHUNK)
                rms = audioop.rms(data, source.SAMPLE_WIDTH)
                current_peak = audioop.max(data, source.SAMPLE_WIDTH)
                rms_values.append(rms)
                peak = max(peak, current_peak)
    except Exception as exc:
        print(f"[FAIL] Microphone capture failed: {exc}")
        return 1

    maximum_rms = max(rms_values, default=0)
    median_rms = int(statistics.median(rms_values)) if rms_values else 0
    configured = Config.SPEECH_ENERGY_THRESHOLD
    active = service.background_energy_threshold(median_rms, configured)

    print("\nCapture result:")
    print(f"  Median RMS : {median_rms}")
    print(f"  Maximum RMS: {maximum_rms}")
    print(f"  Peak       : {peak}")
    print(f"  Tenri gate : {active}")

    if peak < 10:
        print("[FAIL] The selected microphone delivered silence.")
        print("Check macOS Microphone permission and System Settings > Sound > Input.")
        return 1
    if maximum_rms <= active:
        print("[FAIL] Voice level did not cross Tenri's energy gate.")
        print(
            "Set SPEECH_ENERGY_THRESHOLD=300 temporarily, move closer to the "
            "microphone, then run this diagnostic again."
        )
        return 1

    print("[PASS] The microphone delivered voice above Tenri's energy gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
