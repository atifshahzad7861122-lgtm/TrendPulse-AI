# Module 5: Deep Diagnostic Audit of Live Marketplace Extractions

**Audit Date:** 2026-08-27  
**Audited Engine:** Multi-Marketplace Standalone Scraper  
**Components Inspected:** `app/crawling/`, `app/intelligence/`, `app/discovery/`, `app/clients/`, `app/core/`, `app/history/`

---

## 1. Executive Summary

During the initial Module 5 controlled live test, extraction attempts across live marketplace URLs produced the following results:

- **Daraz:** `failed_or_challenged`
- **Amazon:** `failed_or_challenged`
- **eBay:** `failed_or_challenged`
- **AliExpress:** `success` (with `quality_status = warning` and `price = 0.00`)
- **Shopify:** `failed_or_challenged`

This audit determines the exact technical root cause for each marketplace failure mode.

---

## 2. Marketplace-by-Marketplace Failure Root Causes

### 1. Daraz
- **Observed Behavior:** HTTP requests returned 200 OK with ~56KB HTML payload, but title and price extraction failed, triggering `ExtractionStatus.FAILED`.
- **Root Cause Analysis:**
  1. **Client-Side Rendering (CSR) Stubs:** Daraz desktop product pages and catalog pages are built on Alibaba's frontend node framework (`lzd-pdp-desktop-node` / `lzd-search-desktop-node`). The initial HTTP response contains JavaScript stubs (`window.g_config`), but product DOM nodes (`.pdp-mod-product-badge-title`, `.pdp-price`) and `window.pageData` are populated dynamically via client-side hydration.
  2. **Insufficient CSR Detection in Crawler:** `Crawl4AIAdapter` checked for `'"renderMode":"CSR"' in http_resp.html or ('id="app"' in http_resp.html and len(http_resp.html) < 800)`. Because Daraz's response was 56KB, `len < 800` was `False`, which prevented automatic fallback to Playwright browser rendering.
  3. **Temporary Host DNS Resolution Error:** A momentary socket resolution blip (`Errno 11001 getaddrinfo failed`) occurred when reaching `www.daraz.pk` before the network stabilized.
- **Remediation:**
  - Update `Crawl4AIAdapter` to recognize Daraz CSR signatures (`lzd-pdp-desktop-node`, `lzd-search-desktop-node`, `window.g_config` without hydrated DOM/pageData) and trigger browser execution.
  - Implement full 6-tier fallback in `DarazIntelligenceExtractor` (JSON-LD $\rightarrow$ `window.pageData` $\rightarrow$ DOM $\rightarrow$ Microdata).

---

### 2. Amazon
- **Observed Behavior:** HTTP status 200 returned, but confidence was 0.0 and fields were missing.
- **Root Cause Analysis:**
  1. **Amazon Robot Check CAPTCHA:** Automated non-browser HTTP requests from datacenter/standard IP ranges to `amazon.com/dp/...` are intercepted by Amazon's anti-bot system, returning HTTP 200 with an Amazon Robot Check CAPTCHA prompt (`"Sorry, we just need to make sure you're not a robot"` / `action="/errors/validateCaptcha"`).
  2. **Improper Classification as Generic Extraction Failure:** `UniversalChallengeDetector` did not intercept this Robot Check page early in the pipeline, allowing `AmazonIntelligenceExtractor` to parse the CAPTCHA page as an empty product, failing title extraction and marking it as `FAILED` instead of `CHALLENGE`.
- **Remediation:**
  - Strengthen `UniversalChallengeDetector` to flag Amazon Robot Check pages immediately as `CHALLENGE` / `CHALLENGE_DETECTED`.
  - Add layered extractors in `AmazonIntelligenceExtractor`: JSON-LD $\rightarrow$ `#desktop_buybox` $\rightarrow$ `#productTitle` $\rightarrow$ `.a-price` $\rightarrow$ `#feature-bullets`.

---

### 3. eBay
- **Observed Behavior:** Returned HTTP 403 with `Akamai challenge`.
- **Root Cause Analysis:**
  1. **WAF Layer 7 Interception:** eBay protects direct programmatic endpoints using Akamai Edge Bot Manager. Unauthenticated HTTP requests receive a 403 Forbidden page containing an Akamai reference ID (`Reference #18...`).
  2. **Correct Challenge Handling Required:** As per the strict architectural rule, the scraper must **never** attempt unauthorized CAPTCHA bypass. Instead, it must detect this condition accurately and return `ExtractionStatus.CHALLENGE`, pause the session, and preserve progress for manual browser intervention.
- **Remediation:**
  - Ensure `EbayIntelligenceExtractor` and `UniversalChallengeDetector` immediately label 403 Akamai blocks as `CHALLENGE_DETECTED` with clean diagnostic logging.

---

### 4. AliExpress
- **Observed Behavior:** Extraction reported `SUCCESS`, but `price = 0.00` and `quality_status = warning` (confidence = 0.41).
- **Root Cause Analysis:**
  1. **Unparsed `window.runParams` Price Objects:** AliExpress product pages embed price structures in `window.runParams.data.priceComponent` (e.g. `origPrice.minAmount.value`, `discountPrice.minAmount.value`, `skuModule.priceList[0].skuVal.actSkuCalPrice`). The extractor only attempted simple DOM query `.product-price-current` which was unhydrated in the initial HTML.
  2. **Placeholder Title Fallback:** For non-existent or redirecting items (such as `1005001234567890`), AliExpress returned a generic stub page with `<title>Aliexpress</title>`. The extractor treated `"Aliexpress"` as a valid title instead of rejecting it as an empty stub.
- **Remediation:**
  - Parse price directly from `window.runParams.data.priceComponent` and `skuModule.priceList`.
  - Reject stub pages where the title is merely `"Aliexpress"` or `"AliExpress.com"` without specific product data.
  - Implement JSON-LD and OpenGraph price fallbacks.

---

### 5. Shopify
- **Observed Behavior:** Failed with `[Errno 11001] getaddrinfo failed` and `ERR_NAME_NOT_RESOLVED`.
- **Root Cause Analysis:**
  1. **Invalid Target Subdomain:** The smoke test target configured `https://shop.allbirds.com/products/mens-tree-runners.json`. The subdomain `shop.allbirds.com` does not exist in DNS; the actual active Shopify domain is `https://www.allbirds.com/products/mens-tree-runners` (or standard Shopify endpoints like `https://kith.com/products/...`).
  2. **Classification as Extraction Failure:** When DNS fails, the system must classify the error as `TARGET_UNAVAILABLE` rather than `EXTRACTION_FAILED`.
  3. **Lack of Multi-Store Generic Extraction:** The extractor relied on `.json` endpoints. When `.json` is disabled or redirected, it must fall back to JSON-LD, Microdata, and Shopify global JavaScript objects (`var meta = {"product": ...}`).
- **Remediation:**
  - Update `ShopifyIntelligenceExtractor` to support generic Shopify HTML, JSON-LD, `meta.product`, and Microdata.
  - Properly classify network/DNS failures as `TARGET_UNAVAILABLE`.

---

## 3. Universal Fallback Priority Matrix

To ensure maximum extraction fidelity without single-selector brittleness, all extractors will adhere to the following fallback priority:

| Priority | Strategy | Source | Description |
|---|---|---|---|
| **1** | **Structured JSON-LD** | `<script type="application/ld+json">` | Standardized `schema.org/Product` schema |
| **2** | **Embedded Page State** | `window.pageData`, `window.runParams`, `meta.product` | Server-rendered JSON states |
| **3** | **Marketplace Structured Data** | HTML Data Attributes (`data-asin`, `data-item-id`, `data-sku`) | Platform-native semantic markup |
| **4** | **Metadata & OpenGraph** | `<meta property="og:...">`, `<meta name="...">` | Standard OpenGraph & Twitter Card tags |
| **5** | **CSS / XPath DOM Selectors** | BeautifulSoup Selectors | Curated, platform-specific element selectors |
| **6** | **Browser Rendered DOM** | Playwright Dynamic Evaluation | Executed JavaScript DOM when CSR is detected |

---

## 4. Next Steps

1. Harden `Crawl4AIAdapter` CSR detection and `UniversalChallengeDetector`.
2. Harden marketplace extractors (`daraz.py`, `amazon.py`, `ebay.py`, `aliexpress.py`, `shopify.py`).
3. Implement independent data exporter (`app/storage/export.py`) supporting JSON, JSONL, and CSV.
4. Implement standalone CLIs for discovery, scraping, and live smoke testing.
5. Add comprehensive regression tests and verify 100% test pass rate.
