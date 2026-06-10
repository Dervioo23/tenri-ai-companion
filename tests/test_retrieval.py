import pytest
import logging
from app.services.retrieval import RetrievalService, _tokenize


CHUNKS = [
    {
        "source_id": "la-galigo",
        "version": "v1",
        "title": "La Galigo",
        "type": "book",
        "chunk_index": 0,
        "heading": "## Sawerigading",
        "text": "Sawerigading adalah tokoh utama dalam epos La Galigo dari Bugis.",
    },
    {
        "source_id": "la-galigo",
        "version": "v1",
        "title": "La Galigo",
        "type": "book",
        "chunk_index": 1,
        "heading": "## We Tenriabeng",
        "text": "We Tenriabeng adalah saudara perempuan Sawerigading, seorang bijaksana.",
    },
    {
        "source_id": "presentasi-ai",
        "version": "v1",
        "title": "Presentasi AI",
        "type": "presentation",
        "chunk_index": 0,
        "heading": "",
        "text": "Kecerdasan buatan atau AI telah berkembang pesat dalam dekade terakhir.",
    },
]


class TestTokenize:
    def test_lowercase(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_strips_punctuation(self):
        assert _tokenize("kata, lain: lagi.") == ["kata", "lain", "lagi"]

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_whitespace_only(self):
        assert _tokenize("   ") == []


class TestRetrievalSearch:
    def test_search_returns_relevant_chunk(self):
        svc = RetrievalService(CHUNKS)
        results = svc.search("tokoh Sawerigading")
        assert len(results) >= 1
        assert results[0]["source_id"] == "la-galigo"

    def test_search_empty_chunks(self):
        svc = RetrievalService([])
        assert svc.search("apa saja") == []

    def test_search_respects_top_k(self):
        svc = RetrievalService(CHUNKS)
        results = svc.search("Sawerigading saudara bijaksana", top_k=1)
        assert len(results) == 1

    def test_search_empty_query(self):
        svc = RetrievalService(CHUNKS)
        assert svc.search("") == []

    def test_search_when_bm25_unavailable(self):
        svc = RetrievalService.__new__(RetrievalService)
        svc._chunks = CHUNKS
        svc._bm25 = None
        assert svc.search("Sawerigading") == []

    def test_search_result_order_by_relevance(self):
        svc = RetrievalService(CHUNKS)
        results = svc.search("kecerdasan buatan AI")
        assert len(results) >= 1
        assert results[0]["source_id"] == "presentasi-ai"
        assert "_retrieval_score" in results[0]
        assert "_query_overlap" in results[0]

    def test_search_returns_list_type(self):
        svc = RetrievalService(CHUNKS)
        assert isinstance(svc.search("apa pun"), list)

    def test_has_strong_match_uses_query_overlap(self):
        svc = RetrievalService(CHUNKS)
        strong = svc.search("Sawerigading")
        weak = [{"_query_overlap": 0}]

        assert svc.has_strong_match(strong)
        assert not svc.has_strong_match(weak)

    def test_search_log_does_not_include_raw_query(self, caplog):
        svc = RetrievalService(CHUNKS)
        private_query = "tokoh Sawerigading nomor pribadi 08123456789"

        with caplog.at_level(logging.INFO, logger="AICompanion.Retrieval"):
            results = svc.search(private_query)

        assert results
        assert private_query not in caplog.text
        assert "08123456789" not in caplog.text
        assert "query length" in caplog.text


class TestFormatContext:
    def setup_method(self):
        self.svc = RetrievalService.__new__(RetrievalService)
        self.svc._chunks = []
        self.svc._bm25 = None

    def test_empty_list_returns_empty_string(self):
        assert self.svc.format_context([]) == ""

    def test_includes_title_and_text(self):
        result = self.svc.format_context([CHUNKS[0]])
        assert "La Galigo" in result
        assert "sumber: la-galigo@v1 / book" in result
        assert "Sawerigading adalah tokoh" in result

    def test_includes_heading(self):
        result = self.svc.format_context([CHUNKS[0]])
        assert "## Sawerigading" in result

    def test_no_heading_skips_separator(self):
        result = self.svc.format_context([CHUNKS[2]])
        assert " — " not in result

    def test_numbering_multiple_chunks(self):
        result = self.svc.format_context(CHUNKS[:2])
        assert "[1]" in result
        assert "[2]" in result
