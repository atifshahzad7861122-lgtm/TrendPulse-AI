# TrendPulse Daraz Scraper

A robust, modular, asynchronous scraping ecosystem for the Daraz Pakistan marketplace.

---

## 📦 Modules

- **Module 1**: Scraper Foundation and Core Architecture (✅ Complete)
- **Module 2**: Daraz Marketplace Discovery Engine (✅ Complete)
- **Module 3**: Daraz Product Extraction Engine (✅ Complete)

---

## 🏗️ Complete Project Structure

```
trendpulse-daraz-scraper/
│
├── app/
│   ├── main.py                     # FastAPI application entrypoint & /health check
│   │
│   ├── core/                       # Module 1: Foundation Layer
│   │   ├── config.py               # Pydantic Settings & environment variables
│   │   ├── logging.py              # Structured JSON logging & secret masking
│   │   ├── exceptions.py           # Standardized ScraperError hierarchy
│   │   ├── constants.py            # Enums (CrawlStatus, SentimentType, etc.)
│   │   ├── rate_limiter.py         # Async rate limiter with concurrency semaphore
│   │   ├── retry.py                # Retry policies & exponential backoff with jitter
│   │   └── runtime.py              # Context variables & request metrics tracking
│   │
│   ├── models/                     # Core Data Contracts
│   │   ├── product.py              # Product schema
│   │   ├── review.py               # Review & sentiment schema
│   │   ├── category.py             # Category taxonomy schema
│   │   ├── seller.py               # Merchant/seller schema
│   │   ├── image.py                # Image asset schema
│   │   └── crawl.py                # Crawl session & metrics schema
│   │
│   ├── clients/                    # Client Abstractions
│   │   ├── http_client.py          # Async HTTP client (retry, rate-limit, metrics)
│   │   └── browser_client.py       # Playwright browser manager with stealth presets
│   │
│   ├── storage/                    # Storage Abstraction Layer
│   │   ├── base.py                 # Abstract BaseStorage interface
│   │   └── repository.py           # In-memory storage repository
│   │
│   ├── crawler/                    # Crawler Framework
│   │   ├── base.py                 # BaseCrawler abstract lifecycle definition
│   │   └── job.py                  # CrawlJob session manager & checkpointing
│   │
│   ├── discovery/                  # Module 2: Daraz Discovery Engine
│   │   ├── config.py               # Daraz marketplace selectors & URL patterns
│   │   ├── models.py               # CategoryTarget, ProductTarget, DiscoveryRun
│   │   ├── normalizer.py           # Tracking removal & numeric Product ID extraction
│   │   ├── detector.py             # CAPTCHA, 403/429, & Challenge detection
│   │   ├── parser.py               # BeautifulSoup HTML adapter (Categories & Products)
│   │   ├── queue.py                # ProductTargetQueue with global deduplication
│   │   ├── manual_intervention.py  # CAPTCHA pause, context hold, & resume manager
│   │   ├── client.py               # DarazDiscoveryClient (HTTP + Playwright bridge)
│   │   └── engine.py               # DarazDiscoveryEngine orchestrator
│   │
│   └── extraction/                 # Module 3: Daraz Product Extraction Engine
│       ├── models.py               # ExtractionResult data model
│       ├── parser.py               # ProductParser unifying DOM & JSON-LD/pageData
│       ├── engine.py               # DarazProductExtractor orchestrator
│       └── extractors/             # Pluggable Domain Extractors
│           ├── price.py            # PriceExtractor (selling price, original, discount)
│           ├── image.py            # ImageExtractor (primary, gallery, dedup, lazy)
│           ├── rating.py           # RatingExtractor (stars, total review count)
│           ├── sales.py            # SalesExtractor (1.2K sold, 500+ sold, etc.)
│           ├── seller.py           # SellerExtractor (merchant ID, store name, score)
│           ├── category.py         # CategoryExtractor (breadcrumbs & leaf ID)
│           ├── variant.py          # VariantExtractor (SKUs, variations, stock)
│           ├── specification.py    # SpecificationExtractor (key-value technical specs)
│           └── description.py      # DescriptionExtractor (clean HTML/text body)
│
├── tests/
│   ├── fixtures/daraz/             # Mock HTML fixtures for isolated unit tests
│   │   ├── category_menu.html
│   │   ├── search_results.html
│   │   ├── search_results_page2.html
│   │   ├── captcha_challenge.html
│   │   ├── blocked_page.html
│   │   ├── product_page_standard.html
│   │   ├── product_page_minimal.html
│   │   ├── product_page_out_of_stock.html
│   │   └── product_page_dynamic_json.html
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_clients.py
│   ├── test_storage.py
│   ├── test_health.py
│   ├── test_discovery_models.py
│   ├── test_discovery_normalizer.py
│   ├── test_discovery_detector.py
│   ├── test_discovery_parser.py
│   ├── test_discovery_queue.py
│   ├── test_discovery_engine.py
│   ├── test_extraction_extractors.py
│   ├── test_extraction_parser.py
│   └── test_extraction_engine.py
│
├── scripts/
│   ├── run_healthcheck.py          # CLI health check validation utility
│   └── run_smoke_test.py           # Controlled live smoke test utility
│
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 🧪 Test Suite

Run the full pytest suite across all modules:
```powershell
python -m pytest tests/ -v
```
All **63 tests** across Module 1, Module 2, and Module 3 are passing with 100% green status.
