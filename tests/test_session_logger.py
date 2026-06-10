import json
import pytest
from unittest.mock import patch
from pathlib import Path
from app.services.session_logger import SessionLogger


def make_logger(tmp_path):
    with patch("app.services.session_logger.LOGS_DIR", tmp_path):
        return SessionLogger()


class TestSessionLoggerInit:
    def test_creates_log_file_directory(self, tmp_path):
        log_dir = tmp_path / "session_logs"
        with patch("app.services.session_logger.LOGS_DIR", log_dir):
            SessionLogger()
        assert log_dir.exists()

    def test_path_property_returns_path(self, tmp_path):
        sl = make_logger(tmp_path)
        assert isinstance(sl.path, Path)

    def test_log_filename_has_session_prefix(self, tmp_path):
        sl = make_logger(tmp_path)
        assert sl.path.name.startswith("session_")

    def test_log_filename_has_jsonl_extension(self, tmp_path):
        sl = make_logger(tmp_path)
        assert sl.path.suffix == ".jsonl"


class TestLogExchange:
    def test_log_exchange_creates_file(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("hello", "hi there")
        assert sl.path.exists()

    def test_log_exchange_writes_valid_json(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("apa itu la galigo", "La Galigo adalah epos besar.")
        line = sl.path.read_text(encoding="utf-8").strip()
        record = json.loads(line)
        assert isinstance(record, dict)

    def test_log_contains_user_input(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("pertanyaan saya", "jawaban tenri")
        record = json.loads(sl.path.read_text(encoding="utf-8"))
        assert record["user"] == "pertanyaan saya"

    def test_log_contains_response(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("pertanyaan saya", "jawaban tenri")
        record = json.loads(sl.path.read_text(encoding="utf-8"))
        assert record["tenri"] == "jawaban tenri"

    def test_log_contains_timestamp(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("tes", "tes")
        record = json.loads(sl.path.read_text(encoding="utf-8"))
        assert "timestamp" in record
        assert len(record["timestamp"]) > 0

    def test_log_contains_sources(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("tes", "tes", sources=["doc_a", "doc_b"])
        record = json.loads(sl.path.read_text(encoding="utf-8"))
        assert record["sources"] == ["doc_a", "doc_b"]

    def test_log_sources_defaults_to_empty_list(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("tes", "tes")
        record = json.loads(sl.path.read_text(encoding="utf-8"))
        assert record["sources"] == []

    def test_log_contains_slide_title(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("tes", "tes", slide_title="La Galigo")
        record = json.loads(sl.path.read_text(encoding="utf-8"))
        assert record["slide"] == "La Galigo"

    def test_log_mode_normal_by_default(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("tes", "tes")
        record = json.loads(sl.path.read_text(encoding="utf-8"))
        assert record["mode"] == "normal"

    def test_log_mode_interruption(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("[trigger]", "respons proaktif", mode="comment")
        record = json.loads(sl.path.read_text(encoding="utf-8"))
        assert record["mode"] == "comment"

    def test_multiple_exchanges_append_lines(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("pesan 1", "balas 1")
        sl.log_exchange("pesan 2", "balas 2")
        lines = sl.path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_multiple_exchanges_each_valid_json(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("pesan 1", "balas 1")
        sl.log_exchange("pesan 2", "balas 2")
        lines = sl.path.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            assert isinstance(json.loads(line), dict)

    def test_unicode_preserved(self, tmp_path):
        sl = make_logger(tmp_path)
        sl.log_exchange("Apa itu Sawerigading?", "Sawerigading ialah tokoh La Galigo.")
        record = json.loads(sl.path.read_text(encoding="utf-8"))
        assert "Sawerigading" in record["user"]
        assert "Sawerigading" in record["tenri"]
