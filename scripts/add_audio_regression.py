"""Add a failed rehearsal recording to Tenri's regression corpus."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.pipeline.audio_corpus import AudioRegressionCorpus


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path, help="Mono 16-bit PCM WAV recording")
    parser.add_argument("--id", required=True, dest="fixture_id")
    parser.add_argument("--expected", required=True, dest="expected_transcript")
    parser.add_argument("--intent", required=True, dest="expected_intent")
    parser.add_argument("--notes", default="")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=ROOT_DIR / "tests" / "audio_corpus",
        help="Corpus directory (default: tests/audio_corpus)",
    )
    args = parser.parse_args()

    fixture = AudioRegressionCorpus(args.corpus).add(
        args.wav,
        fixture_id=args.fixture_id,
        expected_transcript=args.expected_transcript,
        expected_intent=args.expected_intent,
        notes=args.notes,
        replace=args.replace,
    )
    print(
        f"Added {fixture.fixture_id}: {fixture.duration_seconds:.3f}s, "
        f"sha256={fixture.sha256[:12]}..."
    )


if __name__ == "__main__":
    main()
