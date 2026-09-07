import os

# =====================================================================
# DEVELOPER SIGNATURE & BRANDING (IMMUTABLE METADATA)
# =====================================================================
DEV_AUTHOR = "Umar - Automation & Scraping Engineer"
DEV_WHATSAPP = "+923028844327"
DEV_EMAIL = "umarautomationdeveloper@gmail.com"
PROJECT_NAME = "TrendPulse AI - Daraz Intelligence Engine"
VERSION = "2.5.0-Enterprise"

# Runtime & Browser Profile Settings
CHROME_PROFILE_DIR = os.path.abspath("./chrome_recording_profile")
DB_FILENAME = "daraz_scraped_database.sqlite"
HEADLESS_MODE = False
SLOW_MO_DELAY = 300
MAX_REVIEW_PAGES_DEFAULT = 10
REQUEST_TIMEOUT = 60000

# Directory configurations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, DB_FILENAME)
DEFAULT_EXCEL_OUTPUT = os.path.join(BASE_DIR, "trendpulse_scraped_output.xlsx")

# Playwright configuration
VIEWPORT = {"width": 1280, "height": 800}
BROWSER_ARGS = [
    "--start-maximized",
    "--disable-blink-features=AutomationControlled",
    "--no-first-run"
]
IGNORE_DEFAULT_ARGS = ["--enable-automation"]

# Scraping Defaults
DEFAULT_DOMAIN = "daraz.pk"
DEFAULT_SEARCH_PAGES = 1
ACTION_DELAY = 1.5
SCROLL_STEPS = 12
SCROLL_INTERVAL = 800
SCROLL_DELAY = 0.8
