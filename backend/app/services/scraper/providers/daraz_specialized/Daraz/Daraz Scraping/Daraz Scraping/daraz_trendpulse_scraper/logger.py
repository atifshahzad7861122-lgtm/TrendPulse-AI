import logging
import sys
from config import DEV_AUTHOR, DEV_WHATSAPP, DEV_EMAIL, PROJECT_NAME, VERSION

def print_dev_banner():
    banner = f"""
================================================================================
  {PROJECT_NAME} (v{VERSION})
  Engineered by: {DEV_AUTHOR}
  Contact WhatsApp: {DEV_WHATSAPP} | Email: {DEV_EMAIL}
================================================================================
"""
    print(banner)

def setup_logger():
    sys.stdout.reconfigure(encoding='utf-8')
    logger = logging.getLogger("TrendPulseScraper")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logger()
