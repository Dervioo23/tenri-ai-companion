"""Tests for scripts/report_latency.py (TAHAP 0 — pengukuran latency)."""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.report_latency import percentile, load_metric_turns, CRITICAL_PATH


def test_percentile_empty_is_zero():
    assert percentile([], 50) == 0.0


def test_percentile_single_value():
    assert percentile([3.0], 95) == 3.0


def test_percentile_p50_is_median():
    assert percentile([1.0, 2.0, 3.0], 50) == 2.0


def test_percentile_p95_interpolates_high_end():
    vals = [float(i) for i in range(1, 11)]  # 1..10
    # p95 of 1..10 (linear interp) = 9.55
    assert abs(percentile(vals, 95) - 9.55) < 1e-9


def test_percentile_p100_is_max():
    assert percentile([1.0, 5.0, 9.0], 100) == 9.0


def _write_session(path: Path, records: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )


def test_load_metric_turns_collects_only_records_with_metrics(tmp_path):
    session = tmp_path / "session_test.jsonl"
    _write_session(session, [
        {"user": "a", "tenri": "b"},                                  # no metrics
        {"user": "c", "tenri": "d", "metrics": {"stt": 0.5}},         # has metrics
        {"user": "e", "tenri": "f", "mode": "comment"},               # interruption, no metrics
        {"user": "g", "tenri": "h", "metrics": {"stt": 0.7, "retrieval": 0.1}},
    ])

    turns = load_metric_turns([str(session)])

    assert len(turns) == 2
    assert turns[0]["stt"] == 0.5
    assert turns[1]["retrieval"] == 0.1


def test_load_metric_turns_skips_malformed_lines(tmp_path):
    session = tmp_path / "session_bad.jsonl"
    session.write_text(
        '{"metrics": {"stt": 0.4}}\n'
        "ini bukan json\n"
        '{"metrics": {"stt": 0.6}}\n',
        encoding="utf-8",
    )

    turns = load_metric_turns([str(session)])

    assert [t["stt"] for t in turns] == [0.4, 0.6]


def test_critical_path_keys_are_expected():
    assert CRITICAL_PATH == ("stt", "retrieval", "tts_first_voice")
