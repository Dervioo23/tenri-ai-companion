"""Offline compatibility smoke test for running Tenri on macOS.

This script never calls Groq, Gemini, ElevenLabs, or speech-to-text APIs. It
checks the local runtime and reports hardware availability separately because
GitHub-hosted runners do not expose a real microphone, speaker, or camera.
"""

from __future__ import annotations

import argparse
import importlib
import os
import pkgutil
import platform
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    @staticmethod
    def passed(message: str) -> None:
        print(f"[PASS] {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"[WARN] {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        print(f"[FAIL] {message}")


def _check_platform(report: Report, require_macos: bool) -> None:
    system = platform.system()
    report.passed(
        f"Python {platform.python_version()} on {system} "
        f"{platform.machine() or 'unknown-arch'}"
    )
    if sys.version_info < (3, 10):
        report.fail("Tenri requires Python 3.10 or newer.")
    if system != "Darwin":
        message = "This process is not running on macOS, so macOS is not proven here."
        if require_macos:
            report.fail(message)
        else:
            report.warn(message)


def _check_assets(report: Report) -> None:
    required_paths = [
        ROOT_DIR / "app" / "prompts" / "character_prompt.txt",
        ROOT_DIR / "app" / "prompts" / "system_rules.txt",
        ROOT_DIR / "app" / "presentation" / "slides.json",
        ROOT_DIR / "assets" / "models" / "silero_vad.onnx",
    ]
    missing = [str(path.relative_to(ROOT_DIR)) for path in required_paths if not path.is_file()]
    if missing:
        report.fail(f"Required runtime assets are missing: {', '.join(missing)}")
    else:
        report.passed("Required prompts, presentation data, and Silero model exist.")


def _check_dependencies(report: Report) -> None:
    required = {
        "cv2": "opencv-python",
        "docx": "python-docx",
        "dotenv": "python-dotenv",
        "groq": "groq",
        "numpy": "numpy",
        "pyaudio": "PyAudio",
        "pygame": "pygame",
        "pdfplumber": "pdfplumber",
        "pptx": "python-pptx",
        "rank_bm25": "rank-bm25",
        "requests": "requests",
        "rich": "rich",
        "speech_recognition": "SpeechRecognition",
    }
    optional = {
        "edge_tts": "edge-tts local fallback",
        "google.genai": "Gemini provider",
        "onnxruntime": "Silero VAD",
        "websockets": "ElevenLabs streaming TTS",
    }

    missing: list[str] = []
    for module_name, package_name in required.items():
        try:
            importlib.import_module(module_name)
        except Exception as error:
            missing.append(f"{package_name} ({error})")
    if missing:
        report.fail(f"Required dependencies failed to import: {'; '.join(missing)}")
    else:
        report.passed("All required Python dependencies import successfully.")

    unavailable: list[str] = []
    for module_name, feature_name in optional.items():
        try:
            importlib.import_module(module_name)
        except Exception:
            unavailable.append(feature_name)
    if unavailable:
        report.warn(f"Optional features unavailable: {', '.join(unavailable)}")
    else:
        report.passed("All optional provider, VAD, and streaming dependencies import.")


def _check_app_imports(report: Report) -> None:
    import app

    failures: list[str] = []
    for module in pkgutil.walk_packages(app.__path__, prefix="app."):
        try:
            importlib.import_module(module.name)
        except Exception as error:
            failures.append(f"{module.name}: {error}")
    if failures:
        report.fail("Application module imports failed: " + "; ".join(failures))
    else:
        report.passed("Every app.* module imports successfully.")


def _check_audio_devices(report: Report) -> None:
    try:
        import pyaudio

        audio = pyaudio.PyAudio()
        try:
            devices = [
                audio.get_device_info_by_index(index)
                for index in range(audio.get_device_count())
            ]
        finally:
            audio.terminate()
    except Exception as error:
        report.warn(f"PortAudio loaded but device enumeration failed: {error}")
        return

    inputs = [item for item in devices if item.get("maxInputChannels", 0) > 0]
    outputs = [item for item in devices if item.get("maxOutputChannels", 0) > 0]
    if inputs:
        report.passed(f"PortAudio found {len(inputs)} input device(s).")
    else:
        report.warn("No microphone is exposed to this process.")
    if outputs:
        report.passed(f"PortAudio found {len(outputs)} output device(s).")
    else:
        report.warn("No speaker/output device is exposed to this process.")


def _check_pygame(report: Report, headless: bool) -> None:
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    try:
        import pygame

        pygame.display.init()
        pygame.display.set_mode((32, 32))
        pygame.mixer.init()
        pygame.mixer.quit()
        pygame.display.quit()
    except Exception as error:
        report.fail(f"Pygame display/audio initialization failed: {error}")
    else:
        mode = "headless" if headless else "desktop"
        report.passed(f"Pygame display and mixer initialize in {mode} mode.")


def _check_macos_backends(report: Report) -> None:
    from app.services.vision_service import VisionService

    backend = VisionService._preferred_camera_backend()
    if platform.system() == "Darwin":
        if backend is None:
            report.fail("OpenCV AVFoundation camera backend is unavailable.")
        else:
            report.passed("OpenCV selects AVFoundation for the macOS camera.")
    else:
        report.warn("AVFoundation selection can only be confirmed on macOS.")

    try:
        import onnxruntime  # noqa: F401
        from app.config import Config
        from app.services.silero_vad import SileroVAD

        SileroVAD(Config.SILERO_VAD_MODEL_PATH)
    except ModuleNotFoundError:
        report.warn("onnxruntime is not installed; Silero VAD was not loaded.")
    except Exception as error:
        report.fail(f"Silero ONNX model failed to load: {error}")
    else:
        report.passed("Silero VAD model loads with ONNX Runtime.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-macos",
        action="store_true",
        help="Fail when the script is not running on macOS.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Use SDL dummy drivers for a CI runner without a display or speaker.",
    )
    args = parser.parse_args()

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    report = Report()
    print("Tenri macOS compatibility smoke test")
    print("=" * 38)
    _check_platform(report, args.require_macos)
    _check_assets(report)
    _check_dependencies(report)
    _check_app_imports(report)
    _check_audio_devices(report)
    _check_pygame(report, args.headless)
    _check_macos_backends(report)

    print("=" * 38)
    print(f"Result: {len(report.failures)} failure(s), {len(report.warnings)} warning(s)")
    if report.failures:
        print("macOS compatibility is NOT proven by this run.")
        return 1
    print("Software compatibility passed. Real hardware still requires the MacBook checklist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
