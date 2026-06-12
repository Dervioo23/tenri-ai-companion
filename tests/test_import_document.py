import logging
from types import SimpleNamespace

from scripts.import_document import _is_docx_heading, _safe_trigger_patterns


def test_safe_trigger_patterns_remove_generic_single_words() -> None:
    patterns = [
        "pengenalan teknologi",
        "pengenalan",
        "teknologi",
        "mengenal",
        "kecerdasan",
        "machine learning",
    ]

    assert _safe_trigger_patterns(patterns) == [
        "pengenalan teknologi",
        "machine learning",
    ]


def test_safe_trigger_patterns_keep_specific_domain_terms() -> None:
    patterns = ["chatgpt", "supervised", "deepfake", "risiko", "ringkasan"]

    assert _safe_trigger_patterns(patterns) == ["chatgpt", "supervised", "deepfake"]


def test_docx_heading_font_failure_is_logged(caplog) -> None:
    class BrokenSize:
        def __ge__(self, _other):
            raise ValueError("invalid font size")

    run = SimpleNamespace(
        text="Judul Campuran",
        bold=False,
        font=SimpleNamespace(size=BrokenSize()),
    )
    paragraph = SimpleNamespace(
        text="Judul Campuran",
        style=SimpleNamespace(name="Normal"),
        runs=[run],
    )

    with caplog.at_level(logging.WARNING, logger="AICompanion.ImportDocument"):
        assert _is_docx_heading(paragraph) is False

    assert "Gagal memeriksa ukuran font heading DOCX" in caplog.text
