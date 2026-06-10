import os
import shutil
import logging
from app.config import Config

logger = logging.getLogger("AICompanion.FileManager")

class FileManager:
    @staticmethod
    def ensure_directories():
        """Creates all necessary directories for assets and data."""
        directories = [
            Config.DATA_DIR,
            Config.LOGS_DIR,
            Config.ASSETS_DIR,
            Config.AUDIO_DIR,
            Config.RESPONSES_DIR,
            Config.TEMP_DIR,
            Config.TTS_CACHE_DIR,
            Config.SNAPSHOTS_DIR
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Directory verified/created: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")

    @staticmethod
    def cleanup_temp_files():
        """Cleans up files inside the temporary audio directory to free up space."""
        temp_dir = Config.TEMP_DIR
        if temp_dir.exists():
            for filename in os.listdir(temp_dir):
                file_path = temp_dir / filename
                try:
                    if file_path.is_file() or file_path.is_symlink():
                        os.unlink(file_path)
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                    logger.info(f"Deleted temp file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}. Reason: {e}")
        else:
            logger.info("Temp directory does not exist. No cleanup needed.")
