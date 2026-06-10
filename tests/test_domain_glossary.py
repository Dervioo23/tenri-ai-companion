import pytest
from app.services.speech_service import SpeechService, _DOMAIN_GLOSSARY, _DOMAIN_GLOSSARY_PATTERNS


# ------------------------------------------------------------------ glossary content

def test_glossary_has_la_galigo_variants() -> None:
    assert "la gaigo" in _DOMAIN_GLOSSARY
    assert "la galligo" in _DOMAIN_GLOSSARY
    assert "lagaligo" in _DOMAIN_GLOSSARY


def test_glossary_has_sawerigading_variants() -> None:
    assert "sawe rigading" in _DOMAIN_GLOSSARY
    assert "saweri gading" in _DOMAIN_GLOSSARY


def test_glossary_has_tursalahjalan_variants() -> None:
    assert "tursa la jalan" in _DOMAIN_GLOSSARY
    assert "tursa lah jalan" in _DOMAIN_GLOSSARY


def test_glossary_canonical_values_are_correct() -> None:
    assert _DOMAIN_GLOSSARY["la gaigo"] == "La Galigo"
    assert _DOMAIN_GLOSSARY["saweri gading"] == "Sawerigading"
    assert _DOMAIN_GLOSSARY["tursa la jalan"] == "tursalahjalan"
    assert _DOMAIN_GLOSSARY["makasar"] == "Makassar"
    assert _DOMAIN_GLOSSARY["macassar"] == "Makassar"
    assert _DOMAIN_GLOSSARY["lontaraq"] == "lontara"


def test_patterns_sorted_longest_first() -> None:
    # Frasa panjang harus dicoba lebih dulu agar tidak terpotong oleh frasa pendek.
    # Ukur dengan panjang key asli (bukan pattern string — re.escape() menambah char ekstra).
    key_lengths = []
    for pattern, _ in _DOMAIN_GLOSSARY_PATTERNS:
        for key in _DOMAIN_GLOSSARY:
            if pattern.fullmatch(key):
                key_lengths.append(len(key))
                break
    assert key_lengths == sorted(key_lengths, reverse=True)


# ------------------------------------------------------------------ _apply_domain_glossary

@pytest.mark.parametrize("wrong, correct", [
    ("la gaigo", "La Galigo"),
    ("la galligo", "La Galigo"),
    ("la goligo", "La Galigo"),
    ("lagaligo", "La Galigo"),
    ("sawe rigading", "Sawerigading"),
    ("saweri gading", "Sawerigading"),
    ("sawerigadig", "Sawerigading"),
    ("tursa la jalan", "tursalahjalan"),
    ("tursa lah jalan", "tursalahjalan"),
    ("tursalah jalan", "tursalahjalan"),
    ("lon tara", "lontara"),
    ("lontaraq", "lontara"),
    ("makasar", "Makassar"),
    ("macassar", "Makassar"),
    ("we tenri abeng", "We Tenriabeng"),
])
def test_apply_domain_glossary_corrects_term(wrong: str, correct: str) -> None:
    result = SpeechService._apply_domain_glossary(wrong)
    assert result == correct


def test_apply_domain_glossary_case_insensitive() -> None:
    assert SpeechService._apply_domain_glossary("LA GAIGO") == "La Galigo"
    assert SpeechService._apply_domain_glossary("La Gaigo") == "La Galigo"
    assert SpeechService._apply_domain_glossary("SAWERI GADING") == "Sawerigading"
    assert SpeechService._apply_domain_glossary("Makasar") == "Makassar"


def test_apply_domain_glossary_preserves_surrounding_text() -> None:
    result = SpeechService._apply_domain_glossary(
        "presentasi ini membahas la gaigo sebagai warisan budaya"
    )
    assert result == "presentasi ini membahas La Galigo sebagai warisan budaya"


def test_apply_domain_glossary_multiple_terms_in_one_sentence() -> None:
    result = SpeechService._apply_domain_glossary(
        "la gaigo ditulis oleh saweri gading dan disimpan di tursalah jalan"
    )
    assert "La Galigo" in result
    assert "Sawerigading" in result
    assert "tursalahjalan" in result


def test_apply_domain_glossary_does_not_alter_correct_text() -> None:
    correct = "La Galigo adalah naskah epik terpanjang di dunia."
    assert SpeechService._apply_domain_glossary(correct) == correct


def test_apply_domain_glossary_does_not_match_substrings() -> None:
    # "gading" by itself should not trigger "saweri gading" → "Sawerigading"
    result = SpeechService._apply_domain_glossary("gading adalah warna putih")
    assert result == "gading adalah warna putih"


def test_apply_domain_glossary_empty_string() -> None:
    assert SpeechService._apply_domain_glossary("") == ""


# ------------------------------------------------------------------ normalize_transcription integration

def test_normalize_transcription_applies_glossary_after_tenri_fix() -> None:
    # Tenri salah tulis + La Galigo salah tulis dalam satu kalimat
    result = SpeechService.normalize_transcription(
        "Tendi, jelaskan la gaigo kepada saya"
    )
    assert "Tenri" in result
    assert "La Galigo" in result
    assert "la gaigo" not in result
    assert "Tendi" not in result


def test_normalize_transcription_glossary_standalone() -> None:
    result = SpeechService.normalize_transcription("ceritakan tentang saweri gading")
    assert result == "ceritakan tentang Sawerigading"


def test_normalize_transcription_no_change_for_correct_text() -> None:
    text = "Tenri, apa itu La Galigo?"
    assert SpeechService.normalize_transcription(text) == text
