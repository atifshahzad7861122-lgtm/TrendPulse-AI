"""Unified Daraz Specialized Scraping Engine."""
import asyncio
import logging
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple, Callable
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from bs4 import BeautifulSoup

from .config import (
    DEFAULT_DOMAIN, DEFAULT_HEADLESS, DEFAULT_SLOW_MO,
    DEFAULT_TIMEOUT_MS, DEFAULT_MAX_REVIEW_PAGES, BROWSER_ARGS,
    DEFAULT_USER_AGENT, VIEWPORT
)
from .challenge import detect_challenge, handle_challenge_if_present
from .extractors.catalog_parser import parse_page_data_json, extract_products_from_json, parse_dom_item
from .extractors.product_parser import extract_product_details
from .extractors.review_parser import extract_product_reviews
from .extractors.variations_parser import extract_variations

logger = logging.getLogger("trendpulse.scraper.daraz.engine")


class DarazSpecializedScraperEngine:
    """
    High-performance specialized scraper engine for Daraz.pk and regional domains.
    Provides Playwright-driven headless / headed execution, window.pageData extraction,
    DOM fallbacks, multi-page customer reviews, seller metrics, and specifications.
    """

    def __init__(
        self,
        headless: bool = True,
        slow_mo: int = 100,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.headless = headless
        self.slow_mo = slow_mo
        self.timeout_ms = timeout_ms
        self.user_agent = user_agent

    async def _create_context(self, p: Any) -> BrowserContext:
        browser = await p.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=BROWSER_ARGS
        )
        context = await browser.new_context(
            user_agent=self.user_agent,
            viewport=VIEWPORT,
            ignore_https_errors=True
        )
        return context

    async def crawl_keyword_search(
        self,
        query: Optional[str] = None,
        keyword: Optional[str] = None,
        domain: str = DEFAULT_DOMAIN,
        max_pages: int = 1,
        max_products: int = 20,
        max_items: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
        """
        Crawls Daraz search catalog for given query keyword across pages.
        Extracts items from window.pageData or falls back to DOM parsing.
        """
        search_query = query or keyword or ""
        limit_products = max_items or max_products
        products: List[Dict[str, Any]] = []
        is_challenged = False
        challenge_reason = None

        async with async_playwright() as p:
            context = await self._create_context(p)
            page = await context.new_page()

            try:
                for current_page in range(1, max_pages + 1):
                    if len(products) >= limit_products:
                        break

                    encoded_query = urllib.parse.quote_plus(search_query)
                    url = f"https://www.{domain}/catalog/?q={encoded_query}&page={current_page}"
                    logger.info(f"Navigating to Daraz search page {current_page}: {url}")

                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                        try:
                            await page.wait_for_selector('div[data-qa-locator="product-item"], div.gridItem, div[class*="box--ujueT"], div[class*="c2prKC"], div.RfADt', timeout=5000)
                        except Exception:
                            pass
                        await asyncio.sleep(1.0)

                        # Challenge Check
                        has_chal, reason = await detect_challenge(page)
                        if has_chal:
                            is_challenged = True
                            challenge_reason = reason
                            logger.warning(f"Challenge encountered on search page {current_page}: {reason}")
                            break

                        # Extract using window.pageData first
                        html_content = await page.content()
                        page_data = parse_page_data_json(html_content)
                        if not page_data:
                            try:
                                page_data = await page.evaluate("() => window.pageData")
                            except Exception:
                                page_data = None

                        if page_data:
                            page_products = extract_products_from_json(page_data, domain)
                            logger.info(f"Extracted {len(page_products)} products from pageData JSON on page {current_page}")
                            for prod in page_products:
                                if not any(p_item.get('product_id') == prod.get('product_id') for p_item in products):
                                    products.append(prod)
                                    if len(products) >= max_products:
                                        break
                        else:
                            # DOM fallback
                            soup = BeautifulSoup(html_content, 'html.parser')
                            items = soup.select('div[data-qa-locator="product-item"], div.gridItem, div[class*="box--ujueT"], div[class*="c2prKC"], div[data-tracking="product-card"], [class*="product-item"]')
                            logger.info(f"DOM fallback found {len(items)} product elements on page {current_page}")
                            for idx, item in enumerate(items):
                                try:
                                    prod = parse_dom_item(item, domain, idx)
                                    if prod.get('title') and not any(p_item.get('product_url') == prod.get('product_url') for p_item in products):
                                        products.append(prod)
                                        if len(products) >= max_products:
                                            break
                                except Exception as parse_err:
                                    logger.debug(f"Error parsing DOM item {idx}: {parse_err}")

                    except Exception as e:
                        logger.error(f"Error loading search page {current_page}: {e}")

            finally:
                await context.close()

        return products, is_challenged, challenge_reason

    async def crawl_product_detail(
        self,
        url: str,
        max_review_pages: int = DEFAULT_MAX_REVIEW_PAGES,
        context: Optional[BrowserContext] = None,
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], bool, Optional[str]]:
        """
        Crawls a single Daraz product page for complete metadata, specs, seller metrics, and reviews.
        Returns (product_data, reviews_list, is_challenged, challenge_reason).
        """
        product_data: Optional[Dict[str, Any]] = None
        reviews: List[Dict[str, Any]] = []
        is_challenged = False
        challenge_reason = None

        created_local_context = False
        ctx = context

        async def _extract_on_context(current_ctx: BrowserContext):
            nonlocal product_data, reviews, is_challenged, challenge_reason
            page = await current_ctx.new_page()
            try:
                logger.info(f"Navigating to product URL: {url}")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=min(self.timeout_ms, 30000))
                except Exception as nav_err:
                    logger.warning(f"Navigation warning for {url}: {nav_err}. Proceeding with extraction on loaded DOM.")
                await asyncio.sleep(1.0)

                # Challenge Check
                has_chal, reason = await detect_challenge(page)
                if has_chal:
                    is_challenged = True
                    challenge_reason = reason
                    logger.warning(f"Challenge encountered on product URL {url}: {reason}")
                    return

                # Extract Product Details & Specifications
                product_data = await extract_product_details(page, url, challenge_detector=detect_challenge)
                if isinstance(product_data, dict):
                    product_data.setdefault("marketplace", "daraz")

                # Extract Reviews
                reviews = await extract_product_reviews(page, max_pages=max_review_pages, challenge_detector=detect_challenge)

            except Exception as e:
                logger.error(f"Error scraping product detail {url}: {e}")
            finally:
                try:
                    await page.close()
                except Exception:
                    pass

        if ctx is not None:
            await _extract_on_context(ctx)
        else:
            async with async_playwright() as p:
                local_ctx = await self._create_context(p)
                try:
                    await _extract_on_context(local_ctx)
                finally:
                    await local_ctx.close()

        return product_data, reviews, is_challenged, challenge_reason

    async def run_daraz_crawl_pipeline(
        self,
        keywords: Optional[List[str]] = None,
        urls: Optional[List[str]] = None,
        max_products: int = 10,
        max_review_pages: int = 1,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        item_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        is_cancelled_callback: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Full crawl workflow handling either a search discovery phase or direct URL list.
        Supports real-time item streaming via item_callback and instant cancellation.
        Reuses a single browser session across discovery and detail extraction.
        """
        extracted_items: List[Dict[str, Any]] = []
        search_map: Dict[str, Dict[str, Any]] = {}
        total_challenged = 0
        total_failed = 0

        target_urls: List[str] = []
        if urls:
            target_urls.extend(urls)

        async with async_playwright() as p:
            context = await self._create_context(p)
            try:
                # Step 1: Collect Target URLs & Search Catalog items if needed
                if keywords and len(target_urls) < max_products:
                    for kw in keywords:
                        if is_cancelled_callback and is_cancelled_callback():
                            break
                        if len(target_urls) >= max_products:
                            break

                        page = await context.new_page()
                        try:
                            encoded_query = urllib.parse.quote_plus(kw)
                            search_url = f"https://www.{DEFAULT_DOMAIN}/catalog/?q={encoded_query}&page=1"
                            logger.info(f"Navigating to Daraz search page: {search_url}")
                            await page.goto(search_url, wait_until="domcontentloaded", timeout=min(self.timeout_ms, 25000))
                            await asyncio.sleep(1.5)

                            has_chal, reason = await detect_challenge(page)
                            if has_chal:
                                total_challenged += 1
                                logger.warning(f"Challenge encountered on search for '{kw}': {reason}")
                            else:
                                html_content = await page.content()
                                page_data = parse_page_data_json(html_content)
                                if not page_data:
                                    try:
                                        page_data = await page.evaluate("() => window.pageData")
                                    except Exception:
                                        page_data = None

                                if page_data:
                                    page_products = extract_products_from_json(page_data, DEFAULT_DOMAIN)
                                    logger.info(f"Extracted {len(page_products)} products from pageData JSON")
                                    for prod in page_products:
                                        u = prod.get('product_url')
                                        if u and u not in target_urls:
                                            target_urls.append(u)
                                            search_map[u] = prod
                                            if len(target_urls) >= max_products:
                                                break
                                else:
                                    soup = BeautifulSoup(html_content, 'html.parser')
                                    items = soup.select('div[data-qa-locator="product-item"], .gridItem, [class*="product-item"], div.RfADt, div[class*="box--ujueT"], div[class*="c2prKC"]')
                                    logger.info(f"DOM fallback found {len(items)} product elements")
                                    for idx, item in enumerate(items):
                                        try:
                                            prod = parse_dom_item(item, DEFAULT_DOMAIN, idx)
                                            u = prod.get('product_url')
                                            if u and u not in target_urls:
                                                target_urls.append(u)
                                                search_map[u] = prod
                                                if len(target_urls) >= max_products:
                                                    break
                                        except Exception as parse_err:
                                            logger.debug(f"Error parsing DOM item {idx}: {parse_err}")
                        except Exception as s_err:
                            logger.error(f"Error during search discovery for '{kw}': {s_err}")
                        finally:
                            try:
                                await page.close()
                            except Exception:
                                pass

                logger.info(f"Daraz specialized pipeline ready to process {len(target_urls)} product targets.")

                # Step 2: Extract Details with immediate fallback to search catalog data
                for idx, u in enumerate(target_urls):
                    if is_cancelled_callback and is_cancelled_callback():
                        logger.info("Daraz crawl cancelled by caller.")
                        break

                    sp_fallback = search_map.get(u)
                    p_data: Optional[Dict[str, Any]] = None
                    p_revs: List[Dict[str, Any]] = []
                    is_chal = False
                    chal_reason = None

                    try:
                        p_data, p_revs, is_chal, chal_reason = await self.crawl_product_detail(
                            url=u,
                            max_review_pages=max_review_pages,
                            context=context
                        )
                    except Exception as e:
                        logger.warning(f"Error extracting detail for {u}: {e}; using search catalog fallback.")

                    if is_chal:
                        total_challenged += 1

                    # Use detail data or fallback to search product data
                    final_item: Optional[Dict[str, Any]] = None
                    if p_data and p_data.get("title"):
                        p_data["reviews"] = p_revs
                        final_item = p_data
                    elif sp_fallback:
                        final_item = dict(sp_fallback)
                        final_item["reviews"] = []

                    if final_item:
                        extracted_items.append(final_item)
                        if item_callback:
                            try:
                                res = item_callback(final_item)
                                if asyncio.iscoroutine(res):
                                    await res
                            except Exception as cb_err:
                                logger.warning(f"Item callback error for {u}: {cb_err}")
                    else:
                        total_failed += 1

                    if progress_callback:
                        progress_callback({
                            "current": idx + 1,
                            "total": len(target_urls),
                            "persisted": len(extracted_items),
                            "challenged": total_challenged,
                            "failed": total_failed
                        })
            finally:
                await context.close()

        return {
            "products": extracted_items,
            "total_fetched": len(extracted_items),
            "challenged_count": total_challenged,
            "failed_count": total_failed
        }
