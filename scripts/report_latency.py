"""report_latency.py — Agregasi latency per tahap dari semua session JSONL.

Membaca semua file session_*.jsonl, mengumpulkan metrik per turn yang dicatat
SessionLogger, lalu mencetak p50/p95/mean/max per tahap. Juga menghitung metrik
turunan "ujung-bicara presenter -> suara pertama Tenri" dan membandingkannya
dengan anggaran (default 2,0 detik).

Pakai:
    python scripts/report_latency.py
    python scripts/report_latency.py --budget 2.0
    python scripts/report_latency.py --sessions "app/data/logs/session_2026*.jsonl"
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Lokasi log saat ini (authoritative) + lokasi legacy, supaya sesi lama tetap terbaca.
try:
    from app.config import Config
    _PRIMARY_LOGS_DIR = Config.LOGS_DIR
except Exception:  # pragma: no cover - fallback bila config gagal dimuat
    _PRIMARY_LOGS_DIR = ROOT_DIR / "app" / "data" / "logs"

_LEGACY_LOGS_DIR = ROOT_DIR / "logs"

# (kunci di JSONL, label tampilan)
STAGES: tuple[tuple[str, str], ...] = (
    ("wait", "Wait (menunggu mulai bicara)"),
    ("record", "Record (durasi rekam)"),
    ("stt", "STT (transkripsi)"),
    ("retrieval", "Retrieval (BM25)"),
    ("llm_first", "LLM kalimat-pertama"),
    ("tts_first_voice", "TTS suara-pertama"),
    ("tts_gen", "TTS generasi total"),
    ("playback", "Playback audio"),
    ("cycle", "Cycle total"),
)

# Tahap di jalur kritis "ujung-bicara -> suara pertama Tenri".
# tts_first_voice diukur dari awal stream (setelah retrieval) sampai audio pertama,
# jadi penjumlahan ini adalah proxy transparan untuk latensi yang dirasakan presenter.
CRITICAL_PATH: tuple[str, ...] = ("stt", "retrieval", "tts_first_voice")


def percentile(values: list[float], pct: float) -> float:
    """Persentil linear-interpolasi (pct 0..100) atas list nilai."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def resolve_paths(patterns: list[str] | None) -> list[str]:
    if patterns:
        paths: list[str] = []
        for pat in patterns:
            paths.extend(glob.glob(pat))
        return sorted(set(paths))

    paths = []
    for d in (_PRIMARY_LOGS_DIR, _LEGACY_LOGS_DIR):
        paths.extend(glob.glob(str(Path(d) / "session_*.jsonl")))
    return sorted(set(paths))


def load_metric_turns(paths: list[str]) -> list[dict]:
    """Kumpulkan dict metrik dari setiap turn yang memilikinya."""
    turns: list[dict] = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    m = rec.get("metrics")
                    if isinstance(m, dict):
                        turns.append(m)
        except OSError:
            continue
    return turns


def _numeric(turn: dict, key: str) -> float | None:
    v = turn.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agregasi latency per tahap dari session JSONL."
    )
    parser.add_argument(
        "--sessions", nargs="*",
        help='Glob/file JSONL (default: semua session_*.jsonl di folder log).',
    )
    parser.add_argument(
        "--budget", type=float, default=2.0,
        help="Anggaran ujung-bicara -> suara pertama Tenri, dalam detik (default 2.0).",
    )
    parser.add_argument(
        "--latest", type=int, default=0, metavar="N",
        help="Hanya N sesi terbaru (mis. --latest 1 untuk run terakhir). 0 = semua.",
    )
    args = parser.parse_args()

    paths = resolve_paths(args.sessions)
    if args.latest > 0:
        paths = paths[-args.latest:]  # nama file session_YYYYmmdd_HHMMSS = urut waktu
    if not paths:
        print(f"Tidak ada file sesi ditemukan di {_PRIMARY_LOGS_DIR}.")
        print("Jalankan Tenri dulu untuk menghasilkan log, lalu jalankan skrip ini.")
        return

    turns = load_metric_turns(paths)
    if not turns:
        print(f"Ditemukan {len(paths)} file sesi, tapi belum ada turn dengan metrik.")
        print("Metrik mulai dicatat setelah pembaruan SessionLogger — jalankan Tenri lagi.")
        return

    print(f"Sumber : {len(paths)} sesi, {len(turns)} turn dengan metrik\n")
    header = f"{'Tahap':<30}{'p50':>8}{'p95':>8}{'mean':>8}{'max':>8}{'n':>5}"
    print(header)
    print("-" * len(header))
    for key, label in STAGES:
        vals = [v for t in turns if (v := _numeric(t, key)) is not None]
        if not vals:
            continue
        print(
            f"{label:<30}{percentile(vals,50):>7.2f}s{percentile(vals,95):>7.2f}s"
            f"{sum(vals)/len(vals):>7.2f}s{max(vals):>7.2f}s{len(vals):>5}"
        )

    # Derived: jalur kritis ujung-bicara -> suara pertama
    crit = [
        sum(vals)
        for t in turns
        if None not in (vals := [_numeric(t, k) for k in CRITICAL_PATH])
    ]
    print()
    if crit:
        p50, p95 = percentile(crit, 50), percentile(crit, 95)
        ok = p95 <= args.budget
        print("Ujung-bicara -> suara pertama Tenri  (stt + retrieval + tts_first_voice):")
        print(f"   p50 = {p50:.2f}s   p95 = {p95:.2f}s   (anggaran {args.budget:.1f}s, n={len(crit)})")
        print(f"   p95 vs anggaran: {'OK' if ok else 'MELEBIHI'} "
              f"({p95:.2f}s {'<=' if ok else '>'} {args.budget:.1f}s)")
    else:
        print("Tidak cukup data untuk menghitung jalur kritis.")


if __name__ == "__main__":
    main()
