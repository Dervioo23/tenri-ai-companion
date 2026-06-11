from unittest.mock import AsyncMock, MagicMock, patch

from app.services.local_tts_service import LocalTTSService


def make_service(available: bool = True, voice: str = "id-ID-GadisNeural") -> LocalTTSService:
    service = LocalTTSService.__new__(LocalTTSService)
    service.available = available
    service._voice = voice
    service._engine = "edge"
    service._sapi_available = False
    service._edge_available = available
    return service


# ------------------------------------------------------------------ init guards

def test_local_tts_disabled_when_flag_false() -> None:
    service = LocalTTSService.__new__(LocalTTSService)
    with patch("app.services.local_tts_service.Config.LOCAL_TTS_ENABLED", False):
        service.__init__()
    assert service.available is False


def test_local_tts_ready_when_edge_tts_importable() -> None:
    service = LocalTTSService.__new__(LocalTTSService)
    fake_edge_tts = MagicMock()
    with (
        patch("app.services.local_tts_service.Config.LOCAL_TTS_ENABLED", True),
        patch("app.services.local_tts_service.Config.LOCAL_TTS_VOICE", "id-ID-GadisNeural"),
        patch.dict("sys.modules", {"edge_tts": fake_edge_tts}),
    ):
        service.__init__()
    assert service.available is True
    assert service._edge_available is True


def test_local_tts_unavailable_when_edge_tts_not_installed() -> None:
    service = LocalTTSService.__new__(LocalTTSService)
    with (
        patch("app.services.local_tts_service.Config.LOCAL_TTS_ENABLED", True),
        patch("app.services.local_tts_service.sys.platform", "linux"),
        patch.dict("sys.modules", {"edge_tts": None}),
    ):
        service.__init__()
    assert service.available is False


def test_local_tts_ready_on_windows_even_without_edge_tts() -> None:
    service = LocalTTSService.__new__(LocalTTSService)
    with (
        patch("app.services.local_tts_service.Config.LOCAL_TTS_ENABLED", True),
        patch("app.services.local_tts_service.sys.platform", "win32"),
        patch.dict("sys.modules", {"edge_tts": None}),
    ):
        service.__init__()
    assert service.available is True
    assert service._sapi_available is True


def test_local_tts_voice_defaults_to_gadis_neural() -> None:
    service = LocalTTSService.__new__(LocalTTSService)
    fake_edge_tts = MagicMock()
    with (
        patch("app.services.local_tts_service.Config.LOCAL_TTS_ENABLED", True),
        patch("app.services.local_tts_service.Config.LOCAL_TTS_VOICE", ""),
        patch.dict("sys.modules", {"edge_tts": fake_edge_tts}),
    ):
        service.__init__()
    assert service._voice == "id-ID-GadisNeural"


# ------------------------------------------------------------------ synthesize guards

def test_synthesize_returns_none_when_not_available() -> None:
    service = make_service(available=False)
    assert service.synthesize("Halo Tenri") is None


def test_synthesize_returns_none_for_empty_text() -> None:
    service = make_service()
    assert service.synthesize("") is None
    assert service.synthesize("   ") is None


# ------------------------------------------------------------------ synthesize happy path

def test_synthesize_calls_edge_tts_communicate(tmp_path) -> None:
    service = make_service(voice="id-ID-GadisNeural")

    mock_communicate = MagicMock()
    mock_communicate.save = AsyncMock()
    mock_edge_tts = MagicMock()
    mock_edge_tts.Communicate.return_value = mock_communicate

    with (
        patch("app.services.local_tts_service.Config.TEMP_DIR", tmp_path),
        patch.dict("sys.modules", {"edge_tts": mock_edge_tts}),
    ):
        result = service.synthesize("Halo Tenri")

    mock_edge_tts.Communicate.assert_called_once_with("Halo Tenri", "id-ID-GadisNeural")
    mock_communicate.save.assert_awaited_once()
    assert result is not None
    assert result.endswith(".mp3")


def test_synthesize_strips_whitespace_from_text(tmp_path) -> None:
    service = make_service()

    mock_communicate = MagicMock()
    mock_communicate.save = AsyncMock()
    mock_edge_tts = MagicMock()
    mock_edge_tts.Communicate.return_value = mock_communicate

    with (
        patch("app.services.local_tts_service.Config.TEMP_DIR", tmp_path),
        patch.dict("sys.modules", {"edge_tts": mock_edge_tts}),
    ):
        service.synthesize("  Halo Tenri  ")

    mock_edge_tts.Communicate.assert_called_once_with("Halo Tenri", service._voice)


def test_synthesize_uses_configured_voice(tmp_path) -> None:
    service = make_service(voice="id-ID-ArdiNeural")

    mock_communicate = MagicMock()
    mock_communicate.save = AsyncMock()
    mock_edge_tts = MagicMock()
    mock_edge_tts.Communicate.return_value = mock_communicate

    with (
        patch("app.services.local_tts_service.Config.TEMP_DIR", tmp_path),
        patch.dict("sys.modules", {"edge_tts": mock_edge_tts}),
    ):
        service.synthesize("Halo")

    mock_edge_tts.Communicate.assert_called_once_with("Halo", "id-ID-ArdiNeural")


# ------------------------------------------------------------------ error handling

def test_synthesize_returns_none_on_exception(tmp_path) -> None:
    service = make_service()

    mock_communicate = MagicMock()
    mock_communicate.save = AsyncMock(side_effect=RuntimeError("network error"))
    mock_edge_tts = MagicMock()
    mock_edge_tts.Communicate.return_value = mock_communicate

    with (
        patch("app.services.local_tts_service.Config.TEMP_DIR", tmp_path),
        patch.dict("sys.modules", {"edge_tts": mock_edge_tts}),
    ):
        result = service.synthesize("Halo Tenri")

    assert result is None


def test_synthesize_prefers_sapi_in_auto_mode(tmp_path) -> None:
    service = make_service(available=True)
    service._engine = "auto"
    service._sapi_available = True
    service._edge_available = True

    with (
        patch.object(service, "_synthesize_sapi", return_value=str(tmp_path / "sapi.wav")) as sapi,
        patch.object(service, "_synthesize_edge", return_value=str(tmp_path / "edge.mp3")) as edge,
    ):
        result = service.synthesize("Halo Tenri")

    assert result.endswith("sapi.wav")
    sapi.assert_called_once_with("Halo Tenri")
    edge.assert_not_called()


def test_synthesize_auto_falls_back_to_edge_when_sapi_fails(tmp_path) -> None:
    service = make_service(available=True)
    service._engine = "auto"
    service._sapi_available = True
    service._edge_available = True

    with (
        patch.object(service, "_synthesize_sapi", return_value=None),
        patch.object(service, "_synthesize_edge", return_value=str(tmp_path / "edge.mp3")) as edge,
    ):
        result = service.synthesize("Halo Tenri")

    assert result.endswith("edge.mp3")
    edge.assert_called_once_with("Halo Tenri")
