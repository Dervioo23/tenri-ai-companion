"""Versioned audio regression corpus for speech-pipeline failures."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import wave
from dataclasses import dataclass
from pathlib import Path

_FIXTURE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")


@dataclass(frozen=True, slots=True)
class AudioFixture:
    fixture_id: str
    audio_path: Path
    expected_transcript: str
    expected_intent: str
    sha256: str
    duration_seconds: float
    notes: str = ""


class AudioRegressionCorpus:
    """Read and update a local WAV corpus using an atomic JSON manifest."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.audio_dir = self.root / "audio"
        self.manifest_path = self.root / "manifest.json"

    def load(self) -> list[AudioFixture]:
        if not self.manifest_path.exists():
            return []
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        fixtures = []
        for item in data.get("fixtures", []):
            relative_path = Path(item["audio"])
            audio_path = (self.root / relative_path).resolve()
            if self.root not in audio_path.parents:
                raise ValueError(f"Audio fixture escapes corpus root: {relative_path}")
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio fixture missing: {relative_path}")
            actual_digest = hashlib.sha256(audio_path.read_bytes()).hexdigest()
            if actual_digest != item["sha256"]:
                raise ValueError(f"Audio fixture checksum mismatch: {relative_path}")
            fixtures.append(AudioFixture(
                fixture_id=item["id"],
                audio_path=audio_path,
                expected_transcript=item["expected_transcript"],
                expected_intent=item["expected_intent"],
                sha256=item["sha256"],
                duration_seconds=float(item["duration_seconds"]),
                notes=item.get("notes", ""),
            ))
        return fixtures

    def add(
        self,
        source_wav: Path,
        *,
        fixture_id: str,
        expected_transcript: str,
        expected_intent: str,
        notes: str = "",
        replace: bool = False,
    ) -> AudioFixture:
        if not _FIXTURE_ID_RE.fullmatch(fixture_id):
            raise ValueError("fixture_id must use 3-64 lowercase letters, numbers, '_' or '-'.")
        source_wav = source_wav.resolve()
        if not source_wav.is_file() or source_wav.suffix.lower() != ".wav":
            raise ValueError("source_wav must be an existing .wav file.")
        duration = self._validate_wav(source_wav)
        existing = {fixture.fixture_id: fixture for fixture in self.load()}
        if fixture_id in existing and not replace:
            raise ValueError(f"Fixture already exists: {fixture_id}")

        self.audio_dir.mkdir(parents=True, exist_ok=True)
        destination = self.audio_dir / f"{fixture_id}.wav"
        shutil.copy2(source_wav, destination)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        fixture = AudioFixture(
            fixture_id=fixture_id,
            audio_path=destination,
            expected_transcript=expected_transcript.strip(),
            expected_intent=expected_intent.strip(),
            sha256=digest,
            duration_seconds=duration,
            notes=notes.strip(),
        )
        existing[fixture_id] = fixture
        self._write_manifest(existing.values())
        return fixture

    @staticmethod
    def _validate_wav(path: Path) -> float:
        try:
            with wave.open(str(path), "rb") as wav:
                if wav.getnchannels() != 1:
                    raise ValueError("Regression WAV must be mono.")
                if wav.getsampwidth() != 2:
                    raise ValueError("Regression WAV must use 16-bit PCM.")
                if wav.getcomptype() != "NONE":
                    raise ValueError("Regression WAV must be uncompressed PCM.")
                frames = wav.getnframes()
                rate = wav.getframerate()
        except wave.Error as error:
            raise ValueError(f"Invalid WAV file: {error}") from error
        if frames <= 0 or rate <= 0:
            raise ValueError("Regression WAV must contain audio frames.")
        return round(frames / rate, 3)

    def _write_manifest(self, fixtures) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        records = []
        for fixture in sorted(fixtures, key=lambda item: item.fixture_id):
            records.append({
                "id": fixture.fixture_id,
                "audio": fixture.audio_path.relative_to(self.root).as_posix(),
                "expected_transcript": fixture.expected_transcript,
                "expected_intent": fixture.expected_intent,
                "sha256": fixture.sha256,
                "duration_seconds": fixture.duration_seconds,
                "notes": fixture.notes,
            })
        temporary = self.manifest_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps({"version": 1, "fixtures": records}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.manifest_path)
