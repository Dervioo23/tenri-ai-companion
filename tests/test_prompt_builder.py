import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.core.prompt_builder import PromptBuilder
from app.config import Config

@pytest.fixture
def builder():
    return PromptBuilder()

def test_build_system_prompt(builder):
    system_prompt = builder.build_system_prompt()
    assert "Tenri" in system_prompt
    assert "ATURAN SISTEM" in system_prompt
    assert "CONTOH DIALOG TENRI" in system_prompt
    assert "saya perlu sedikit tidak setuju" in system_prompt
    assert "Jangan membuat kutipan palsu" in system_prompt

def test_build_messages_without_vision(builder):
    history = [{"role": "user", "content": "Halo"}, {"role": "assistant", "content": "Hai"}]
    user_input = "Apa kabar?"
    
    messages = builder.build_messages(user_input, history, vision_context=None)
    
    assert len(messages) == 4  # system + history (2) + current user
    assert messages[0]["role"] == "system"
    assert messages[1] == history[0]
    assert messages[2] == history[1]
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "Apa kabar?"

@patch('app.config.Config.VISION_ENABLED', True)
def test_build_messages_with_vision(builder):
    history = []
    user_input = "Halo"
    vision_context = {"face_detected": True, "face_count": 2, "motion_detected": True}

    messages = builder.build_messages(user_input, history, vision_context=vision_context)

    assert len(messages) == 2  # system + user
    assert messages[1]["role"] == "user"
    assert "2 wajah terdeteksi" in messages[1]["content"]
    assert "ada gerakan terdeteksi" in messages[1]["content"]
    assert "Halo" in messages[1]["content"]

def test_no_context_injects_grounding_warning(builder):
    messages = builder.build_messages("tes", [], no_context=True)
    system_content = messages[0]["content"]
    assert "TIDAK ADA KONTEKS RELEVAN" in system_content
    assert "jangan mengarang" in system_content

def test_no_context_false_does_not_inject_warning(builder):
    messages = builder.build_messages("tes", [], no_context=False)
    system_content = messages[0]["content"]
    assert "TIDAK ADA KONTEKS RELEVAN" not in system_content

def test_context_str_injected_into_system_prompt(builder):
    messages = builder.build_messages("tes", [], context_str="Ini adalah konteks dokumen.")
    system_content = messages[0]["content"]
    assert "KONTEKS RELEVAN" in system_content
    assert "Ini adalah konteks dokumen." in system_content
    assert "sebutkan sumbernya" in system_content

def test_slide_str_injected_into_system_prompt(builder):
    messages = builder.build_messages("tes", [], slide_str="[1/5] Pembukaan\nTopik: tenri")
    system_content = messages[0]["content"]
    assert "SLIDE AKTIF" in system_content
    assert "Pembukaan" in system_content

def test_narrative_str_injected_into_system_prompt(builder):
    narrative = "Presentasi berjalan: slide 2 dari 5. Sudah dibahas: Pembukaan."
    messages = builder.build_messages("tes", [], narrative_str=narrative)
    system_content = messages[0]["content"]
    assert "POSISI PRESENTASI" in system_content
    assert narrative in system_content

def test_grounding_rule_in_system_rules(builder):
    system_prompt = builder.build_system_prompt()
    assert "GROUNDING CHECK" in system_prompt


def test_build_wake_ack_messages_uses_minimal_prompt(builder):
    messages = builder.build_wake_ack_messages()
    system_content = messages[0]["content"]

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "Tenri"}
    assert "Presenter hanya memanggil namamu" in system_content
    assert "Jangan menjelaskan slide" in system_content
    assert "SLIDE AKTIF" not in system_content
    assert "KONTEKS RELEVAN" not in system_content
    assert "POSISI PRESENTASI" not in system_content


def test_build_slide_explanation_messages_uses_strict_slide_route(builder):
    messages = builder.build_slide_explanation_messages(
        "jelaskan slide ini",
        [],
        slide_str="[1/12] PENGENALAN TEKNOLOGI\nTopik: AI\nCatatan: AI membaca pola.",
        context_str="[1] AI adalah sistem yang belajar dari data.",
        narrative_str="Presentasi berjalan: slide 1 dari 12.",
    )
    system_content = messages[0]["content"]

    assert len(messages) == 2
    assert "MODE KHUSUS: JELASKAN SLIDE" in system_content
    assert "Ambil konsep inti" in system_content
    assert "Jelaskan maknanya" in system_content
    assert "Beri implikasi untuk audiens" in system_content
    assert "Jangan menyebut nomor slide" in system_content
    assert "Maksimal 2 kalimat" in system_content
    assert "KONTEKS RELEVAN" in system_content
    assert "Ikuti MODE KHUSUS: JELASKAN SLIDE" in messages[1]["content"]


@patch("app.core.prompt_builder.Config.LIVE_PROMPT_MODE", True)
def test_live_prompt_mode_uses_compact_system_prompt(builder):
    messages = builder.build_messages("Jelaskan slide ini", [])
    system_content = messages[0]["content"]

    assert "companion presentasi berbasis suara" in system_content
    assert "CONTOH DIALOG TENRI" not in system_content
    assert "sudut pandang utama" in system_content
    assert "definisi Wikipedia" in system_content
    assert "membacakan ulang judul" in system_content
    assert "Maksimal 3 kalimat" in system_content
