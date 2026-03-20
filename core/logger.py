import logging
import os
from logging.handlers import RotatingFileHandler

def get_logger(name: str) -> logging.Logger:
    """Configures and returns a logger instance."""
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    log_dir = os.path.join(project_root, "logs")
    log_file = os.path.join(log_dir, "system.log")

    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if the logger already has them
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Add File Handler
        try:
            file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup file logging to {log_file}: {e}")

        # Add Stream (Console) Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
