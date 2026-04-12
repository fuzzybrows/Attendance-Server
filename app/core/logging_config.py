import logging
import os
import sys
import json
from logging.handlers import RotatingFileHandler
from app.settings import settings, Environment

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name
        }
        
        # Standard attributes to exclude from extra fields
        standard_attrs = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 
            'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName', 
            'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 
            'processName', 'process', 'message', 'asctime', 'taskName'
        }

        # Add all extra attributes to the log record
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                log_record[key] = value

        # Ensure 'type' is present if not provided
        if "type" not in log_record:
            log_record["type"] = "generic_log"

        return json.dumps(log_record)

def setup_logging():
    is_local = settings.environment == Environment.LOCAL

    # JSON Formatter
    json_formatter = JSONFormatter('%(asctime)s')

    # Console Handler (always active)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(json_formatter)

    # Collect handlers
    handlers = [console_handler]

    # File Handler (local only — avoids disk writes in production/CI)
    if is_local:
        file_handler = RotatingFileHandler('server.log', maxBytes=10*1024*1024, backupCount=5)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(json_formatter)
        handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers = []
        
    for h in handlers:
        root_logger.addHandler(h)

    # Configure uvicorn loggers to use our JSON format and handlers
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = []  # Remove default handlers
        for h in handlers:
            uvicorn_logger.addHandler(h)
        uvicorn_logger.propagate = False

    # Explicit log to confirm setup
    root_logger.info("Logging setup complete", extra={"type": "system_startup"})
