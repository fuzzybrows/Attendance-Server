import logging
import sys
import json
from logging.handlers import RotatingFileHandler

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
    # Create a custom logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # JSON Formatter
    json_formatter = JSONFormatter('%(asctime)s')

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = RotatingFileHandler('server.log', maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    # Prevent double logging from uvicorn or other libs if they propagate
    logging.getLogger("uvicorn.access").handlers = []
    
    logger.info("Logging setup complete", extra={"type": "system_startup"})
