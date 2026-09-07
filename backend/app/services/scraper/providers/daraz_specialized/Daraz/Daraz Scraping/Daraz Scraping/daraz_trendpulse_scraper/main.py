import asyncio
import sys
import os
import urllib.parse
from playwright.async_api import async_playwright
from config import CHROME_PROFILE_DIR, SLOW_MO_DELAY, MAX_REVIEW_PAGES_DEFAULT, DATABASE_PATH
from db_manager import DatabaseManager
from extractors.product_parser import extract_product_details
from extractors.review_parser import extract_product_reviews
from excel_exporter import export_to_excel
from logger import logger, print_dev_banner

def is_url(string):
    return string.startswith("http://") or string.startswith("https://") or "daraz." in string and "/products/" in string

async def crawl_search_results(page, query, domain, max_pages=1):
    """
    Crawls search results pages and extracts product detail URLs, inserting them into the database queue.
    """
    db = DatabaseManager()
    logger.info(f"Crawling Daraz Search Catalog for: '{query}' on {domain} (Pages: {max_pages})")
    
    urls_found = []
    for current_page in range(1, max_pages + 1):
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.{domain}/catalog/?q={encoded_query}&page={current_page}"
        logger.info(f"Navigating to search page {current_page}: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
            
            # Locate all links pointing to product detail pages
            links = await page.query_selector_all('div[data-qa-locator="product-item"] a, a[href*="/products/"]')
            
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    if href.startswith("//"):
                        href = "https:" + href
                    elif href.startswith("/"):
                        href = f"https://www.{domain}" + href
                    
                    if "?" in href:
                        href = href.split("?")[0]
                        
                    if "/products/" in href and href.endswith(".html") and href not in urls_found:
                        urls_found.append(href)
            
        except Exception as e:
            logger.error(f"Error crawling search page {current_page}: {e}")
            
    logger.info(f"Found {len(urls_found)} product detail URLs in search listing.")
    for u in urls_found:
        db.queue_product_url(u)
    db.close()

def cleanup_temporary_files():
    """Deletes unnecessary Excel files in the working directory other than final_out.xlsx."""
    logger.info("Cleaning up temporary spreadsheet files...")
    for file in os.listdir("."):
        if file.endswith(".xlsx") and file != "final_out.xlsx":
            try:
                os.remove(file)
                logger.info(f"Deleted unnecessary file: {file}")
            except Exception as e:
                logger.debug(f"Failed to delete {file}: {e}")

async def main():
    print_dev_banner()
    
    # Prompt the user in the terminal
    target_input = input("write your target product = ").strip()
    if not target_input:
        logger.error("No input entered. Exiting...")
        sys.exit(1)

    db = DatabaseManager()

    async with async_playwright() as p:
        logger.info("Initializing dedicated recording browser profile...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE_DIR,
            channel="chrome",
            headless=False,
            slow_mo=SLOW_MO_DELAY,
            viewport={"width": 1280, "height": 800},
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Step 1: Populating queue depending on input type
        db.clear_queue()
        if is_url(target_input):
            logger.info(f"Input detected as URL. Queuing target: {target_input}")
            db.queue_product_url(target_input)
        else:
            logger.info(f"Input detected as search query. Resolving catalog URLs...")
            await crawl_search_results(page, target_input, "daraz.pk", max_pages=1)

        # Step 2: Processing the queue item-by-item
        output_file = "final_out.xlsx"
        
        while True:
            target_url = db.get_next_queued_url()
            if not target_url:
                break
                
            logger.info(f"Scraping product page: {target_url}")
            db.update_queue_status(target_url, "processing")
            
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)

                # Extract Details & Specs
                product_data = await extract_product_details(page, target_url)
                
                # Check duplication checkpoint
                if db.is_already_crawled(product_data["product_id"]):
                    logger.info(f"Duplicate check: Product ID '{product_data['product_id']}' already indexed. Updating record...")

                # Extract Reviews
                reviews = await extract_product_reviews(page, max_pages=MAX_REVIEW_PAGES_DEFAULT)
                
                # Save product JSON to database
                db.save_product({**product_data, "reviews": reviews})
                
                # Export and append immediately to final_out.xlsx
                saved_file = export_to_excel(product_data, product_data["specifications"], reviews, output_filepath=output_file)
                logger.info(f"Product data appended to '{saved_file}'")
                
                db.update_queue_status(target_url, "completed")
            except Exception as e:
                logger.error(f"Failed to scrape {target_url}: {e}")
                db.update_queue_status(target_url, "failed")
                
            await asyncio.sleep(1.5)

        await context.close()
        db.close()
        
    # Clean up unnecessary files
    cleanup_temporary_files()
    logger.info("=" * 75)
    logger.info(f"✅ SCRAPING WORKFLOW COMPLETE! Saved output appended to: '{output_file}'")
    logger.info("=" * 75)

if __name__ == "__main__":
    asyncio.run(main())
