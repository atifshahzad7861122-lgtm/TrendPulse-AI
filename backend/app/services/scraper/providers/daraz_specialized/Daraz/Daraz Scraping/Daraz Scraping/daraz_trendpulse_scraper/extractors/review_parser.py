import asyncio
from captcha_handler import handle_captcha_if_present
from logger import logger

async def extract_product_reviews(page, max_pages: int = 10) -> list:
    """Extracts customer reviews across paginated review pages."""
    logger.info("Locating customer reviews...")
    for _ in range(3):
        await page.evaluate("window.scrollBy({ top: 900, behavior: 'smooth' })")
        await asyncio.sleep(1)

    reviews = []
    current_page = 1

    while current_page <= max_pages:
        await handle_captcha_if_present(page)
        try:
            await page.wait_for_selector(".mod-reviews .item", timeout=6000)
            items = await page.query_selector_all(".mod-reviews .item")
        except Exception:
            logger.info(f"End of reviews reached or no reviews on page {current_page}.")
            break

        for rev in items:
            u_el = await rev.query_selector(".user-name, .middle")
            d_el = await rev.query_selector(".title.right, .date")
            c_el = await rev.query_selector(".content, .review-content")
            s_el = await rev.query_selector(".skuInfo, [class*='sku']")
            stars = await rev.query_selector_all(".star")

            img_nodes = await rev.query_selector_all(".review-image img, .image-item img")
            images = [await img.get_attribute("src") for img in img_nodes if await img.get_attribute("src")]

            reviews.append({
                "page": current_page,
                "reviewer": (await u_el.inner_text()).strip() if u_el else "Anonymous",
                "date": (await d_el.inner_text()).strip() if d_el else "N/A",
                "rating": len(stars) if stars else 5,
                "variation": (await s_el.inner_text()).strip() if s_el else "N/A",
                "content": (await c_el.inner_text()).strip() if c_el else "No written review",
                "images": ", ".join(images)
            })

        # Next button pagination check
        next_btn = await page.query_selector(".next-btn, .ant-pagination-next, button[class*='next']")
        if not next_btn:
            break
        
        is_disabled = await next_btn.get_attribute("aria-disabled")
        btn_class = await next_btn.get_attribute("class") or ""
        if is_disabled == "true" or "disabled" in btn_class.lower():
            break

        await next_btn.scroll_into_view_if_needed()
        await next_btn.click()
        current_page += 1
        await asyncio.sleep(2)

    logger.info(f"Total reviews extracted: {len(reviews)} across {current_page - 1} pages.")
    return reviews
