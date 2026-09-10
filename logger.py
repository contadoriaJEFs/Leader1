import logging
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

logger = logging.getLogger("leader1")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.FileHandler(
        "logs/app.log",
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
    )
    logger.addHandler(handler)

def get_logger():
    return logger
