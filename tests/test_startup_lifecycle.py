import threading
from unittest.mock import patch

import pytest

import main as app_main
from app.core.interaction_loop import InteractionLoop
from app.ui.jarvis_display import JarvisDisplay


def test_invalid_config_blocks_services_before_initialization() -> None:
    with (
        patch(
            "app.core.interaction_loop.Config.validate_critical_configs",
            return_value=(["LLM_PROVIDER tidak valid"], []),
        ),
        patch("app.core.interaction_loop.GroqService") as groq_service,
    ):
        with pytest.raises(ValueError, match="Invalid Tenri configuration"):
            InteractionLoop()

    groq_service.assert_not_called()


def test_main_preflight_blocks_interaction_loop_on_invalid_config() -> None:
    with (
        patch.object(
            app_main.Config,
            "validate_critical_configs",
            return_value=(["LLM_PROVIDER tidak valid"], []),
        ),
        patch.object(app_main, "InteractionLoop") as interaction_loop,
        patch.object(app_main, "setup_logger"),
    ):
        app_main._run_tenri()

    interaction_loop.assert_not_called()


def test_jarvis_display_start_runs_render_loop_on_main_thread() -> None:
    display = JarvisDisplay()

    with patch.object(display, "_render_loop") as render_loop:
        display.start()

    render_loop.assert_called_once_with(on_quit=None)


def test_jarvis_display_rejects_non_main_thread() -> None:
    display = JarvisDisplay()
    errors: list[Exception] = []

    def _start_display() -> None:
        try:
            display.start()
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=_start_display)
    worker.start()
    worker.join(timeout=2.0)

    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert "main thread" in str(errors[0])
