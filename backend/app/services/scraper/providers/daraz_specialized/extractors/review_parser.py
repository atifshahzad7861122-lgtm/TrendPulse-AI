"""Paginated Customer Reviews Extractor for Daraz."""
import asyncio
import logging
from typing import List, Dict, Any

logger = logging.getLogger("trendpulse.scraper.daraz.reviews")


async def extract_product_reviews(page: Any, max_pages: int = 2, challenge_detector: Any = None) -> List[Dict[str, Any]]:
    """
    Extracts customer reviews across paginated review pages with star ratings, buyer info, dates, and images.
    Uses optimized batch client-side evaluation for sub-second execution.
    """
    reviews: List[Dict[str, Any]] = []
    
    # Quick scroll towards reviews container
    try:
        await page.evaluate("window.scrollBy({ top: 1000, behavior: 'auto' })")
        await asyncio.sleep(0.2)
    except Exception:
        pass

    current_page = 1

    while current_page <= max_pages:
        if challenge_detector:
            chal_res = await challenge_detector(page)
            has_chal = chal_res[0] if isinstance(chal_res, tuple) else bool(chal_res)
            if has_chal:
                logger.warning(f"Challenge encountered while scraping reviews on page {current_page}.")
                break

        # Fast client-side review extraction
        try:
            page_reviews = await page.evaluate("""() => {
                const items = document.querySelectorAll('.mod-reviews .item, .pdp-mod-review .item');
                const results = [];
                items.forEach((rev, idx) => {
                    const u_el = rev.querySelector('.user-name, .middle');
                    const d_el = rev.querySelector('.title.right, .date');
                    const c_el = rev.querySelector('.content, .review-content');
                    const s_el = rev.querySelector('.skuInfo, [class*="sku"]');
                    const starNodes = rev.querySelectorAll('.star, .i-rate-star');
                    
                    let calc_rating = 0;
                    starNodes.forEach(star => {
                        const h = star.innerHTML || '';
                        const cls = star.getAttribute('class') || '';
                        if (h.includes('rgb(255, 200, 60)') || cls.includes('star-filled') || cls.includes('Dy1nx')) {
                            calc_rating += 1;
                        }
                    });
                    const rating = calc_rating > 0 ? calc_rating : (starNodes.length || 5.0);

                    const images = [];
                    const imgNodes = rev.querySelectorAll('.review-image img, .image-item img');
                    imgNodes.forEach(img => {
                        let src = img.getAttribute('src') || '';
                        if (src) {
                            if (src.startsWith('//')) src = 'https:' + src;
                            images.push(src);
                        }
                    });

                    results.push({
                        reviewer_name: u_el ? u_el.innerText.trim() : 'Daraz Customer',
                        rating: Number(rating),
                        date_str: d_el ? d_el.innerText.trim() : 'N/A',
                        variation: s_el ? s_el.innerText.trim() : 'Standard',
                        content: c_el ? c_el.innerText.trim() : 'No written review',
                        review_text: c_el ? c_el.innerText.trim() : 'No written review',
                        images: images,
                        verified_purchase: true
                    });
                });
                return results;
            }""")
            if page_reviews:
                for idx, r in enumerate(page_reviews):
                    r["page"] = current_page
                    r["review_id"] = f"rev_p{current_page}_{idx+1}"
                    reviews.append(r)
        except Exception as e:
            logger.debug(f"Error evaluating reviews batch: {e}")

        if current_page >= max_pages:
            break

        # Check for pagination next button
        try:
            next_btn = await page.query_selector(".next-btn, .ant-pagination-next, button[class*='next']")
            if not next_btn:
                break

            is_disabled = await next_btn.get_attribute("aria-disabled")
            btn_class = (await next_btn.get_attribute("class")) or ""
            if is_disabled == "true" or "disabled" in btn_class.lower():
                break

            await next_btn.click()
            current_page += 1
            await asyncio.sleep(0.8)
        except Exception:
            break

    logger.info(f"Extracted {len(reviews)} reviews across {current_page} pages.")
    return reviews
