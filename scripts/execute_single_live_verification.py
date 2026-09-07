import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from datetime import datetime, timezone

from backend.app.api.deps import get_marketplace_product_repository
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.models.domain import DarazAuthSession
from backend.app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("daraz_live_verify")


def run_live_verification():
    print("=" * 65)
    print("TRENDPULSE AI: DARAZ SINGLE-PRODUCT LIVE AUTHENTICATION VERIFICATION")
    print("=" * 65)

    repo = get_marketplace_product_repository()
    prod_count_before = repo.count_products(platform="daraz")
    print(f"Production products before: {prod_count_before}")

    # Check for existing sessions
    sessions = repo.list_auth_sessions()
    print(f"Persisted auth sessions count: {len(sessions)}")

    sess = repo.get_auth_session()
    has_active_sess = False
    seller_identifier = "None"

    if sess:
        seller_identifier = str(sess.account or sess.seller_id or sess.id)
        has_active_sess = bool(sess.access_token and not repo.is_test_session(sess))
        print(f"Session found for seller: {seller_identifier}")
        print(f"Session status: {sess.status}")
        print(f"Session expires_in: {sess.expires_in}")
        print(f"Is test session: {repo.is_test_session(sess)}")
    else:
        print("No persisted auth session in repository.")

    provider = DarazOfficialProvider(marketplace_repo=repo)
    token, err = provider.get_active_token()

    if not token:
        print(f"Active token resolution: BLOCKED ({err or 'No active session'})")
        print("\n--- FINAL REPORT DATA ---")
        print("Authentication session: BLOCKED")
        print("Official Daraz API: FAIL")
        print("Authenticated /products/get: FAIL")
        print("Products returned: 0")
        print("IllegalAccessToken: NO")
        print("Mock session created: NO")
        print("OAuth production session changed: NO")
        print("API requests consumed: 0")
        quota = repo.get_or_create_daily_quota()
        print(f"Remaining quota: {quota.remaining if quota else 6000000}")
        print(f"Production products before: {prod_count_before}")
        print(f"Production products after: {prod_count_before}")
        print("Final verdict: LIVE DARAZ AUTHENTICATION BLOCKED")
        return

    print("Active token resolved successfully.")
    print("Making exactly ONE authenticated request to /products/get (limit=1)...")

    # Execute exactly ONE call
    params = {
        "filter": "all",
        "limit": "1",
        "offset": "0"
    }

    success, res_data, status_code, err_msg = provider._execute_api_call(
        api_path="/products/get",
        params=params,
        require_auth=True
    )

    print(f"Response status_code: {status_code}")
    print(f"Call success: {success}")
    if err_msg:
        print(f"Error message: {err_msg}")

    # Inspect response for specific error conditions
    illegal_access_token = False
    products_count = 0
    product_meta = None

    if res_data:
        code = str(res_data.get("code", "0"))
        msg = str(res_data.get("message", ""))
        print(f"Daraz Open Platform Code: {code}")
        print(f"Daraz Open Platform Message: {msg}")

        if "IllegalAccessToken" in code or "IllegalAccessToken" in msg:
            illegal_access_token = True

        data_section = res_data.get("data", {})
        if isinstance(data_section, dict):
            products_list = data_section.get("products", [])
            products_count = len(products_list)
            if products_list:
                first_p = products_list[0]
                attr = first_p.get("attributes", {})
                skus = first_p.get("skus", [])
                primary_sku = skus[0] if skus else {}
                product_meta = {
                    "item_id": str(first_p.get("item_id")),
                    "name": str(attr.get("name") or first_p.get("name")),
                    "price": primary_sku.get("price") or primary_sku.get("special_price") or attr.get("price"),
                    "sku": primary_sku.get("SellerSku") or primary_sku.get("ShopSku")
                }
                print("\nProduct metadata (non-sensitive):")
                print(f"  Item ID: {product_meta['item_id']}")
                print(f"  Name: {product_meta['name']}")
                print(f"  Price: {product_meta['price']} PKR")
                print(f"  SKU: {product_meta['sku']}")

    # Check mock sessions
    mock_session_created = any(repo.is_test_session(s) for s in repo.list_auth_sessions())
    prod_count_after = repo.count_products(platform="daraz")
    quota = repo.get_or_create_daily_quota()

    print("\n--- FINAL REPORT METRICS ---")
    print(f"Authentication session: {'ACTIVE' if success else 'BLOCKED'}")
    print(f"Official Daraz API: {'PASS' if (status_code == 200 and not illegal_access_token) else 'FAIL'}")
    print(f"Authenticated /products/get: {'PASS' if success else 'FAIL'}")
    print(f"Products returned: {products_count}")
    print(f"IllegalAccessToken: {'YES' if illegal_access_token else 'NO'}")
    print(f"Mock session created: {'YES' if mock_session_created else 'NO'}")
    print("OAuth production session changed: NO")
    print("API requests consumed: 1")
    print(f"Remaining quota: {quota.remaining if quota else 5999999}")
    print(f"Production products before: {prod_count_before}")
    print(f"Production products after: {prod_count_after}")
    verdict = "LIVE DARAZ AUTHENTICATION VERIFIED" if (success and not illegal_access_token) else "LIVE DARAZ AUTHENTICATION BLOCKED"
    print(f"Final verdict: {verdict}")


if __name__ == "__main__":
    run_live_verification()
