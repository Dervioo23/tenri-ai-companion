import pytest
from app.services.local_intent_classifier import (
    LocalIntentClassifier,
    _tokenize,
    _TRAINING_CORPUS,
    _MIN_CONFIDENCE,
)
from app.services.intent_classifier import IntentClassifier, Intent


# ------------------------------------------------------------------ fixtures

@pytest.fixture
def clf():
    return LocalIntentClassifier()


@pytest.fixture
def intent_classifier_with_local(monkeypatch):
    """IntentClassifier with LOCAL_INTENT_CLASSIFIER forced ON."""
    import app.config as config_module
    monkeypatch.setattr(config_module.Config, "LOCAL_INTENT_CLASSIFIER", True)
    return IntentClassifier()


@pytest.fixture
def intent_classifier_without_local(monkeypatch):
    """IntentClassifier with LOCAL_INTENT_CLASSIFIER forced OFF."""
    import app.config as config_module
    monkeypatch.setattr(config_module.Config, "LOCAL_INTENT_CLASSIFIER", False)
    return IntentClassifier()


# ------------------------------------------------------------------ LocalIntentClassifier.predict()

def test_predict_returns_tuple(clf):
    result = clf.predict("jadi proses ini membutuhkan waktu")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_predict_label_is_string(clf):
    label, _ = clf.predict("jadi proses ini membutuhkan waktu")
    assert isinstance(label, str)


def test_predict_confidence_is_float_in_range(clf):
    _, conf = clf.predict("jadi proses ini membutuhkan waktu")
    assert isinstance(conf, float)
    assert 0.0 <= conf <= 1.0


def test_predict_empty_returns_ambient_zero(clf):
    label, conf = clf.predict("")
    assert label == "ambient"
    assert conf == 0.0


def test_predict_only_stopwords_returns_ambient(clf):
    # Very short words filtered out by tokenizer (len ≤ 2)
    label, conf = clf.predict("ya di ke")
    assert label == "ambient"
    assert conf == 0.0


# ------------------------------------------------------------------ explaining detection (the main gap)

def test_short_explanation_opener_jadi(clf):
    """'jadi' opener with 8 words — normally AMBIENT by rule, should be EXPLAINING here."""
    label, conf = clf.predict("jadi proses ini memerlukan waktu yang lama")
    assert label == "explaining"
    assert conf >= _MIN_CONFIDENCE


def test_short_explanation_opener_maksudnya(clf):
    label, conf = clf.predict("maksudnya adalah data ini perlu diverifikasi")
    assert label == "explaining"
    assert conf >= _MIN_CONFIDENCE


def test_short_explanation_opener_artinya(clf):
    label, conf = clf.predict("artinya setiap naskah harus diperlakukan dengan hati-hati")
    assert label == "explaining"
    assert conf >= _MIN_CONFIDENCE


def test_short_explanation_opener_dalam_konteks(clf):
    label, conf = clf.predict("dalam konteks ini pelestarian sangat penting")
    assert label == "explaining"
    assert conf >= _MIN_CONFIDENCE


def test_short_explanation_opener_nah_jadi(clf):
    label, conf = clf.predict("nah jadi intinya adalah metadata yang terstruktur")
    assert label == "explaining"
    assert conf >= _MIN_CONFIDENCE


def test_short_explanation_opener_berdasarkan(clf):
    label, conf = clf.predict("berdasarkan penelitian ini hasilnya sangat signifikan")
    assert label == "explaining"
    assert conf >= _MIN_CONFIDENCE


# ------------------------------------------------------------------ ambient detection (true ambiguous short sentences)

def test_short_filler_hmm(clf):
    label, _ = clf.predict("hmm ya begitu saja")
    assert label == "ambient"


def test_short_filler_ya_betul(clf):
    label, _ = clf.predict("ya betul sekali memang")
    assert label == "ambient"


def test_short_filler_oh_oke(clf):
    label, _ = clf.predict("oh oke paham sudah")
    assert label == "ambient"


# ------------------------------------------------------------------ confidence threshold

def test_min_confidence_attribute_exists(clf):
    assert hasattr(clf, "min_confidence")
    assert clf.min_confidence == _MIN_CONFIDENCE


# ------------------------------------------------------------------ custom corpus

def test_custom_corpus_works():
    small_corpus = {
        "explaining": ["jadi ini adalah penjelasan tentang proses digitalisasi"],
        "ambient": ["hmm ya oke baik sudah paham"],
    }
    clf_custom = LocalIntentClassifier(corpus=small_corpus)
    label, conf = clf_custom.predict("jadi ini adalah contoh penjelasan")
    assert label == "explaining"


def test_empty_corpus_returns_ambient_zero():
    clf_empty = LocalIntentClassifier(corpus={})
    label, conf = clf_empty.predict("jadi ini penjelasan")
    assert label == "ambient"
    assert conf == 0.0


# ------------------------------------------------------------------ training corpus sanity

def test_corpus_has_required_categories():
    required = {"asking_tenri", "asking_audience", "explaining", "ambient"}
    assert required.issubset(set(_TRAINING_CORPUS.keys()))


def test_corpus_explaining_has_short_examples():
    # Ensure corpus contains examples that are < 15 words (the rule-based gap)
    explaining_examples = _TRAINING_CORPUS["explaining"]
    short_examples = [ex for ex in explaining_examples if len(ex.split()) < 15]
    assert len(short_examples) >= 5, "Corpus should have ≥5 short explaining examples"


def test_corpus_examples_are_non_empty():
    for category, examples in _TRAINING_CORPUS.items():
        assert len(examples) >= 5, f"Category '{category}' has fewer than 5 examples"
        for ex in examples:
            assert ex.strip(), f"Empty example found in '{category}'"


# ------------------------------------------------------------------ IntentClassifier integration


def test_integration_short_explanation_upgraded(intent_classifier_with_local):
    """Short explanation utterance (9 words, starts with 'jadi') → EXPLAINING via local fallback."""
    result = intent_classifier_with_local.classify(
        "jadi proses digitalisasi ini memerlukan waktu yang lama",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )
    assert result.intent == Intent.EXPLAINING


def test_integration_short_filler_stays_ambient(intent_classifier_with_local):
    """Filler phrase like 'hmm ya oke' stays AMBIENT even with local classifier active."""
    result = intent_classifier_with_local.classify(
        "hmm ya oke begitu",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )
    assert result.intent == Intent.AMBIENT


def test_integration_wake_word_not_overridden_by_local(intent_classifier_with_local):
    """Wake word → ASKING_TENRI must not be overridden by local classifier."""
    result = intent_classifier_with_local.classify(
        "Tenri jadi penjelasannya gimana",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )
    assert result.intent == Intent.ASKING_TENRI
    assert result.was_wake_word is True


@pytest.mark.parametrize(
    "utterance",
    [
        "dan sepulni, selamat menikmati",
        "baik kita lanjut ke bagian berikutnya",
        "oke teman-teman sekarang kita masuk ke materi berikutnya",
        "silakan menyimak bagian ini",
    ],
)
def test_stage_transition_is_blocked_even_in_conversation_window(intent_classifier_with_local, utterance):
    result = intent_classifier_with_local.classify(
        utterance,
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=True,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_AUDIENCE
    assert "Stage transition" in result.reason


def test_wake_word_still_overrides_stage_transition(intent_classifier_with_local):
    result = intent_classifier_with_local.classify(
        "Tenri, lanjutkan penjelasan slide ini",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=True,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert result.was_wake_word is True


def test_conversation_window_statement_now_engages(intent_classifier_with_local):
    # Hybrid model: inside an open conversation a plain statement (no narration
    # opener, not a monologue) is treated as addressed to Tenri and answered,
    # not silenced as before.
    result = intent_classifier_with_local.classify(
        "data ini cukup jelas sebenarnya",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=True,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert "Conversation engagement" in result.reason


@pytest.mark.parametrize(
    "utterance",
    [
        "jelaskan lebih detail",
        "maksudnya gimana",
        "beri contoh",
        "perjelas bagian itu",
        "memangnya seperti apa yang dibayangkan itu",
        "seperti apa itu",
        "yang mana tadi",
        "kok bisa begitu",
        "berarti apa",
    ],
)
def test_conversation_window_clear_followup_answers(intent_classifier_with_local, utterance):
    result = intent_classifier_with_local.classify(
        utterance,
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=True,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert result.was_wake_word is False


def test_conversation_followup_not_overridden_by_local_explaining(intent_classifier_with_local):
    result = intent_classifier_with_local.classify(
        "Memangnya seperti apa yang dibayangkan itu",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=True,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert "Conversation follow-up signal" in result.reason
    assert "question word 'memangnya'" in result.reason


def test_conversation_followup_reason_mentions_reference_signal(intent_classifier_with_local):
    result = intent_classifier_with_local.classify(
        "bagian itu",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=True,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert "reference follow-up" in result.reason


def test_conversation_narration_opener_stays_silent(intent_classifier_with_local):
    # Even mid-conversation, an explain opener ("jadi ...") marks audience
    # narration, so Tenri stays silent instead of interrupting the presentation.
    result = intent_classifier_with_local.classify(
        "jadi proses digitalisasi ini memerlukan waktu yang lama",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=True,
        quiet_mode=False,
    )

    assert result.intent == Intent.EXPLAINING
    assert result.reason.startswith("Conversation narration opener")


def test_clarification_question_outside_conversation_is_still_answered(intent_classifier_with_local):
    result = intent_classifier_with_local.classify(
        "Memangnya seperti apa yang dibayangkan itu",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert "Question bypass" in result.reason


@pytest.mark.parametrize(
    "utterance",
    [
        "Jelaskan slide pertama ini",
        "jelaskan bagian ini",
        "perjelas poin kedua",
        "ringkas materi slide ini",
    ],
)
def test_direct_presentation_command_answers_without_wake_word(intent_classifier_with_local, utterance):
    result = intent_classifier_with_local.classify(
        utterance,
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert "Direct presentation command" in result.reason


@pytest.mark.parametrize(
    "utterance",
    [
        "music",
        "thanks for watching",
        "subscribe",
        "buk buk buk",
    ],
)
def test_stt_noise_is_blocked(intent_classifier_with_local, utterance):
    result = intent_classifier_with_local.classify(
        utterance,
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=True,
        quiet_mode=False,
    )

    assert result.intent == Intent.NOISE


def test_integration_long_sentence_still_explaining_without_local(intent_classifier_without_local):
    """Long sentences still hit EXPLAINING via rule-based path (no local classifier).

    Note: must NOT contain question words ('jelaskan', 'apa', 'bagaimana', etc.)
    or the rule-based question bypass would intercept it first.
    """
    long_sentence = (
        "pada bagian ini saya akan membahas secara rinci proses digitalisasi "
        "naskah lontara yang ada di museum"
    )
    result = intent_classifier_without_local.classify(
        long_sentence,
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )
    assert result.intent == Intent.EXPLAINING


def test_integration_local_off_short_explanation_is_ambient(intent_classifier_without_local):
    """With LOCAL_INTENT_CLASSIFIER=False, short explanation stays AMBIENT (rule gap unchanged)."""
    result = intent_classifier_without_local.classify(
        "jadi proses digitalisasi ini memerlukan waktu",
        wake_words=["tenri"],
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )
    # Without local classifier, short sentences fall through to AMBIENT
    assert result.intent == Intent.AMBIENT


# ------------------------------------------------------------------ _tokenize unit tests

def test_tokenize_lowercases_and_strips_punct():
    result = _tokenize("Jadi, Proses! Ini.")
    assert all(t == t.lower() for t in result)
    assert "jadi" in result
    assert "proses" in result


def test_tokenize_filters_tokens_le_2_chars():
    result = _tokenize("di la ya ke ini itu")
    for t in result:
        assert len(t) > 2


def test_tokenize_empty_string():
    assert _tokenize("") == []


def test_tokenize_all_short_words():
    assert _tokenize("ya di ke la") == []


# ------------------------------------------------------------------ wake word boundary (BUG-01)

_WAKE_WORDS = [
    "tenri", "halo tenri", "hallo tenri", "hai tenri", "hi tenri",
    "oke tenri", "ok tenri", "hey tenri", "eh tenri",
]


@pytest.mark.parametrize(
    "utterance",
    [
        "kisah we tenriabeng sangat menarik",
        "tokoh tenriabeng dalam la galigo",
        "naskah ini menyebut tenriabeng",
    ],
)
def test_wake_word_not_matched_inside_other_word(intent_classifier_with_local, utterance):
    """'tenri' inside 'Tenriabeng' must NOT be treated as a wake call (BUG-01)."""
    result = intent_classifier_with_local.classify(
        utterance,
        wake_words=_WAKE_WORDS,
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )
    assert result.was_wake_word is False
    assert result.intent != Intent.ASKING_TENRI


def test_wake_word_standalone_still_detected(intent_classifier_with_local):
    """A real wake call must still be detected and its query extracted."""
    result = intent_classifier_with_local.classify(
        "Tenri jelaskan slide ini",
        wake_words=_WAKE_WORDS,
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )
    assert result.was_wake_word is True
    assert result.intent == Intent.ASKING_TENRI
    assert result.query == "jelaskan slide ini"


def test_multiword_wake_extracts_query_after_wake(intent_classifier_with_local):
    """Multi-word wake ('halo tenri') matches before bare 'tenri' and strips cleanly."""
    result = intent_classifier_with_local.classify(
        "Halo Tenri, apa itu lontara",
        wake_words=_WAKE_WORDS,
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )
    assert result.was_wake_word is True
    assert result.query == "apa itu lontara"


def test_wake_word_at_end_preserves_question_before_it(intent_classifier_with_local):
    result = intent_classifier_with_local.classify(
        "Apa itu kecerdasan buatan, Tenri?",
        wake_words=_WAKE_WORDS,
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert result.was_wake_word is True
    assert result.query == "Apa itu kecerdasan buatan"


def test_wake_word_in_middle_preserves_both_query_sides(intent_classifier_with_local):
    result = intent_classifier_with_local.classify(
        "Jelaskan slide ini Tenri sekarang",
        wake_words=_WAKE_WORDS,
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert result.was_wake_word is True
    assert result.query == "Jelaskan slide ini sekarang"


def test_wake_word_only_keeps_empty_query(intent_classifier_with_local):
    result = intent_classifier_with_local.classify(
        "Tenri",
        wake_words=_WAKE_WORDS,
        audience_markers=frozenset(),
        closing_phrases=frozenset(),
        in_conversation=False,
        quiet_mode=False,
    )

    assert result.intent == Intent.ASKING_TENRI
    assert result.was_wake_word is True
    assert result.query == ""
