from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts import run_rehearsal


def test_rehearsal_output_paths_include_timestamp(tmp_path):
    now = datetime(2026, 6, 4, 20, 15, 30)

    with patch.object(run_rehearsal, "REHEARSAL_DIR", tmp_path):
        rehearsal_path, priority_path = run_rehearsal.rehearsal_output_paths(now)

    assert rehearsal_path == Path(tmp_path) / "rehearsal_20260604_201530.md"
    assert priority_path == Path(tmp_path) / "priority_fixes_20260604_201530.md"
