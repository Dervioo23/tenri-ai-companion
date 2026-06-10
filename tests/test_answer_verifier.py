import pytest
from app.services.answer_verifier import AnswerVerifier, _FALLBACK_RESPONSE, _cosine_similarity, _tokenize


@pytest.fixture
def verifier():
    return AnswerVerifier(threshold=0.4)


@pytest.fixture
def context_lagaligo():
    return (
        "[1] Koleksi Museum La Galigo — Naskah\n"
        "La Galigo adalah naskah epik terpanjang di dunia, berasal dari tradisi Bugis "
        "Sulawesi Selatan. Naskah ini ditulis dalam aksara lontara dan menceritakan "
        "perjalanan Sawerigading, putra mahkota Kerajaan Luwu."
    )


@pytest.fixture
def context_digitalisasi():
    return (
        "[1] Arsip Digital — Pelestarian\n"
        "Proses digitalisasi arsip melibatkan pemindaian naskah lontara menggunakan "
        "perangkat resolusi tinggi. Metadata setiap dokumen disimpan dalam database "
        "untuk memudahkan pencarian dan pelestarian jangka panjang."
    )


# ------------------------------------------------------------------ grounded responses (pass)


def test_grounded_response_passes(verifier, context_lagaligo):
    response = "La Galigo adalah naskah epik dari tradisi Bugis yang ditulis dalam lontara."
    result, overridden = verifier.check(response, context_lagaligo)
    assert not overridden
    assert result == response


def test_grounded_response_uses_domain_terms(verifier, context_digitalisasi):
    response = "Digitalisasi naskah menggunakan pemindaian untuk pelestarian arsip."
    result, overridden = verifier.check(response, context_digitalisasi)
    assert not overridden
    assert result == response


def test_partially_grounded_response_passes(verifier, context_lagaligo):
    # Response shares key domain terms (Sawerigading, naskah) — should pass
    response = "Sawerigading adalah tokoh utama dalam naskah epik tersebut."
    result, overridden = verifier.check(response, context_lagaligo)
    assert not overridden


# ------------------------------------------------------------------ ungrounded responses (fail)


def test_ungrounded_response_overridden(verifier, context_lagaligo):
    # Response uses completely different vocabulary — low similarity
    response = "Python adalah bahasa pemrograman yang populer untuk data science."
    result, overridden = verifier.check(response, context_lagaligo)
    assert overridden
    assert result == _FALLBACK_RESPONSE


def test_generic_response_overridden(verifier, context_digitalisasi):
    # Vague response with no context terms
    response = "Iya, itu sangat menarik dan perlu dipertimbangkan lebih lanjut."
    result, overridden = verifier.check(response, context_digitalisasi)
    assert overridden
    assert result == _FALLBACK_RESPONSE


def test_common_words_do_not_create_false_grounding(verifier):
    context = "Ini adalah konteks tentang arsip dan dokumen museum."
    response = "Ini adalah hal yang bisa dilakukan dengan baik."

    result, overridden = verifier.check(response, context)

    assert overridden
    assert result == _FALLBACK_RESPONSE


# ------------------------------------------------------------------ skip conditions


def test_empty_context_skips_check(verifier):
    response = "Ini adalah respons tanpa konteks."
    result, overridden = verifier.check(response, "")
    assert not overridden
    assert result == response


def test_empty_response_skips_check(verifier, context_lagaligo):
    result, overridden = verifier.check("", context_lagaligo)
    assert not overridden
    assert result == ""


def test_both_empty_skips_check(verifier):
    result, overridden = verifier.check("", "")
    assert not overridden
    assert result == ""


def test_fallback_text_as_input_skips_check(verifier, context_lagaligo):
    # Prevent infinite loop — if response is already the fallback, don't recheck
    result, overridden = verifier.check(_FALLBACK_RESPONSE, context_lagaligo)
    assert not overridden
    assert result == _FALLBACK_RESPONSE


def test_offline_mode_response_skips_check(verifier, context_lagaligo):
    response = "[Offline Mode] Batas token harian Groq tercapai."
    result, overridden = verifier.check(response, context_lagaligo)
    assert not overridden
    assert result == response


# ------------------------------------------------------------------ return type and tuple shape


def test_returns_tuple_of_two(verifier, context_lagaligo):
    result = verifier.check("La Galigo adalah naskah Bugis.", context_lagaligo)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_was_overridden_is_bool(verifier, context_lagaligo):
    _, overridden = verifier.check("La Galigo adalah naskah Bugis.", context_lagaligo)
    assert isinstance(overridden, bool)


# ------------------------------------------------------------------ custom threshold


def test_custom_high_threshold_overrides_borderline(context_lagaligo):
    strict = AnswerVerifier(threshold=0.99)
    response = "La Galigo adalah naskah epik dari Bugis."
    _, overridden = strict.check(response, context_lagaligo)
    # Very high threshold — even a decent match gets flagged
    assert overridden


def test_custom_zero_threshold_never_overrides(context_lagaligo):
    permissive = AnswerVerifier(threshold=0.0)
    response = "Xyz qrs abc def — completely unrelated."
    _, overridden = permissive.check(response, context_lagaligo)
    assert not overridden


# ------------------------------------------------------------------ _cosine_similarity unit tests


def test_cosine_identical_tokens():
    tokens = ["naskah", "lontara", "bugis", "sulawesi"]
    assert _cosine_similarity(tokens, tokens) == pytest.approx(1.0, abs=1e-6)


def test_cosine_zero_overlap():
    a = ["python", "programming", "function"]
    b = ["naskah", "lontara", "bugis"]
    assert _cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)


def test_cosine_partial_overlap():
    a = ["naskah", "bugis", "python"]
    b = ["naskah", "bugis", "lontara"]
    sim = _cosine_similarity(a, b)
    assert 0.0 < sim < 1.0


def test_cosine_empty_a():
    assert _cosine_similarity([], ["naskah", "lontara"]) == 0.0


def test_cosine_empty_b():
    assert _cosine_similarity(["naskah", "lontara"], []) == 0.0


def test_cosine_both_empty():
    assert _cosine_similarity([], []) == 0.0


# ------------------------------------------------------------------ _tokenize unit tests


def test_tokenize_lowercases():
    result = _tokenize("La Galigo NASKAH")
    assert all(t == t.lower() for t in result)


def test_tokenize_strips_punctuation():
    result = _tokenize("naskah, lontara. bugis!")
    assert "naskah" in result
    assert "lontara" in result
    assert "bugis" in result


def test_tokenize_skips_short_tokens():
    # Tokens ≤ 2 chars should be excluded
    result = _tokenize("di la ini itu La Galigo")
    assert "la" not in result
    assert "di" not in result
    assert "galigo" in result


def test_tokenize_empty():
    assert _tokenize("") == []
