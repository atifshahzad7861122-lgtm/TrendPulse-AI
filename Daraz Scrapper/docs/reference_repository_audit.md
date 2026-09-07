# Module 7: Reference Repository Audit Document

**Date:** 2026-08-27  
**Auditor:** Antigravity AI Engineering Toolkit  
**Status:** FULLY INSPECTED & ATTRIBUTED  

---

## 1. Executive Summary

This document details the local physical inspection of the cloned reference repositories located in `_reference_repos/`. Each repository was evaluated for reusable components, parsing patterns, selector definitions, concurrency structures, and anti-bot mitigation techniques.

---

## 2. Comprehensive Audit Matrix

### 1. `regmiprabesh/daraz-scraper`
- **Location:** `_reference_repos/daraz-scraper/`
- **Relevant Files:**
  - `scraper/spiders/daraz_spider.py`
  - `scraper/middlewares.py`
  - `scraper/pipelines.py`
- **Useful Components Inspected:**
  - Clean URL canonicalization removing tracking queries (`pdp_npi`, `spm`, `scm`).
  - Scrapy downloader middleware aborting unnecessary media requests (fonts, analytics, media).
  - Infinite scroll and catalog pagination parameter generators.
- **How Adapted:**
  - Integrated tracking parameter stripper into `app/crawling/marketplaces/daraz.py` (`canonicalize_url`).
  - Adapted resource blocking in `Crawl4AIBrowserPool` to abort tracking beacons and heavy CSS/fonts.
- **Integration Point:** `app/crawling/marketplaces/daraz.py`, `app/crawling/browser.py`.
- **Reason for Using / Rejecting:**
  - *Accepted:* Query parameter normalization prevents duplicate crawls of identical products.
  - *Rejected:* Scrapy-specific twisted reactor architecture rejected in favor of native asyncio `aiohttp`/`crawl4ai`.

---

### 2. `sushil-rgb/Daraz-Global-WebScraper`
- **Location:** `_reference_repos/Daraz-Global-WebScraper/`
- **Relevant Files:**
  - `scrapers/daraz_scraper.py`
  - `scrapers/selectors.yaml`
  - `tools/functionalities.py`
- **Useful Components Inspected:**
  - Regional domain matching (`.pk`, `.com.bd`, `.lk`, `.com.np`, `.com.mm`).
  - Centralized hierarchical YAML selector fallbacks for price, rating, reviews, and seller.
  - Safe element text extraction with whitespace stripping and None-safety.
- **How Adapted:**
  - Adapted multi-region Daraz URL parser into `DarazRegionalDetector` and `DarazDiscoveryEngine`.
  - Implemented multi-selector DOM fallbacks for Daraz PDP in `DarazIntelligenceExtractor`.
- **Integration Point:** `app/crawling/marketplaces/daraz.py`, `app/intelligence/marketplaces/daraz.py`.
- **Reason for Using / Rejecting:**
  - *Accepted:* Regional domain regex and layered selector trees.
  - *Rejected:* Synchronous Selenium architecture rejected in favor of non-blocking async Playwright.

---

### 3. `MuhammadAhmedSuhail/WebScraping-Ecommerce-Website`
- **Location:** `_reference_repos/WebScraping-Ecommerce-Website/`
- **Relevant Files:**
  - `Scrape.ipynb`
- **Useful Components Inspected:**
  - BeautifulSoup string clean up routines for messy currency symbols (`Rs.`, `PKR`, `US $`, commas).
  - Regex patterns for extracting sold volume units (`1.2K sold`, `500+ items bought`).
- **How Adapted:**
  - Adapted currency parsing and numerical conversion logic into `PriceExtractor` and `SalesExtractor`.
- **Integration Point:** `app/intelligence/extractors/price.py`, `app/intelligence/extractors/sales.py`.
- **Reason for Using / Rejecting:**
  - *Accepted:* Robust regex parsing for heterogeneous currency and sales text.
  - *Rejected:* Hardcoded Jupyter notebook execution model rejected in favor of structured OOP pipelines.

---

### 4. `BrenoFariasdaSilva/E-Commerces-WebScraper`
- **Location:** `_reference_repos/E-Commerces-WebScraper/`
- **Relevant Files:**
  - `AliExpress.py`
  - `Amazon.py`
  - `MercadoLivre.py`
  - `product_utils.py`
  - `url_input_normalizer.py`
- **Useful Components Inspected:**
  - High-resolution image extraction resolving lazy attributes (`data-src`, `data-zoom-image`, `data-old-hires`).
  - Multi-marketplace URL parser and platform auto-detection.
  - Variant matrix resolution across SKU permutations.
- **How Adapted:**
  - Integrated comprehensive lazy image attribute resolution in `ImageExtractor` (`data-src`, `data-lazy-src`, `srcset`).
  - Implemented automatic platform inferencing in `ProductionScrapingOrchestrator._infer_marketplace`.
- **Integration Point:** `app/intelligence/extractors/images.py`, `app/orchestration/orchestrator.py`.
- **Reason for Using / Rejecting:**
  - *Accepted:* Lazy-loaded image URL recovery and multi-store taxonomy parser.
  - *Rejected:* Blocking single-threaded execution rejected in favor of bounded async worker pools.

---

### 5. `unclecode/crawl4ai`
- **Location:** `_reference_repos/crawl4ai/`
- **Relevant Files:**
  - `crawl4ai/async_crawler.py`
  - `crawl4ai/browser_context.py`
  - `crawl4ai/models.py`
- **Useful Components Inspected:**
  - Dynamic Client-Side Rendering (CSR) detection heuristics.
  - Anti-bot challenge detection hooks and session state persistence.
  - Dual-mode HTTP $\rightarrow$ Browser automatic fallback.
- **How Adapted:**
  - Implemented `Crawl4AIAdapter` wrapping HTTP fetch with dynamic CSR stub detection (`lzd-pdp-desktop-node`).
  - Session state preservation across challenges in `UniversalChallengeDetector` and `SessionManager`.
- **Integration Point:** `app/crawling/adapters/crawl4ai_adapter.py`, `app/crawling/challenge.py`.
- **Reason for Using / Rejecting:**
  - *Accepted:* Lightweight async dispatcher, browser pooling, and stealth session configuration.
  - *Rejected:* Heavy AI-markdown generation dependencies excluded to keep scraper standalone and fast.

---

### 6. `Panniantong/Agent-Reach`
- **Location:** `_reference_repos/Agent-Reach/`
- **Relevant Files:**
  - Architecture overview and agent interaction blueprints.
- **Audit Evaluation:**
  - Investigated for future social product discovery and trends architecture.
  - As per PRD requirements, social scraping features are strictly deferred and not forced into this standalone ecommerce scraper.

---

## 3. Attribution & Licensing Notice
All adapted patterns adhere to original open-source licenses (MIT/Apache 2.0). Attribution is maintained within module docstrings.
