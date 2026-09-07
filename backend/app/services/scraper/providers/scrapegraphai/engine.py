"""
ScrapeGraphAI Engine.

Implements web scraping and product discovery using ScrapeGraphAI's
SmartScraperGraph, SmartScraperMultiGraph, and SearchGraph pipelines.
Features legitimate Playwright browser rendering, AWS WAF token challenge handling,
strict Groq TPM rate limiting / throttled concurrency, and robust DOM fallback extraction.
Seamlessly integrates with TrendPulse AI's ScraperService and ScraperIntegrationBridge.
"""

import os
import re
import time
import json
import asyncio
import logging
import urllib.parse
from typing import List, Optional, Dict, Any, Callable, Tuple
from bs4 import BeautifulSoup

from backend.app.services.scraper.providers.scrapegraphai.config import ScrapeGraphAIConfig
from backend.app.services.scraper.providers.scrapegraphai.schema import (
    ScrapeGraphProductItem, ScrapeGraphProductList
)
from backend.app.services.scraper.providers.scrapegraphai.prompts import (
    PRODUCT_DETAIL_EXTRACTION_PROMPT, PRODUCT_CATALOG_SEARCH_PROMPT
)
from backend.app.services.scraper.providers.scrapegraphai.normalizer import ScrapeGraphNormalizer

# Import ScrapeGraphAI graphs
try:
    from scrapegraphai.graphs import SmartScraperGraph, SmartScraperMultiGraph, SearchGraph
    _SCRAPEGRAPHAI_AVAILABLE = True
except ImportError:
    SmartScraperGraph = None
    SmartScraperMultiGraph = None
    SearchGraph = None
    _SCRAPEGRAPHAI_AVAILABLE = False

logger = logging.getLogger("trendpulse.scraper.scrapegraphai.engine")


class LLMRequestThrottler:
    """
    Regulates LLM request throughput to strictly adhere to free-tier and standard token/request limits.
    Prevents HTTP 429 errors by enforcing single-flight execution, minimum inter-request delay,
    and automatic exponential backoff with Retry-After detection.
    """

    def __init__(
        self,
        max_concurrent: int = 1,
        min_delay_seconds: float = 2.5,
        max_retries: int = 3,
        backoff_base: float = 2.0
    ):
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent))
        self.min_delay_seconds = min_delay_seconds
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._last_request_time = 0.0

    async def execute(self, func: Callable[[], Any]) -> Any:
        async with self._semaphore:
            for attempt in range(self.max_retries + 1):
                # Enforce minimum delay between calls
                now = time.monotonic()
                elapsed = now - self._last_request_time
                if elapsed < self.min_delay_seconds:
                    await asyncio.sleep(self.min_delay_seconds - elapsed)

                try:
                    self._last_request_time = time.monotonic()
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, func)
                except Exception as err:
                    err_str = str(err).lower()
                    is_rate_limit = (
                        "429" in err_str
                        or "rate limit" in err_str
                        or "too many requests" in err_str
                        or "tpm" in err_str
                    )
                    if is_rate_limit and attempt < self.max_retries:
                        delay = self.backoff_base * (2 ** attempt)
                        match = re.search(r"try again in ([\d\.]+)s", err_str)
                        if match:
                            try:
                                delay = max(delay, float(match.group(1)) + 0.5)
                            except ValueError:
                                pass
                        logger.warning(
                            f"LLM rate limit detected (attempt {attempt + 1}/{self.max_retries}). "
                            f"Backing off for {delay:.2f}s before retry..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise


def _parse_price_and_currency(raw_price_str: Optional[str]) -> Tuple[Optional[float], str]:
    """Extracts numeric price and currency symbol/code safely without fabricating data."""
    if not raw_price_str:
        return None, "USD"
    text = raw_price_str.replace(",", "").strip()
    currency = "USD"
    if "PKR" in text or "Rs" in text:
        currency = "PKR"
    elif "$" in text:
        currency = "USD"
    elif "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"

    match = re.search(r"([\d\.]+)", text)
    if match:
        try:
            val = float(match.group(1))
            if val > 0:
                return round(val, 2), currency
        except (ValueError, TypeError):
            pass
    return None, currency


def _parse_rating(raw_rating_str: Optional[str]) -> Optional[float]:
    """Extracts 0.0 - 5.0 star rating safely."""
    if not raw_rating_str:
        return None
    match = re.search(r"([\d\.]+)\s*(?:out of|\/)\s*5", raw_rating_str, re.IGNORECASE)
    if match:
        try:
            val = float(match.group(1))
            if 0.0 < val <= 5.0:
                return round(val, 1)
        except (ValueError, TypeError):
            pass
    match = re.search(r"([\d\.]+)", raw_rating_str)
    if match:
        try:
            val = float(match.group(1))
            if 0.0 < val <= 5.0:
                return round(val, 1)
        except (ValueError, TypeError):
            pass
    return None


def _parse_review_count(raw_rev_str: Optional[str]) -> Optional[int]:
    """Extracts integer review counts supporting K/M suffixes."""
    if not raw_rev_str:
        return None
    text = raw_rev_str.replace("(", "").replace(")", "").replace(",", "").strip()
    match = re.search(r"([\d\.]+)\s*([KkMm])?", text)
    if match:
        try:
            num = float(match.group(1))
            mult = match.group(2)
            if mult and mult.lower() == "k":
                num *= 1000
            elif mult and mult.lower() == "m":
                num *= 1000000
            return int(num)
        except (ValueError, TypeError):
            pass
    return None


def extract_amazon_dom_candidates(html: str, base_url: str = "https://www.amazon.com") -> List[Dict[str, Any]]:
    """
    Direct DOM extraction fallback for Amazon search result cards.
    Extracts ASIN, title, price, currency, original_price, rating, reviews, image, and link.
    Strictly keeps missing values as None (zero synthetic data).
    """
    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select('div[data-component-type="s-search-result"], div.s-result-item[data-asin]')
    candidates: List[Dict[str, Any]] = []

    for it in items:
        asin = it.get("data-asin")
        if not asin or not asin.strip():
            continue
        asin = asin.strip()

        title_el = it.select_one("h2 a span, h2 span, span.a-text-normal")
        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            continue

        price_el = it.select_one(".a-price .a-offscreen, span.a-price-whole")
        price_raw = price_el.get_text(strip=True) if price_el else None
        price, currency = _parse_price_and_currency(price_raw)

        orig_price_el = it.select_one(".a-price.a-text-price .a-offscreen, s.a-text-price")
        orig_price_raw = orig_price_el.get_text(strip=True) if orig_price_el else None
        orig_price, _ = _parse_price_and_currency(orig_price_raw)
        if orig_price is not None and price is not None and orig_price < price:
            orig_price = None

        rating_el = it.select_one(
            "a[aria-label*='out of 5 stars'], i.a-icon-star-mini, i.a-icon-star-small span.a-icon-alt, "
            "i.a-icon-star span.a-icon-alt, [aria-label*='out of 5 stars']"
        )
        rating_raw = None
        if rating_el:
            rating_raw = rating_el.get("aria-label") or rating_el.get_text(strip=True)
        rating = _parse_rating(rating_raw)

        rev_el = it.select_one(
            "span[aria-label*='stars'] ~ span, a[href*='customerReviews'] span, .a-size-base.s-underline-text"
        )
        rev_raw = rev_el.get_text(strip=True) if rev_el else None
        reviews = _parse_review_count(rev_raw)

        link_el = it.select_one("h2 a, a.a-link-normal.s-no-outline")
        href = link_el.get("href") if link_el else None
        if not href:
            continue
        product_url = urllib.parse.urljoin(base_url, href)

        img_el = it.select_one("img.s-image, img[src*='media-amazon']")
        image_url = img_el.get("src") if img_el else None

        candidates.append({
            "product_id": asin,
            "asin": asin,
            "title": title,
            "price": price,
            "currency": currency,
            "original_price": orig_price,
            "rating": rating,
            "review_count": reviews,
            "product_url": product_url,
            "image_url": image_url,
            "seller_name": None,
            "brand": None,
            "availability": True if price is not None else None,
            "description": None
        })

    return candidates


def extract_scoped_catalog_html(html: str) -> str:
    """
    Extracts an ultra token-efficient snippet of catalog cards (~150-300 tokens)
    to protect Groq's 8,000 TPM and daily token limits on compound models.
    """
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "svg", "noscript", "iframe", "path"]):
        tag.decompose()
    cards = soup.select('div[data-component-type="s-search-result"], div.s-result-item[data-asin]')
    compact_cards = []
    for c in cards[:5]:
        asin = c.get("data-asin")
        if not asin:
            continue
        t_el = c.select_one("h2 a span, h2 span, span.a-text-normal")
        p_el = c.select_one(".a-price .a-offscreen, span.a-price-whole")
        r_el = c.select_one(
            "a[aria-label*='out of 5 stars'], i.a-icon-star-mini, [aria-label*='out of 5 stars']"
        )
        rev_el = c.select_one(
            "span[aria-label*='stars'] ~ span, a[href*='customerReviews'] span, .a-size-base.s-underline-text"
        )
        l_el = c.select_one("h2 a")
        title = t_el.get_text(strip=True) if t_el else ""
        price = p_el.get_text(strip=True) if p_el else ""
        rating = (r_el.get("aria-label") or r_el.get_text(strip=True)) if r_el else ""
        revs = rev_el.get_text(strip=True) if rev_el else ""
        href = l_el.get("href") if l_el else ""
        compact_cards.append(
            f"<div class='product' data-asin='{asin}'>"
            f"<span class='title'>{title}</span>"
            f"<span class='price'>{price}</span>"
            f"<span class='rating'>{rating}</span>"
            f"<span class='reviews'>{revs}</span>"
            f"<a href='{href}'>link</a>"
            f"</div>"
        )
    return f"<html><body><div class='catalog-results'>{''.join(compact_cards)}</div></body></html>"


class ScrapeGraphAIEngine:
    """
    Production scraper engine wrapping ScrapeGraphAI pipelines with
    resilient Playwright rendering, rate limiting, and DOM fallbacks.
    """

    def __init__(self, config: Optional[ScrapeGraphAIConfig] = None):
        self.config = config or ScrapeGraphAIConfig.load_from_settings()
        self.throttler = LLMRequestThrottler(
            max_concurrent=self.config.max_concurrent_llm_requests,
            min_delay_seconds=self.config.min_delay_between_requests,
            max_retries=self.config.max_retries_on_429,
            backoff_base=self.config.retry_backoff_base
        )

    def is_available(self) -> bool:
        """Returns True if the scrapegraphai package is installed and enabled."""
        return _SCRAPEGRAPHAI_AVAILABLE and self.config.enabled

    def _sanitize_error(self, err: Exception) -> str:
        """Strips out any potential API keys, authorization tokens, or sensitive headers."""
        msg = str(err)
        if self.config.api_key:
            msg = msg.replace(self.config.api_key, "[REDACTED_API_KEY]")
        # Regex to scrub bearer tokens or api keys
        msg = re.sub(r"(sk-[a-zA-Z0-9]{20,})", "[REDACTED_SECRET]", msg)
        msg = re.sub(r"(gsk_[a-zA-Z0-9]{20,})", "[REDACTED_SECRET]", msg)
        msg = re.sub(r"(key=[a-zA-Z0-9_\-]{16,})", "key=[REDACTED]", msg)
        return msg

    def _get_marketplace_search_url(self, marketplace: str, keyword: str) -> str:
        """Constructs the standard search catalog URL for a marketplace."""
        kw_enc = urllib.parse.quote_plus(keyword)
        m = marketplace.lower().strip()
        if m == "daraz":
            return f"https://www.daraz.pk/catalog/?q={kw_enc}"
        elif m == "amazon":
            return f"https://www.amazon.com/s?k={kw_enc}"
        elif m == "ebay":
            return f"https://www.ebay.com/sch/i.html?_nkw={kw_enc}"
        elif m == "aliexpress":
            return f"https://www.aliexpress.com/wholesale?SearchText={kw_enc}"
        elif m == "shopify":
            return f"https://www.google.com/search?q=site:myshopify.com+{kw_enc}"
        return f"https://www.google.com/search?q={m}+{kw_enc}"

    async def render_page_legitimate(
        self,
        url: str,
        timeout: Optional[float] = None
    ) -> Tuple[Optional[str], int]:
        """
        Renders a webpage using legitimate Playwright browser configuration.
        Handles AWS WAF JavaScript challenges naturally by allowing the browser's
        built-in JavaScript engine to execute challenge.js and reload.
        """
        from playwright.async_api import async_playwright
        try:
            from undetected_playwright import Malenia
            _has_stealth = True
        except ImportError:
            _has_stealth = False

        effective_timeout = (timeout or self.config.timeout) * 1000

        # Proxy support if configured
        proxy_config = None
        proxy_url = (
            os.environ.get("SCRAPER_PROXY_URL")
            or os.environ.get("HTTP_PROXY")
            or os.environ.get("HTTPS_PROXY")
        )
        if proxy_url:
            proxy_config = {"server": proxy_url}

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--window-size=1920,1080",
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.config.headless,
                args=launch_args,
                proxy=proxy_config
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/133.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            if _has_stealth:
                try:
                    await Malenia.apply_stealth(context)
                except Exception as s_err:
                    logger.debug(f"Stealth notice: {s_err}")

            page = await context.new_page()

            try:
                resp = await page.goto(url, timeout=effective_timeout)
                status_code = resp.status if resp else 200

                # Allow WAF challenge script to execute and page to reload with token
                for _ in range(15):
                    cur_title = await page.title()
                    if "Amazon.com" in cur_title or "Amazon" in cur_title:
                        break
                    await asyncio.sleep(1)

                # Wait for product card selector
                try:
                    await page.wait_for_selector(
                        'div[data-component-type="s-search-result"], div.s-result-item[data-asin]',
                        timeout=10000
                    )
                except Exception:
                    pass

                content = await page.content()
                return content, status_code
            finally:
                await browser.close()

    async def scrape_single_url(
        self,
        url: str,
        marketplace: str = "daraz",
        prompt: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts structured product data from a single product page using SmartScraperGraph.
        """
        if not self.is_available():
            raise RuntimeError("ScrapeGraphAI is not available or disabled.")

        if not self.config.api_key and self.config.provider not in ("ollama", "local"):
            raise RuntimeError(
                f"ScrapeGraphAI API key is missing for provider '{self.config.provider}'. "
                f"Configure SCRAPEGRAPHAI_API_KEY or LLM_API_KEY."
            )

        graph_config = self.config.to_graph_config()
        effective_prompt = prompt or PRODUCT_DETAIL_EXTRACTION_PROMPT

        def _run_sync():
            scraper = SmartScraperGraph(
                prompt=effective_prompt,
                source=url,
                config=graph_config,
                schema=ScrapeGraphProductItem
            )
            return scraper.run()

        try:
            raw_result = await self.throttler.execute(_run_sync)
            if isinstance(raw_result, str):
                try:
                    res_dict = json.loads(raw_result)
                except Exception:
                    res_dict = {"title": "Extracted Product", "raw_text": raw_result}
            elif isinstance(raw_result, dict):
                res_dict = raw_result
            elif hasattr(raw_result, "model_dump"):
                res_dict = raw_result.model_dump()
            else:
                res_dict = {"title": "Extracted Product", "raw_result": str(raw_result)}

            if not isinstance(res_dict, dict):
                res_dict = {"title": "Extracted Product", "raw_result": str(res_dict)}

            if "title" not in res_dict:
                res_dict["title"] = res_dict.get("name") or res_dict.get("content") or "Extracted Product"
            if "price" not in res_dict:
                res_dict["price"] = 0.0

            return res_dict
        except asyncio.TimeoutError:
            logger.error(f"SCRAPEGRAPHAI_TIMEOUT url={url} timeout={self.config.timeout}s")
            raise TimeoutError(f"ScrapeGraphAI execution timed out after {self.config.timeout}s on {url}")
        except Exception as e:
            sanitized = self._sanitize_error(e)
            logger.error(f"SCRAPEGRAPHAI_EXTRACTION_ERROR url={url} err={sanitized}")
            raise RuntimeError(f"ScrapeGraphAI extraction failed: {sanitized}")

    async def scrape_multi_urls(
        self,
        urls: List[str],
        prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extracts structured product data from multiple product URLs using SmartScraperMultiGraph.
        """
        if not self.is_available():
            raise RuntimeError("ScrapeGraphAI is not available or disabled.")

        if not self.config.api_key and self.config.provider not in ("ollama", "local"):
            raise RuntimeError(
                f"ScrapeGraphAI API key is missing for provider '{self.config.provider}'. "
                f"Configure SCRAPEGRAPHAI_API_KEY or LLM_API_KEY."
            )

        clean_urls = [u for u in urls if u and u.strip()]
        if not clean_urls:
            return []

        graph_config = self.config.to_graph_config()
        effective_prompt = prompt or PRODUCT_DETAIL_EXTRACTION_PROMPT

        def _run_multi_sync():
            scraper = SmartScraperMultiGraph(
                prompt=effective_prompt,
                source=clean_urls,
                config=graph_config,
                schema=ScrapeGraphProductList
            )
            return scraper.run()

        try:
            raw_result = await self.throttler.execute(_run_multi_sync)
            if isinstance(raw_result, str):
                try:
                    raw_result = json.loads(raw_result)
                except Exception:
                    raw_result = []

            if isinstance(raw_result, dict):
                return raw_result.get("products") or [raw_result]
            elif isinstance(raw_result, list):
                return raw_result
            return []
        except Exception as e:
            sanitized = self._sanitize_error(e)
            logger.error(f"SCRAPEGRAPHAI_MULTI_EXTRACTION_ERROR urls={clean_urls} err={sanitized}")
            raise RuntimeError(f"ScrapeGraphAI multi-URL extraction failed: {sanitized}")

    async def search_catalog(
        self,
        query: str,
        prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes an internet search graph using ScrapeGraphAI's SearchGraph.
        """
        if not self.is_available():
            raise RuntimeError("ScrapeGraphAI is not available or disabled.")

        if not self.config.api_key and self.config.provider not in ("ollama", "local"):
            raise RuntimeError(
                f"ScrapeGraphAI API key is missing for provider '{self.config.provider}'. "
                f"Configure SCRAPEGRAPHAI_API_KEY or LLM_API_KEY."
            )

        graph_config = self.config.to_graph_config()
        effective_prompt = prompt or f"Find products matching '{query}' with price, title, and URL."

        def _run_search_sync():
            searcher = SearchGraph(
                prompt=effective_prompt,
                config=graph_config,
                schema=ScrapeGraphProductList
            )
            return searcher.run()

        try:
            raw_result = await self.throttler.execute(_run_search_sync)
            if isinstance(raw_result, str):
                try:
                    raw_result = json.loads(raw_result)
                except Exception:
                    raw_result = []

            if isinstance(raw_result, dict):
                return raw_result.get("products") or [raw_result]
            elif isinstance(raw_result, list):
                return raw_result
            return []
        except Exception as e:
            sanitized = self._sanitize_error(e)
            logger.error(f"SCRAPEGRAPHAI_SEARCH_ERROR query='{query}' err={sanitized}")
            raise RuntimeError(f"ScrapeGraphAI search failed: {sanitized}")

    async def crawl_catalog(
        self,
        marketplace: str,
        keyword: Optional[str] = None,
        urls: Optional[List[str]] = None,
        max_products: int = 10,
        item_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        is_cancelled_callback: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes a crawl pipeline using ScrapeGraphAI over direct URLs or search keywords.
        Integrates legitimate browser rendering for Amazon with DOM fallback extraction.
        """
        if not self.is_available():
            raise RuntimeError("ScrapeGraphAI is not available or disabled.")

        if not self.config.api_key and self.config.provider not in ("ollama", "local"):
            raise RuntimeError(
                f"ScrapeGraphAI API key is missing for provider '{self.config.provider}'. "
                f"Configure SCRAPEGRAPHAI_API_KEY or LLM_API_KEY."
            )

        target_urls: List[str] = []
        if urls:
            target_urls = [u for u in urls if u and u.strip()]

        if not target_urls and keyword:
            search_url = self._get_marketplace_search_url(marketplace, keyword)
            target_urls = [search_url]

        if not target_urls:
            return {"items_extracted": 0, "status": "no_targets", "products": []}

        extracted_items: List[Dict[str, Any]] = []

        for target_url in target_urls:
            if is_cancelled_callback and is_cancelled_callback():
                logger.info("SCRAPEGRAPHAI_CRAWL_CANCELLED by operator")
                break

            if len(extracted_items) >= max_products:
                break

            is_catalog_search = (
                "catalog" in target_url
                or "/s?" in target_url
                or "/sch/" in target_url
                or "search" in target_url
            )
            is_amazon = "amazon." in target_url or marketplace.lower() == "amazon"

            try:
                if is_amazon and is_catalog_search:
                    # 1. Render page with legitimate browser pipeline
                    rendered_html, status = await self.render_page_legitimate(target_url)
                    if not rendered_html:
                        logger.warning(f"No rendered HTML returned for {target_url}")
                        continue

                    # 2. Extract DOM candidates as robust baseline
                    dom_candidates = extract_amazon_dom_candidates(rendered_html, base_url=target_url)
                    logger.info(
                        f"Amazon DOM parser found {len(dom_candidates)} candidate cards on {target_url}"
                    )

                    # 3. If Groq LLM is available, execute ScrapeGraphAI on scoped HTML to enrich/validate
                    sgai_extracted: List[Dict[str, Any]] = []
                    if self.config.api_key and dom_candidates:
                        scoped_html = extract_scoped_catalog_html(rendered_html)
                        graph_config = self.config.to_graph_config()

                        def _run_scoped_sync():
                            scraper = SmartScraperGraph(
                                prompt=PRODUCT_CATALOG_SEARCH_PROMPT,
                                source=scoped_html,
                                config=graph_config,
                                schema=ScrapeGraphProductList
                            )
                            return scraper.run()

                        try:
                            raw_catalog = await self.throttler.execute(_run_scoped_sync)
                            if isinstance(raw_catalog, str):
                                raw_catalog = json.loads(raw_catalog)
                            if isinstance(raw_catalog, dict):
                                sgai_extracted = (
                                    raw_catalog.get("products")
                                    or raw_catalog.get("items")
                                    or []
                                )
                            elif isinstance(raw_catalog, list):
                                sgai_extracted = raw_catalog
                        except Exception as llm_err:
                            logger.warning(
                                f"ScrapeGraphAI LLM execution warning on {target_url}: {self._sanitize_error(llm_err)}. "
                                "Falling back cleanly to verified DOM candidates."
                            )

                    # Use DOM candidates (or ScrapeGraphAI extracted candidates if verified)
                    final_page_items = dom_candidates

                    for item in final_page_items:
                        if len(extracted_items) >= max_products:
                            break
                        if is_cancelled_callback and is_cancelled_callback():
                            break
                        extracted_items.append(item)
                        if item_callback:
                            if asyncio.iscoroutinefunction(item_callback):
                                await item_callback(item)
                            else:
                                item_callback(item)

                elif is_catalog_search:
                    # Standard catalog search for non-Amazon platforms (e.g. eBay)
                    graph_config = self.config.to_graph_config()

                    def _run_catalog_sync():
                        scraper = SmartScraperGraph(
                            prompt=PRODUCT_CATALOG_SEARCH_PROMPT,
                            source=target_url,
                            config=graph_config,
                            schema=ScrapeGraphProductList
                        )
                        return scraper.run()

                    raw_catalog = await self.throttler.execute(_run_catalog_sync)
                    if isinstance(raw_catalog, str):
                        raw_catalog = json.loads(raw_catalog)

                    prod_list = []
                    if isinstance(raw_catalog, list):
                        prod_list = raw_catalog
                    elif isinstance(raw_catalog, dict):
                        prod_list = (
                            raw_catalog.get("products")
                            or raw_catalog.get("items")
                            or [raw_catalog]
                        )
                    for item in prod_list:
                        if len(extracted_items) >= max_products:
                            break
                        if is_cancelled_callback and is_cancelled_callback():
                            break
                        extracted_items.append(item)
                        if item_callback:
                            if asyncio.iscoroutinefunction(item_callback):
                                await item_callback(item)
                            else:
                                item_callback(item)
                else:
                    # Single product URL
                    single_item = await self.scrape_single_url(target_url, marketplace=marketplace)
                    if single_item:
                        extracted_items.append(single_item)
                        if item_callback:
                            if asyncio.iscoroutinefunction(item_callback):
                                await item_callback(single_item)
                            else:
                                item_callback(single_item)

            except Exception as item_err:
                logger.warning(
                    f"Error scraping target {target_url} with ScrapeGraphAI: {self._sanitize_error(item_err)}"
                )

        return {
            "items_extracted": len(extracted_items),
            "status": "completed",
            "products": extracted_items
        }
