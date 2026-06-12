"""Hybrid addressee model: inside an open conversation (opened by name), Tenri
engages with statements/debate too — but stays silent on audience narration, and
the engagement is strictly window-scoped (no name -> no engagement)."""

from app.services.intent_classifier import Intent, IntentClassifier

_WAKE = ["tenri", "halo tenri"]
_AUDIENCE = frozenset({"teman-teman", "hadirin", "kalian"})
_CLOSING = frozenset({"terima kasih", "makasih", "cukup"})


def _classify(text: str, *, in_conversation: bool, quiet_mode: bool = False):
    return IntentClassifier().classify(
        text,
        wake_words=_WAKE,
        audience_markers=_AUDIENCE,
        closing_phrases=_CLOSING,
        in_conversation=in_conversation,
        quiet_mode=quiet_mode,
    )


# ------------------------------------------------------------ engage inside window

def test_debate_statement_in_conversation_is_answered():
    # No question word, no wake word — pure opinion/debate addressed to Tenri.
    result = _classify("Menurut saya kecerdasan buatan justru berbahaya", in_conversation=True)
    assert result.intent is Intent.ASKING_TENRI


def test_plain_statement_in_conversation_is_answered():
    result = _classify("AI akan menggantikan banyak pekerjaan manusia", in_conversation=True)
    assert result.intent is Intent.ASKING_TENRI


def test_question_in_conversation_still_answered():
    result = _classify("Kenapa AI penting?", in_conversation=True)
    assert result.intent is Intent.ASKING_TENRI


# ------------------------------------------------------------ stay silent on narration

def test_audience_marker_in_conversation_stays_silent():
    result = _classify("Baik teman-teman mari kita lihat bersama", in_conversation=True)
    assert result.intent is Intent.ASKING_AUDIENCE


def test_long_monologue_in_conversation_stays_silent():
    # >=15-word narration with an explain opener — presenter talking, not asking.
    monologue = (
        "Jadi pada dasarnya teknologi ini sudah berkembang sangat pesat sejak "
        "beberapa tahun terakhir di banyak sektor industri besar dunia"
    )
    result = _classify(monologue, in_conversation=True)
    assert result.intent is Intent.EXPLAINING


# ------------------------------------------------------------ window-scoped (the crux)

def test_debate_statement_outside_conversation_stays_silent():
    # Identical opinion, but no conversation open (name not called) -> NOT answered.
    result = _classify("Menurut saya kecerdasan buatan justru berbahaya", in_conversation=False)
    assert result.intent is not Intent.ASKING_TENRI


def test_name_call_opens_then_engages():
    # The name itself routes to ASKING_TENRI (wake), which is what opens the window.
    opened = _classify("Tenri", in_conversation=False)
    assert opened.intent is Intent.ASKING_TENRI and opened.was_wake_word


# ------------------------------------------------------------ closing the conversation

def _classify_closing(text: str, *, in_conversation: bool):
    # Use the real production closing set so these stay in sync with the app.
    from app.core.interaction_loop import _CLOSING_PHRASES
    return IntentClassifier().classify(
        text,
        wake_words=_WAKE,
        audience_markers=_AUDIENCE,
        closing_phrases=_CLOSING_PHRASES,
        in_conversation=in_conversation,
        quiet_mode=False,
    )


import pytest


@pytest.mark.parametrize("phrase", [
    "terima kasih", "makasih", "oke terima kasih", "terima kasih ya",
    "cukup", "sudah cukup", "sekian", "segitu dulu", "oke deh", "udahan",
])
def test_closing_phrases_close_conversation(phrase):
    result = _classify_closing(phrase, in_conversation=True)
    assert result.intent is Intent.CLOSING_TENRI


def test_closing_phrase_outside_conversation_does_not_close():
    # "terima kasih" with no open conversation and no name is not a close signal.
    result = _classify_closing("terima kasih", in_conversation=False)
    assert result.intent is not Intent.CLOSING_TENRI
