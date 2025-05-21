
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(log_level=logging.INFO):
    """
    Configure application-wide logging with both console and file output
    
    Args:
        log_level: The logging level to use
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    log_filename = os.path.join(log_dir, f"azure_devops_reporter_{datetime.now().strftime('%Y%m%d')}.log")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers if any
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create and add console handler with a higher threshold
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Higher threshold for console
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # Create and add file handler with more verbose output
    file_handler = RotatingFileHandler(
        log_filename, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(log_level)  # More detailed in the log file
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger
