"""Custom logging configuration for the Jira Logger application."""

import json
import logging
import time
from datetime import datetime
from functools import wraps
from logging.handlers import RotatingFileHandler

# ---------------------------------------
# Existing custom format logger
# ---------------------------------------
LOG_FORMAT = (
    "%(asctime)s | [%(name)s:%(levelname)s] | [%(threadName)s] | "
    "%(filename)s:%(lineno)d %(funcName)s() | MSG=%(message)s"
)


class SafeFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, "mobile"):
            record.mobile = "-"
        return super().format(record)


# ---------------------------------------
# LOG FILES
# ---------------------------------------
LOG_FILE = "jira-logger.log"
JSON_LOG_FILE = "elk-jira-logger.log"

MAX_LOG_SIZE = 100 * 1024 * 1024  # 100MB
BACKUP_COUNT = 5


# ---------------------------------------
# JSON formatter
# ---------------------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "@version": "1",
            "message": record.getMessage(),
            "logger_name": record.name,
            "thread_name": record.threadName,
            "request": {"id": record.threadName},
            "level": record.levelname,
            "level_value": record.levelno,
            "application_name": "jira-logger",
        }
        return json.dumps(log_record)


# ---------------------------------------
# CONFIGURE HANDLERS
# ---------------------------------------
formatter = SafeFormatter(LOG_FORMAT)

file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
)
file_handler.setFormatter(formatter)

json_handler = RotatingFileHandler(
    JSON_LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
)
json_handler.setFormatter(JsonFormatter())

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# ---------------------------------------
# APPLY CUSTOM LOGGING TO UVICORN
# ---------------------------------------
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, json_handler, console_handler],
    force=True,
)

# ---------------------------------------
# PATCH UVICORN LOGGERS
# ---------------------------------------
for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi"]:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(json_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True

# ---------------------------------------
# IMPORTANT 3rd-party modules to capture
# ---------------------------------------
third_parties = [
    "fastapi",
    "starlette",
    "requests",
    "httpx",
    "asyncio",
    "pydantic",
    "openai",
    "sqlalchemy",
]

for lib in third_parties:
    logger = logging.getLogger(lib)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(json_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True

logging.basicConfig(
    level=logging.INFO, handlers=[file_handler, json_handler, console_handler]
)


# ---------------------------------------
# Utility
# ---------------------------------------
def get_logger(name):
    return logging.getLogger(name)


logger = get_logger(__name__)


def log_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"🔄 Started: {func.__name__}()")
        start_time = time.time()

        result = func(*args, **kwargs)

        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"✅ Finished: {func.__name__} | Duration: {duration:.2f} seconds")
        return result

    return wrapper
