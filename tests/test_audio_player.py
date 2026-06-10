import logging
from unittest.mock import MagicMock, patch

from app.services.audio_player import AudioPlayer


def make_player():
    player = AudioPlayer.__new__(AudioPlayer)
    player.initialized = True
    player.pygame = MagicMock()
    return player


def test_play_audio_stops_when_playback_timeout_is_reached(caplog):
    player = make_player()
    player.pygame.mixer.music.get_busy.return_value = True

    with patch("app.services.audio_player.Config.AUDIO_PLAYBACK_TIMEOUT", 0.2), \
         patch("app.services.audio_player.time.monotonic", side_effect=[0.0, 0.3]), \
         patch("app.services.audio_player.time.sleep") as sleep_mock, \
         caplog.at_level(logging.WARNING, logger="AICompanion.AudioPlayer"):
        player.play_audio("stuck.wav")

    player.pygame.mixer.music.load.assert_called_once_with("stuck.wav")
    player.pygame.mixer.music.play.assert_called_once()
    player.pygame.mixer.music.stop.assert_called_once()
    player.pygame.mixer.music.unload.assert_called_once()
    sleep_mock.assert_not_called()
    assert "Audio playback timed out after 0.2s: stuck.wav" in caplog.text


def test_play_audio_does_not_stop_when_playback_finishes_normally():
    player = make_player()
    player.pygame.mixer.music.get_busy.side_effect = [True, False]

    with patch("app.services.audio_player.Config.AUDIO_PLAYBACK_TIMEOUT", 5.0), \
         patch("app.services.audio_player.time.monotonic", side_effect=[0.0, 0.1]), \
         patch("app.services.audio_player.time.sleep"):
        player.play_audio("normal.wav")

    player.pygame.mixer.music.stop.assert_not_called()
    player.pygame.mixer.music.unload.assert_called_once()
