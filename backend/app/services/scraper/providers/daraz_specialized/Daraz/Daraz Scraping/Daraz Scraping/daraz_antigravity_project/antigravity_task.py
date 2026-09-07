import asyncio
import sys
from scraper_engine import run_daraz_scraper
from excel_exporter import export_to_excel

async def main():
    # Set console encoding to UTF-8 to support emoji printing
    sys.stdout.reconfigure(encoding='utf-8')
    
    # Provide the target URL or read from CLI argument
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        target_url = "https://www.daraz.pk/products/sample-product-i123456789.html"

    output_excel = "daraz_scraped_output.xlsx"
    max_review_pages = 3

    print("="*65)
    print("🚀 GOOGLE ANTIGRAVITY AGENT WORKFLOW: DARAZ SCRAPER")
    print(f"Target URL: {target_url}")
    print(f"Output File: {output_excel}")
    print("="*65)

    # Step 1: Scrape
    product_data, specs, reviews = await run_daraz_scraper(target_url, max_review_pages=max_review_pages)

    # Step 2: Export
    print(f"\n[ANTIGRAVITY AGENT] Writing data to {output_excel}...")
    saved_path = export_to_excel(product_data, specs, reviews, output_filepath=output_excel)

    print("\n" + "="*65)
    print(f"✅ TASK COMPLETED SUCCESSFULLY!")
    print(f"📊 Total Specifications Extracted: {len(specs)}")
    print(f"💬 Total Reviews Extracted: {len(reviews)}")
    print(f"📁 Excel Artifact Saved: {saved_path}")
    print("="*65)

if __name__ == "__main__":
    asyncio.run(main())
