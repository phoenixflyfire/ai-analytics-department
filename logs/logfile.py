# logs/logfile.py
import os
import logging
from logging.handlers import RotatingFileHandler

_LOGGING_CONFIGURED = False

def setup_logging():
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    _LOGGING_CONFIGURED = True

    # 1. Create directory for logs
    log_dir = "local_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "adk_debug.log")

    # 2. Set strict formatting for tracing agent steps
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 3. Setup File Handler (Saves verbose debug details)
    file_handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)  # <-- This captures detailed LLM calls

    # 4. Setup Stream Handler (Keeps your main terminal window clean)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)   # <-- Only shows main actions on screen

    # 5. Attach everything to the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)      # <-- Must be set to DEBUG globally
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    print(f"[*] Debug logging enabled. File output path: {log_file_path}")
