import logging
from pathlib import Path

def get_logger():
    Path("logs").mkdir(exist_ok=True)
    logger = logging.getLogger("lead_scraper")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler("logs/app.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(handler)
    return logger
