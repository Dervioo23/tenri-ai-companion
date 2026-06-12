import json
import wave

import pytest

from app.pipeline.audio_corpus import AudioRegressionCorpus


def _write_wav(path, *, channels=1, width=2, rate=16000, frames=1600) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(b"\x00" * frames * channels * width)


def test_audio_corpus_adds_and_loads_verified_fixture(tmp_path) -> None:
    source = tmp_path / "source.wav"
    _write_wav(source)
    corpus = AudioRegressionCorpus(tmp_path / "corpus")

    added = corpus.add(
        source,
        fixture_id="wake-word-tail",
        expected_transcript="Apa itu AI, Tenri?",
        expected_intent="asking_tenri",
        notes="wake word at the end",
    )
    loaded = corpus.load()

    assert added.duration_seconds == 0.1
    assert len(loaded) == 1
    assert loaded[0].sha256 == added.sha256
    assert loaded[0].audio_path.read_bytes() == source.read_bytes()


def test_audio_corpus_rejects_duplicate_without_replace(tmp_path) -> None:
    source = tmp_path / "source.wav"
    _write_wav(source)
    corpus = AudioRegressionCorpus(tmp_path / "corpus")
    kwargs = {
        "fixture_id": "duplicate-case",
        "expected_transcript": "Tenri",
        "expected_intent": "asking_tenri",
    }
    corpus.add(source, **kwargs)
    with pytest.raises(ValueError, match="already exists"):
        corpus.add(source, **kwargs)


def test_audio_corpus_rejects_non_mono_wav(tmp_path) -> None:
    source = tmp_path / "stereo.wav"
    _write_wav(source, channels=2)
    corpus = AudioRegressionCorpus(tmp_path / "corpus")
    with pytest.raises(ValueError, match="mono"):
        corpus.add(
            source,
            fixture_id="stereo-case",
            expected_transcript="Tenri",
            expected_intent="asking_tenri",
        )


def test_audio_corpus_detects_modified_fixture(tmp_path) -> None:
    source = tmp_path / "source.wav"
    _write_wav(source)
    corpus = AudioRegressionCorpus(tmp_path / "corpus")
    fixture = corpus.add(
        source,
        fixture_id="modified-case",
        expected_transcript="Tenri",
        expected_intent="asking_tenri",
    )
    fixture.audio_path.write_bytes(fixture.audio_path.read_bytes() + b"tampered")

    with pytest.raises(ValueError, match="checksum mismatch"):
        corpus.load()


def test_audio_corpus_rejects_manifest_path_traversal(tmp_path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps({
        "version": 1,
        "fixtures": [{
            "id": "bad-path",
            "audio": "../outside.wav",
            "expected_transcript": "",
            "expected_intent": "noise",
            "sha256": "x",
            "duration_seconds": 1.0,
        }],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="escapes corpus root"):
        AudioRegressionCorpus(root).load()
