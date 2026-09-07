"""
Factual Prompt Templates for ScrapeGraphAI.

Enforces strict factual extraction from web pages.
Explicitly prohibits calculation or hallucination of intelligence scores.
"""

PRODUCT_DETAIL_EXTRACTION_PROMPT = """
You are a precise, factual e-commerce data extraction engine.
Extract the product information that is explicitly and visibly present on this web page.

Rules:
1. Extract only factual data directly visible on the page.
2. If a field is not present or cannot be determined with certainty, return null or an empty list.
3. DO NOT infer, guess, or fabricate missing values.
4. Extract the exact product title, current selling price (numeric), original price before discount, discount amount, currency code (e.g., PKR, USD), availability/stock status, brand, seller name, specifications, image URLs, and customer reviews.
5. NEVER calculate, estimate, or hallucinate:
   - trend scores
   - market share
   - sales growth
   - velocity
   - demand forecasts
   - opportunity scores
   All predictive and analytical metrics are computed externally.
6. Return clean structured JSON conforming to the requested schema.
"""

PRODUCT_CATALOG_SEARCH_PROMPT = """
You are a precise, factual e-commerce product search and listing extraction engine.
Extract the list of product cards or search results that are explicitly displayed on this page.

Rules:
1. For each product card found on the page, extract:
   - product title
   - price (numeric)
   - original price (if on sale)
   - currency code
   - rating (if present)
   - review count (if present)
   - product direct URL
   - primary image URL
   - seller or store name (if displayed)
   - in_stock status
2. DO NOT fabricate products that do not exist on the page.
3. If fewer products are visible than requested, return only the products that actually exist.
4. Return null for fields not explicitly present on the product card.
5. NEVER calculate trend scores, growth rates, or demand metrics.
"""
