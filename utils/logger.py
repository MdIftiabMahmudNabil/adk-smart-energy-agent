"""Logging configuration for the Smart Energy Consumption Agent."""

import logging
import sys
from pathlib import Path
from .config import LOGS_DIR, LOG_LEVEL, LOG_FORMAT

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Set up a logger with console and file handlers.
    
    Args:
        name: Logger name (typically __name__ of the module)
        log_file: Optional log file name (if None, uses name.log)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_path = LOGS_DIR / log_file
    else:
        file_path = LOGS_DIR / f"{name.replace('.', '_')}.log"
    
    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger
