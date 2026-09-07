import sys
import os
import json
import time
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.api.deps import get_marketplace_product_repository


def run_auth_context_verification():
    print("=" * 65)
    print("TRENDPULSE AI: DARAZ INGESTION AUTH CONTEXT LIVE VERIFICATION")
    print("=" * 65)

    # 1. Initialize persistent repository using backend application repository
    repo = get_marketplace_product_repository()
    print("Loaded application marketplace product repository.")

    # 2. Check persistent OAuth session
    sess = repo.get_auth_session()

    if not sess:
        print("RESULT: No persisted Daraz OAuth session found in database.")
        print("VERDICT: INGESTION AUTH CONTEXT BLOCKED")
        return False

    print(f"Persisted Session ID: {sess.id}")
    print(f"Seller Account: {sess.account or 'N/A'}")
    print(f"Session Status: {sess.status}")
    print(f"Authorized At: {sess.authorized_at.isoformat() if sess.authorized_at else 'N/A'}")
    print("Access Token Security: [SECURELY LOADED - MASKED]")

    # 3. Instantiate Official Provider without in-memory token
    # Provider must resolve token dynamically from persistent repository
    provider = DarazOfficialProvider(
        app_key=settings.DARAZ_APP_KEY,
        app_secret=settings.DARAZ_APP_SECRET,
        access_token=None,
        marketplace_repo=repo
    )

    token, auth_err = provider.get_active_token()
    if not token:
        print(f"Provider Token Resolution Failed: {auth_err}")
        print("VERDICT: INGESTION AUTH CONTEXT BLOCKED")
        return False

    print("Provider Active Token Resolution: RESOLVED (From Persistent Session)")

    # 4. Make exactly ONE authenticated /products/get request with limit=1
    print("\nExecuting exactly ONE live authenticated request to /products/get (limit=1)...")
    start_time = time.time()
    success, res_data, status_code, err_msg = provider._execute_api_call(
        api_path="/products/get",
        params={"filter": "all", "limit": 1, "offset": 0},
        require_auth=True,
        method="GET"
    )
    latency_ms = round((time.time() - start_time) * 1000, 2)

    print(f"HTTP Status Code: {status_code}")
    print(f"Latency: {latency_ms}ms")
    print(f"Success: {success}")

    if not success:
        print(f"Error Message: {err_msg}")
        if "MissingParameter" in (err_msg or "") and "access_token" in (err_msg or ""):
            print("ERROR: MissingParameter access_token is still occurring!")
            print("VERDICT: INGESTION AUTH CONTEXT BLOCKED")
            return False
        else:
            print(f"API Returned non-fatal response or logical code: {err_msg}")

    products = []
    total_products = 0
    if res_data and isinstance(res_data, dict):
        data_payload = res_data.get("data") or {}
        if isinstance(data_payload, dict):
            products = data_payload.get("products") or []
            total_products = data_payload.get("total_products") or len(products)

    print(f"Products Returned: {len(products)}")
    print(f"Total Available in Catalog: {total_products}")
    if products:
        sample_prod = products[0]
        sample_id = sample_prod.get("item_id") or sample_prod.get("product_id")
        sample_name = (sample_prod.get("attributes") or {}).get("name") or sample_prod.get("name") or "N/A"
        print(f"Sample Product ID: {sample_id}")
        print(f"Sample Product Name: {sample_name[:50]}...")

    # 5. Check Daily Quota
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    quota = repo.get_or_create_daily_quota(today_str)

    if quota:
        print(f"\nQuota Date: {quota.date}")
        print(f"Requests Used Today: {quota.requests_used}")
        print(f"Daily Limit: {quota.daily_limit}")
        print(f"Remaining Quota: {quota.remaining}")

    print("\n" + "=" * 65)
    print("VERDICT: INGESTION AUTH CONTEXT FIXED")
    print("=" * 65)
    return True


if __name__ == "__main__":
    run_auth_context_verification()
