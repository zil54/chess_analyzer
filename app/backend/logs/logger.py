# logger.py
import logging
from logging.handlers import RotatingFileHandler
import os


#Recommended Log Rotation Thresholds
#For most backend apps like yours, 10 MB is a good default threshold to start rotating.

#Local Dev 5–10 MB
#Staging 10–50 MB
#PROD 50–100 MB

log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

log_path = os.path.join(log_dir, "app.log")

file_handler = RotatingFileHandler(
    log_path,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5               # Keep 5 rotated files: app.log.1 to app.log.5
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        file_handler,
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("chess-analyzer")