import json
from pathlib import Path
from unittest.mock import patch

from scripts import manage_knowledge


def test_slugify_title() -> None:
    assert manage_knowledge.slugify("La Galigo Paper!") == "la-galigo-paper"


def test_add_replace_disable_enable_source(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    sources_path = knowledge_dir / "sources.json"
    source_file = tmp_path / "paper.md"
    replacement_file = tmp_path / "paper_revised.md"
    source_file.write_text("first version", encoding="utf-8")
    replacement_file.write_text("second version", encoding="utf-8")

    with (
        patch.object(manage_knowledge, "KNOWLEDGE_DIR", knowledge_dir),
        patch.object(manage_knowledge, "SOURCES_PATH", sources_path),
    ):
        source = manage_knowledge.add_source("paper", "La Galigo Paper", source_file)
        assert source["id"] == "la-galigo-paper"
        assert source["active_version"] == "v1"
        assert (knowledge_dir / source["versions"][0]["path"]).exists()

        replaced = manage_knowledge.replace_source("la-galigo-paper", replacement_file)
        assert replaced["active_version"] == "v2"
        assert replaced["versions"][0]["status"] == "archived"
        assert replaced["versions"][1]["status"] == "active"

        disabled = manage_knowledge.disable_source("la-galigo-paper")
        assert disabled["status"] == "disabled"

        enabled = manage_knowledge.enable_source("la-galigo-paper")
        assert enabled["status"] == "active"

        data = json.loads(sources_path.read_text(encoding="utf-8"))
        assert data[0]["id"] == "la-galigo-paper"
