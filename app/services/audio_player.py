import time
import logging
from app.config import Config

logger = logging.getLogger("AICompanion.AudioPlayer")

class AudioPlayer:
    def __init__(self):
        self.initialized = False
        try:
            import pygame
            pygame.mixer.init()
            self.pygame = pygame
            self.initialized = True
            logger.info("Pygame mixer initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Pygame mixer: {e}. Audio playback will be mock-only.")

    def play_audio(self, file_path: str):
        """Plays the audio file blocking until completion."""
        if not self.initialized or not file_path:
            logger.warning(f"Audio playback skipped. (Path: {file_path}, Pygame Init: {self.initialized})")
            return

        try:
            logger.info(f"Playing audio: {file_path}")
            self.pygame.mixer.music.load(file_path)
            self.pygame.mixer.music.play()
            
            # Block until playback finishes, but never let a stuck audio driver freeze the app.
            started_at = time.monotonic()
            while self.pygame.mixer.music.get_busy():
                if time.monotonic() - started_at >= Config.AUDIO_PLAYBACK_TIMEOUT:
                    logger.warning(
                        f"Audio playback timed out after {Config.AUDIO_PLAYBACK_TIMEOUT:.1f}s: {file_path}"
                    )
                    self.pygame.mixer.music.stop()
                    break
                time.sleep(0.1)
                
            # Unload file to release lock
            self.pygame.mixer.music.unload()
            logger.info("Audio playback completed and file unloaded.")
        except Exception as e:
            logger.error(f"Failed playing audio {file_path}: {e}")

    def stop(self):
        """Interrupts playback if busy."""
        if self.initialized and self.pygame.mixer.music.get_busy():
            try:
                self.pygame.mixer.music.stop()
                self.pygame.mixer.music.unload()
                logger.info("Audio playback interrupted by user.")
            except Exception as e:
                logger.error(f"Error while stopping audio: {e}")
