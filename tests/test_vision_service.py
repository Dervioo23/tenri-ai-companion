from unittest.mock import MagicMock, call, patch

from app.services import vision_service
from app.services.vision_service import VisionService


def test_empty_face_cascade_is_set_to_none() -> None:
    empty_cascade = MagicMock()
    empty_cascade.empty.return_value = True

    with patch("app.services.vision_service.cv2.CascadeClassifier", return_value=empty_cascade):
        service = VisionService()

    assert service.face_cascade is None


def test_loaded_face_cascade_is_kept() -> None:
    loaded_cascade = MagicMock()
    loaded_cascade.empty.return_value = False

    with patch("app.services.vision_service.cv2.CascadeClassifier", return_value=loaded_cascade):
        service = VisionService()

    assert service.face_cascade is loaded_cascade


def test_face_cascade_exception_sets_none() -> None:
    with patch("app.services.vision_service.cv2.CascadeClassifier", side_effect=Exception("missing cascade")):
        service = VisionService()

    assert service.face_cascade is None


# ------------------------------------------------------------------ snapshot throttle (BUG-08)

def _service() -> VisionService:
    loaded = MagicMock()
    loaded.empty.return_value = False
    with patch("app.services.vision_service.cv2.CascadeClassifier", return_value=loaded):
        return VisionService()


def test_should_snapshot_false_without_face() -> None:
    service = _service()
    assert service._should_snapshot(face_detected=False, now=1000.0) is False


def test_should_snapshot_does_not_fire_repeatedly_within_interval() -> None:
    """The ~10 FPS loop must NOT write ~10 files within the same window (BUG-08)."""
    service = _service()
    interval = VisionService.SNAPSHOT_INTERVAL_SECONDS

    # First call within a window fires once...
    assert service._should_snapshot(True, 100.0) is True
    # ...then every subsequent frame in that window is suppressed.
    writes = sum(
        service._should_snapshot(True, 100.0 + 0.1 * i)
        for i in range(1, int(interval * 10))
    )
    assert writes == 0


def test_should_snapshot_fires_again_after_interval_elapses() -> None:
    service = _service()
    interval = VisionService.SNAPSHOT_INTERVAL_SECONDS

    assert service._should_snapshot(True, 100.0) is True
    assert service._should_snapshot(True, 100.0 + interval - 0.5) is False
    assert service._should_snapshot(True, 100.0 + interval) is True


# ------------------------------------------------------------------ platform camera backend

def test_preferred_camera_backend_uses_avfoundation_on_macos() -> None:
    with (
        patch("app.services.vision_service.sys.platform", "darwin"),
        patch.object(vision_service.cv2, "CAP_AVFOUNDATION", 1200),
    ):
        assert VisionService._preferred_camera_backend() == 1200


def test_preferred_camera_backend_uses_directshow_on_windows() -> None:
    with (
        patch("app.services.vision_service.sys.platform", "win32"),
        patch.object(vision_service.cv2, "CAP_DSHOW", 700),
    ):
        assert VisionService._preferred_camera_backend() == 700


def test_preferred_camera_backend_uses_auto_detection_on_linux() -> None:
    with patch("app.services.vision_service.sys.platform", "linux"):
        assert VisionService._preferred_camera_backend() is None


def test_open_default_camera_falls_back_when_native_backend_fails() -> None:
    preferred = MagicMock()
    preferred.isOpened.return_value = False
    fallback = MagicMock()

    with (
        patch.object(VisionService, "_preferred_camera_backend", return_value=1200),
        patch(
            "app.services.vision_service.cv2.VideoCapture",
            side_effect=[preferred, fallback],
        ) as video_capture,
    ):
        result = VisionService._open_default_camera()

    assert result is fallback
    assert video_capture.call_args_list == [call(0, 1200), call(0)]
    preferred.release.assert_called_once_with()
