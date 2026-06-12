import logging
from logging.handlers import RotatingFileHandler
from app.config import Config

def setup_logger():
    """Sets up the global logger for the application."""
    # Ensure log directory exists
    log_dir = Config.LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "app.log"
    
    logger = logging.getLogger("AICompanion")
    logger.setLevel(logging.INFO)
    
    # Clean existing handlers
    if logger.handlers:
        logger.handlers.clear()
        
    # File handler (rotate at 1MB, keep 3 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=3, encoding="utf-8")
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    console_handler.setLevel(logging.WARNING) # Console only shows warnings/errors by default
    logger.addHandler(console_handler)
    
    logger.info("Logger system initialized.")
    return logger
