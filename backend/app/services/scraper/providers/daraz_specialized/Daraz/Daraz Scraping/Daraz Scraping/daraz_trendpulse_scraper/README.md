# Daraz TrendPulse Scraper

An enterprise-grade, asynchronous e-commerce scraping suite designed for Daraz. It utilizes Playwright browser automation to bypass bot detection signatures, features SQLite-backed checkpoint resume queueing, includes human-in-the-loop CAPTCHA pause alerts, and exports a styled multi-tab Excel spreadsheet report.

## Project Structure

```text
daraz_trendpulse_scraper/
├── config.py                  # Developer metadata, constants & paths
├── logger.py                  # Terminal logging & branding banner
├── db_manager.py              # SQLite deduplication, queue & checkpoint resume
├── captcha_handler.py         # Human-in-the-loop CAPTCHA pause mechanism
├── extractors/
│   ├── __init__.py
│   ├── product_parser.py      # Core info, gallery, pricing, specs & taxonomy
│   ├── review_parser.py       # Full review pagination, comments & reviewer data
│   └── variations_parser.py   # Product SKU variations & attributes
├── excel_exporter.py          # Multi-tab styled Excel report with branding
├── main.py                    # Orchestrator & CLI runner
├── test_scraper.py            # Automated Unit & Integration tests
├── requirements.txt           # Dependencies
└── README.md                  # Setup & execution guide
```

---

## Features

1. **Asynchronous Architecture**: Full async crawling using `playwright.async_api` for rapid extraction.
2. **Persistent Chrome Profile Context**: Launches persistent user profiles to bypass automation checks and reduce block rates.
3. **SQLite Queue & Resume Checkpoints**: Queues URL items during crawl. Interrupted crawlers can be safely resumed at the same queue index.
4. **Human-In-The-Loop CAPTCHA Detection**: Recognizes slide checks and pauses for manual verification directly inside the headed browser window.
5. **Styled Multi-Tab Spreadsheets**: Automatically styles headers, cell alignments, gridlines, and auto-sizes column widths based on contents.

---

## Installation

Ensure you have Python 3.8+ installed on Windows. Then, install dependencies:

```bash
# Navigate to the project directory
cd "daraz_trendpulse_scraper"

# Install packages
pip install -r requirements.txt

# Install Playwright browser binaries
python -m playwright install chromium
```

---

## Execution Commands

### 1. Scrape a Single Product Page
Pass a Daraz product detail page URL to `-q`:
```bash
python main.py -q "https://www.daraz.pk/products/microsoft-arc-mouse-arc-touch-mouse-bluetooth-mouse-wireless-mouse-foldable-mouse-slim-mouse-surface-pro-mouse-portable-mouse-travel-mouse-premium-office-mouse-titanium-mouse-i1968312196.html" --reviews-pages 1 -o "single_product_details.xlsx"
```

### 2. Scrape Search Catalog Listing
Pass a search term to `-q` and specify the domain (`daraz.pk`, `daraz.com.bd`, `daraz.com.np`, etc.) and the number of catalog pages to crawl:
```bash
python main.py -q "wireless mouse" -d "daraz.pk" -p 1 --reviews-pages 1 -o "mouse_search_report.xlsx"
```

### 3. Resume Scraper Checkpoint Queue
If a search crawl gets interrupted, simply use `-r`/`--resume` to complete the queue execution:
```bash
python main.py -r -o "mouse_search_report.xlsx"
```

### 4. Run Automated Unit & Integration Tests
Execute unit tests verifying SQLite database state transitions and Excel reports:
```bash
python -m unittest test_scraper.py
```
