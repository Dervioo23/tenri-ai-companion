import json
import builtins
from unittest.mock import patch, MagicMock
from app.services.document_loader import DocumentLoader


SAMPLE_SOURCE = {
    "id": "test-doc",
    "title": "Test Document",
    "type": "project_note",
    "active_version": "v1",
    "status": "active",
    "versions": [{"version": "v1", "path": "project_notes/test_doc.md", "status": "active"}],
}

SAMPLE_MD = """# Judul Utama

Paragraf pertama sebelum heading kedua.

## Bagian Satu

Isi bagian satu.
Masih bagian satu.

## Bagian Dua

Isi bagian dua.
"""

SAMPLE_TXT = """Paragraf pertama.
Masih paragraf pertama.

Paragraf kedua.

Paragraf ketiga.
"""


class TestDocumentLoaderChunking:
    def setup_method(self):
        self.loader = DocumentLoader.__new__(DocumentLoader)

    def test_chunk_markdown_splits_by_heading(self):
        chunks = self.loader._chunk_markdown(SAMPLE_MD, SAMPLE_SOURCE)
        assert len(chunks) == 3
        assert chunks[0]["heading"] == "# Judul Utama"
        assert chunks[1]["heading"] == "## Bagian Satu"
        assert chunks[2]["heading"] == "## Bagian Dua"

    def test_chunk_markdown_preserves_metadata(self):
        chunks = self.loader._chunk_markdown(SAMPLE_MD, SAMPLE_SOURCE)
        for chunk in chunks:
            assert chunk["source_id"] == "test-doc"
            assert chunk["version"] == "v1"
            assert chunk["title"] == "Test Document"
            assert chunk["type"] == "project_note"

    def test_chunk_markdown_sequential_index(self):
        chunks = self.loader._chunk_markdown(SAMPLE_MD, SAMPLE_SOURCE)
        assert [c["chunk_index"] for c in chunks] == [0, 1, 2]

    def test_chunk_text_splits_by_paragraph(self):
        chunks = self.loader._chunk_text(SAMPLE_TXT, SAMPLE_SOURCE)
        assert len(chunks) == 3
        assert "Paragraf pertama" in chunks[0]["text"]
        assert chunks[1]["text"] == "Paragraf kedua."
        assert chunks[2]["text"] == "Paragraf ketiga."

    def test_chunk_text_empty_heading(self):
        chunks = self.loader._chunk_text(SAMPLE_TXT, SAMPLE_SOURCE)
        for chunk in chunks:
            assert chunk["heading"] == ""

    def test_chunk_markdown_fallback_to_text_when_no_headings(self):
        no_headings = "Baris satu.\n\nBaris dua."
        chunks = self.loader._chunk_markdown(no_headings, SAMPLE_SOURCE)
        assert len(chunks) == 2

    def test_chunk_skips_empty_paragraphs(self):
        text = "\n\n\nIsi nyata.\n\n\n"
        chunks = self.loader._chunk_text(text, SAMPLE_SOURCE)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "Isi nyata."


class TestDocumentLoaderIO:
    def setup_method(self):
        self.loader = DocumentLoader.__new__(DocumentLoader)

    def test_load_active_sources_filters_inactive(self, tmp_path):
        sources = [
            {**SAMPLE_SOURCE, "id": "aktif", "status": "active"},
            {**SAMPLE_SOURCE, "id": "nonaktif", "status": "disabled"},
        ]
        sources_file = tmp_path / "sources.json"
        sources_file.write_text(json.dumps(sources), encoding="utf-8")

        with patch("app.services.document_loader.SOURCES_PATH", sources_file):
            result = self.loader.load_active_sources()

        assert len(result) == 1
        assert result[0]["id"] == "aktif"

    def test_load_active_sources_missing_file(self, tmp_path):
        with patch("app.services.document_loader.SOURCES_PATH", tmp_path / "missing.json"):
            result = self.loader.load_active_sources()
        assert result == []

    def test_load_active_sources_malformed_json_returns_empty(self, tmp_path):
        sources_file = tmp_path / "sources.json"
        sources_file.write_text("{ this is not valid json", encoding="utf-8")

        with patch("app.services.document_loader.SOURCES_PATH", sources_file):
            result = self.loader.load_active_sources()

        assert result == []

    def test_load_active_sources_non_list_json_returns_empty(self, tmp_path):
        sources_file = tmp_path / "sources.json"
        sources_file.write_text(json.dumps({"status": "active"}), encoding="utf-8")

        with patch("app.services.document_loader.SOURCES_PATH", sources_file):
            result = self.loader.load_active_sources()

        assert result == []

    def test_save_and_load_index(self, tmp_path):
        with patch("app.services.document_loader.INDEXES_DIR", tmp_path):
            chunks = [self.loader._make_chunk(SAMPLE_SOURCE, 0, "## A", "teks")]
            self.loader.save_index("test-doc", "v1", chunks)
            loaded = self.loader.load_index("test-doc", "v1")

        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0]["heading"] == "## A"

    def test_save_index_returns_path_when_cache_write_fails(self, tmp_path, caplog):
        with patch("app.services.document_loader.INDEXES_DIR", tmp_path), \
             patch("builtins.open", side_effect=PermissionError("disk full")):
            result = self.loader.save_index("test-doc", "v1", [])

        assert result == tmp_path / "test-doc_v1.json"
        assert "Could not save index cache for test-doc" in caplog.text

    def test_load_index_returns_none_if_missing(self, tmp_path):
        with patch("app.services.document_loader.INDEXES_DIR", tmp_path):
            result = self.loader.load_index("tidak-ada", "v1")
        assert result is None

    def test_load_index_returns_none_if_cache_is_malformed(self, tmp_path, caplog):
        index_file = tmp_path / "test-doc_v1.json"
        index_file.write_text("{ this is not valid json", encoding="utf-8")

        with patch("app.services.document_loader.INDEXES_DIR", tmp_path):
            result = self.loader.load_index("test-doc", "v1")

        assert result is None
        assert "Corrupted index cache test-doc_v1.json" in caplog.text

    def test_load_all_uses_cache(self, tmp_path):
        cached_chunks = [{"source_id": "test-doc", "chunk_index": 0, "text": "cached"}]
        index_file = tmp_path / "test-doc_v1.json"
        index_file.write_text(json.dumps(cached_chunks), encoding="utf-8")

        sources_file = tmp_path / "sources.json"
        sources_file.write_text(json.dumps([SAMPLE_SOURCE]), encoding="utf-8")

        with patch("app.services.document_loader.SOURCES_PATH", sources_file), \
             patch("app.services.document_loader.INDEXES_DIR", tmp_path):
            result = self.loader.load_all_documents()

        assert len(result) == 1
        assert result[0]["text"] == "cached"


class TestDocumentLoaderExtractors:
    def setup_method(self):
        self.loader = DocumentLoader.__new__(DocumentLoader)

    def _pdf_source(self, path):
        return {**SAMPLE_SOURCE, "versions": [{"version": "v1", "path": str(path), "status": "active"}]}

    def test_extract_text_returns_empty_when_plain_text_decode_fails(self, tmp_path, caplog):
        text_file = tmp_path / "broken.txt"
        text_file.write_bytes(b"\xff\xfe\xfa")

        result = self.loader._extract_text(text_file)

        assert result == ""
        assert "Failed to read broken.txt" in caplog.text

    def test_extract_pdf_returns_pages(self, tmp_path):
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Teks halaman satu."
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Teks halaman dua."
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page1, mock_page2]

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = self.loader._extract_pdf(tmp_path / "test.pdf")

        assert "[Halaman 1]" in result
        assert "Teks halaman satu." in result
        assert "[Halaman 2]" in result
        assert "Teks halaman dua." in result

    def test_extract_pdf_skips_empty_pages(self, tmp_path):
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "   "
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Isi nyata."
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page1, mock_page2]

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = self.loader._extract_pdf(tmp_path / "test.pdf")

        assert "[Halaman 1]" not in result
        assert "[Halaman 2]" in result

    def test_extract_pdf_returns_empty_when_dependency_missing(self, tmp_path):
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pdfplumber":
                raise ImportError("missing pdfplumber")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            result = self.loader._extract_pdf(tmp_path / "test.pdf")

        assert result == ""

    def test_extract_pdf_returns_empty_when_parser_fails(self, tmp_path):
        with patch("pdfplumber.open", side_effect=Exception("encrypted pdf")):
            result = self.loader._extract_pdf(tmp_path / "test.pdf")

        assert result == ""

    def test_extract_docx_returns_paragraphs(self, tmp_path):
        mock_para1 = MagicMock()
        mock_para1.text = "Paragraf pertama."
        mock_para2 = MagicMock()
        mock_para2.text = "  "
        mock_para3 = MagicMock()
        mock_para3.text = "Paragraf ketiga."
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]

        with patch("docx.Document", return_value=mock_doc):
            result = self.loader._extract_docx(tmp_path / "test.docx")

        assert "Paragraf pertama." in result
        assert "Paragraf ketiga." in result
        assert result.count("\n\n") == 1

    def test_extract_docx_returns_empty_when_dependency_missing(self, tmp_path):
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "docx":
                raise ImportError("missing docx")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            result = self.loader._extract_docx(tmp_path / "test.docx")

        assert result == ""

    def test_extract_docx_returns_empty_when_parser_fails(self, tmp_path):
        with patch("docx.Document", side_effect=Exception("broken docx")):
            result = self.loader._extract_docx(tmp_path / "test.docx")

        assert result == ""

    def test_extract_pptx_returns_slides(self, tmp_path):
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_para = MagicMock()
        mock_para.text = "Judul Slide Satu"
        mock_shape.text_frame.paragraphs = [mock_para]

        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]

        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        with patch("pptx.Presentation", return_value=mock_prs):
            result = self.loader._extract_pptx(tmp_path / "test.pptx")

        assert "[Slide 1]" in result
        assert "Judul Slide Satu" in result

    def test_extract_pptx_skips_empty_slides(self, tmp_path):
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_para = MagicMock()
        mock_para.text = "   "
        mock_shape.text_frame.paragraphs = [mock_para]

        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]

        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        with patch("pptx.Presentation", return_value=mock_prs):
            result = self.loader._extract_pptx(tmp_path / "test.pptx")

        assert result == ""

    def test_extract_pptx_returns_empty_when_dependency_missing(self, tmp_path):
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pptx":
                raise ImportError("missing pptx")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            result = self.loader._extract_pptx(tmp_path / "test.pptx")

        assert result == ""

    def test_extract_pptx_returns_empty_when_parser_fails(self, tmp_path):
        with patch("pptx.Presentation", side_effect=Exception("broken pptx")):
            result = self.loader._extract_pptx(tmp_path / "test.pptx")

        assert result == ""

    def test_load_and_chunk_skips_unsupported_format(self, tmp_path):
        fake_file = tmp_path / "doc.xlsx"
        fake_file.write_bytes(b"binary")
        source = {
            **SAMPLE_SOURCE,
            "versions": [{"version": "v1", "path": str(fake_file), "status": "active"}],
        }
        with patch("app.services.document_loader.KNOWLEDGE_DIR", tmp_path):
            chunks = self.loader.load_and_chunk(source)
        assert chunks == []
