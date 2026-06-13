"""Smoke + behavior tests for the Tenri web backend (Phase 0).

Exercises the reused brain through the real FastAPI endpoints — no network, no
keys, no audio. Skips cleanly if FastAPI isn't installed.
"""

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["slides"] >= 1
    assert body["chunks"] >= 1
    assert body["live_model"]


def test_route_empty_is_ignored():
    r = client.post("/route", json={"transcript": "   ", "slide_index": 0})
    assert r.json()["action"] == "ignore"


def test_route_slide_explanation_returns_grounded_prompt():
    r = client.post("/route", json={
        "transcript": "jelaskan slide ini",
        "slide_index": 0,
        "history": [],
        "in_conversation": False,
        "quiet_mode": False,
    })
    body = r.json()
    assert body["action"] == "answer"
    assert body["messages"] and body["messages"][0]["role"] == "system"
    assert body["llm"]["model"]
    assert body["llm"]["max_tokens"] >= 1
    # The browser will send messages to Groq with the user's key; we just shape it.


def test_route_wake_word_is_ack():
    r = client.post("/route", json={"transcript": "Tenri", "slide_index": 0})
    body = r.json()
    assert body["action"] == "wake_ack"
    assert body["text"]
    assert body["extend_window"] is True


def test_route_navigation_changes_slide_silently():
    r = client.post("/route", json={"transcript": "lanjut", "slide_index": 0})
    body = r.json()
    assert body["action"] == "navigate"
    assert body["slide_index"] == 1


def test_route_closing_in_conversation_closes():
    r = client.post("/route", json={
        "transcript": "terima kasih",
        "slide_index": 0,
        "in_conversation": True,
    })
    body = r.json()
    assert body["action"] == "close"
    assert body["set_quiet"] is True


def test_route_debate_in_conversation_engages():
    # Hybrid addressee model carries over: a statement inside the window is answered.
    r = client.post("/route", json={
        "transcript": "menurut saya kecerdasan buatan justru berbahaya",
        "slide_index": 0,
        "in_conversation": True,
    })
    assert r.json()["action"] == "answer"


def test_verify_passes_grounded_and_blocks_ungrounded():
    context = (
        "[1] Kecerdasan buatan adalah cabang ilmu komputer yang membuat mesin "
        "meniru kemampuan berpikir manusia, belajar dari data dan mengenali pola."
    )
    grounded = client.post("/verify", json={
        "response": "Kecerdasan buatan membuat mesin meniru cara berpikir manusia.",
        "context_str": context,
    }).json()
    assert grounded["overridden"] is False

    ungrounded = client.post("/verify", json={
        "response": "Python adalah bahasa pemrograman populer untuk data science.",
        "context_str": context,
    }).json()
    assert ungrounded["overridden"] is True
