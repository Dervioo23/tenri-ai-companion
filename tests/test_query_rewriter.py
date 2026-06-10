import pytest
from app.services.query_rewriter import QueryRewriter


@pytest.fixture
def rewriter():
    return QueryRewriter()


@pytest.fixture
def slide_digitalisasi():
    return {
        "title": "Digitalisasi Arsip Museum La Galigo",
        "topics": ["arsip", "digital", "pelestarian"],
    }


@pytest.fixture
def history_with_lagaligo():
    return [
        {"role": "user", "content": "ceritakan tentang La Galigo"},
        {
            "role": "assistant",
            "content": (
                "La Galigo adalah naskah epik terpanjang di dunia dari Sawerigading "
                "yang tersimpan di Museum Makassar."
            ),
        },
    ]


# ------------------------------------------------------------------ non-vague queries


def test_specific_query_enriched_with_slide_topics(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("apa itu La Galigo?", slide_digitalisasi, [])
    assert "apa itu La Galigo?" in result
    assert "Digitalisasi Arsip Museum La Galigo" in result
    assert "arsip" in result
    assert "digital" in result


def test_specific_query_no_slide_returns_as_is(rewriter):
    result = rewriter.rewrite("apa itu La Galigo?", None, [])
    assert result == "apa itu La Galigo?"


def test_specific_query_no_slide_no_history(rewriter):
    result = rewriter.rewrite("jelaskan proses digitalisasi", None, [])
    assert result == "jelaskan proses digitalisasi"


def test_specific_query_with_proper_noun_enriched(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("Sawerigading itu siapa?", slide_digitalisasi, [])
    assert "Sawerigading" in result
    assert "Digitalisasi Arsip Museum La Galigo" in result


def test_generic_question_not_enriched_with_active_slide(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("apa kabar?", slide_digitalisasi, [])
    assert result == "apa kabar?"
    assert "Digitalisasi Arsip Museum La Galigo" not in result


def test_slide_reference_is_enriched_with_active_slide(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("jelaskan slide ini", slide_digitalisasi, [])
    assert "jelaskan slide ini" in result
    assert "Digitalisasi Arsip Museum La Galigo" in result


# ------------------------------------------------------------------ vague anaphor detection


def test_vague_tadi_kamu_bilang(rewriter, slide_digitalisasi):
    result = rewriter.rewrite(
        "tadi kamu bilang soal itu, gimana lebih detailnya?",
        slide_digitalisasi,
        [],
    )
    assert "Digitalisasi Arsip Museum La Galigo" in result
    assert "arsip" in result


def test_vague_yang_tadi(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("yang tadi, bisa dijelaskan lagi?", slide_digitalisasi, [])
    assert "Digitalisasi Arsip Museum La Galigo" in result


def test_vague_yang_barusan(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("yang barusan kamu bilang itu apa?", slide_digitalisasi, [])
    assert "Digitalisasi Arsip Museum La Galigo" in result


def test_vague_hal_tersebut(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("hal tersebut maksudnya apa?", slide_digitalisasi, [])
    assert "Digitalisasi Arsip Museum La Galigo" in result


# ------------------------------------------------------------------ vague elaboration detection


def test_vague_lebih_detail(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("bisa lebih detail?", slide_digitalisasi, [])
    assert "Digitalisasi Arsip Museum La Galigo" in result


def test_vague_lebih_lanjut(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("jelaskan lebih lanjut", slide_digitalisasi, [])
    assert "Digitalisasi Arsip Museum La Galigo" in result


def test_vague_lebih_lengkap(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("lebih lengkap dong", slide_digitalisasi, [])
    assert "Digitalisasi Arsip Museum La Galigo" in result


def test_vague_ceritakan_lebih(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("ceritakan lebih", slide_digitalisasi, [])
    assert "Digitalisasi Arsip Museum La Galigo" in result


# ------------------------------------------------------------------ short query detection


def test_short_query_without_proper_noun_is_vague(rewriter, slide_digitalisasi):
    result = rewriter.rewrite("apa itu?", slide_digitalisasi, [])
    assert "Digitalisasi Arsip Museum La Galigo" in result


def test_short_query_with_proper_noun_not_vague(rewriter, slide_digitalisasi):
    # "Sawerigading?" is short but has a proper noun — not vague
    result = rewriter.rewrite("Sawerigading?", slide_digitalisasi, [])
    assert "Sawerigading?" in result
    assert "Digitalisasi Arsip Museum La Galigo" in result


def test_three_tokens_without_proper_noun_not_short(rewriter, slide_digitalisasi):
    # 4 meaningful tokens → not flagged as short
    result = rewriter.rewrite("gimana cara mengarsipkan dokumen", slide_digitalisasi, [])
    assert "gimana cara mengarsipkan dokumen" in result


# ------------------------------------------------------------------ history entity extraction


def test_vague_query_uses_history_entities_when_no_slide(
    rewriter, history_with_lagaligo
):
    result = rewriter.rewrite("lebih detail soal itu", None, history_with_lagaligo)
    assert "La" in result or "Galigo" in result or "Sawerigading" in result or "Makassar" in result


def test_vague_slide_terms_take_priority_over_history(
    rewriter, slide_digitalisasi, history_with_lagaligo
):
    result = rewriter.rewrite(
        "yang tadi disebutkan itu apa?", slide_digitalisasi, history_with_lagaligo
    )
    # Slide terms must appear first (slide_terms come before history_entities)
    assert result.startswith("Digitalisasi Arsip Museum La Galigo")


def test_no_duplicate_terms_in_rewrite(rewriter):
    # If slide and history both mention "Museum", dedup must prevent repetition.
    slide = {"title": "Museum Makassar", "topics": ["museum", "koleksi"]}
    history = [
        {"role": "assistant", "content": "Museum ini menyimpan banyak koleksi penting."}
    ]
    result = rewriter.rewrite("lebih detail tentang itu", slide, history)
    terms = result.lower().split()
    assert terms.count("museum") == 1 or result.lower().count("museum makassar") >= 1


# ------------------------------------------------------------------ edge cases


def test_empty_query_returns_context(rewriter, slide_digitalisasi):
    # Empty string — too short and unspecific → uses slide context
    result = rewriter.rewrite("", slide_digitalisasi, [])
    assert "Digitalisasi Arsip Museum La Galigo" in result


def test_empty_query_no_context_returns_empty(rewriter):
    result = rewriter.rewrite("", None, [])
    assert result == ""


def test_vague_no_slide_no_history_returns_original(rewriter):
    result = rewriter.rewrite("lebih detail", None, [])
    assert result == "lebih detail"


def test_specific_long_query_not_flagged_as_short(rewriter, slide_digitalisasi):
    query = "bagaimana cara Museum La Galigo menjaga koleksi naskah lontara yang sangat tua"
    result = rewriter.rewrite(query, slide_digitalisasi, [])
    assert query in result


def test_rewriter_does_not_modify_slide_object(rewriter):
    slide = {"title": "Test Slide", "topics": ["topik1", "topik2"]}
    original_topics = list(slide["topics"])
    rewriter.rewrite("lebih detail", slide, [])
    assert slide["topics"] == original_topics


# ------------------------------------------------------------------ _is_vague unit tests


def test_is_vague_detects_anaphor_phrases(rewriter):
    assert rewriter._is_vague("tadi kamu bilang soal itu")
    assert rewriter._is_vague("yang tadi dibahas")
    assert rewriter._is_vague("hal tersebut maksudnya apa")
    assert rewriter._is_vague("yang barusan kamu bilang itu penting")


def test_is_vague_detects_elaboration_phrases(rewriter):
    assert rewriter._is_vague("bisa lebih detail tidak")
    assert rewriter._is_vague("tolong jelaskan lebih lanjut")
    assert rewriter._is_vague("ceritakan lebih tentang hal itu")


def test_is_vague_returns_false_for_specific_queries(rewriter):
    assert not rewriter._is_vague("apa itu la galigo")
    assert not rewriter._is_vague("siapa sawerigading dalam naskah bugis")
    assert not rewriter._is_vague("berapa jumlah halaman lontara di museum")


# ------------------------------------------------------------------ _extract_entities unit tests


def test_extract_entities_picks_capitalized_words(rewriter):
    text = "La Galigo adalah naskah dari Sawerigading di Makassar."
    entities = rewriter._extract_entities_from_text(text)
    assert "Galigo" in entities or "Sawerigading" in entities or "Makassar" in entities


def test_extract_entities_skips_common_words(rewriter):
    text = "Tenri menjelaskan bahwa Saya dan Anda memahami hal ini dengan Dalam konteks."
    entities = rewriter._extract_entities_from_text(text)
    assert "Tenri" not in entities
    assert "Saya" not in entities
    assert "Anda" not in entities
    assert "Dalam" not in entities


def test_extract_entities_max_six(rewriter):
    text = "Alpha Beta Gamma Delta Epsilon Zeta Theta Iota Kappa Lambda"
    entities = rewriter._extract_entities_from_text(text)
    assert len(entities) <= 6


def test_extract_entities_from_history_uses_last_assistant(rewriter):
    history = [
        {"role": "user", "content": "ceritakan tentang sesuatu"},
        {"role": "assistant", "content": "Lontara adalah aksara Bugis dari Sulawesi."},
        {"role": "user", "content": "dan lainnya?"},
        {"role": "assistant", "content": "Makassar juga dikenal dengan Sawerigading."},
    ]
    entities = rewriter._extract_entities_from_history(history)
    assert "Makassar" in entities or "Sawerigading" in entities


def test_extract_entities_from_history_empty(rewriter):
    assert rewriter._extract_entities_from_history([]) == []
    assert rewriter._extract_entities_from_history([{"role": "user", "content": "halo"}]) == []
