import json
from pathlib import Path


PRESENTATION_DIR = Path(__file__).resolve().parent.parent / "app" / "presentation"


def test_trigger_slide_ids_exist_in_slides_json() -> None:
    slides = json.loads((PRESENTATION_DIR / "slides.json").read_text(encoding="utf-8"))
    triggers = json.loads((PRESENTATION_DIR / "triggers.json").read_text(encoding="utf-8"))
    slide_ids = {slide["id"] for slide in slides}

    missing_refs = [
        (trigger.get("id"), slide_id)
        for trigger in triggers
        for slide_id in trigger.get("slide_ids", [])
        if slide_id not in slide_ids
    ]

    assert missing_refs == []


def test_slide_ids_are_unique() -> None:
    slides = json.loads((PRESENTATION_DIR / "slides.json").read_text(encoding="utf-8"))
    slide_ids = [slide["id"] for slide in slides]

    assert len(slide_ids) == len(set(slide_ids))
