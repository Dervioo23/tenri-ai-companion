from unittest.mock import MagicMock, patch

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
