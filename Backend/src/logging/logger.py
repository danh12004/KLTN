import os
import sys
import logging
from io import TextIOWrapper
from src.utils.config import BASE_DIR

logging_str = "%(asctime)s: %(levelname)s: %(module)s: %(message)s"

log_dir = os.path.join(BASE_DIR, "logs")
log_filepath = os.path.join(log_dir, "running_logs.log")
os.makedirs(log_dir, exist_ok=True)

file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
stream_handler = logging.StreamHandler(TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))

logging.basicConfig(
    level=logging.INFO,
    format=logging_str,
    handlers=[file_handler, stream_handler]
)

logger = logging.getLogger("Chatbot_Logger")
logger.setLevel(logging.INFO)