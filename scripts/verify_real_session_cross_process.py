import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from datetime import datetime, timezone

from backend.app.api.deps import get_marketplace_product_repository
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.models.domain import DarazAuthSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("cross_process_verify")


def verify_cross_process_session():
    print("=" * 65)
    print("TRENDPULSE AI: CROSS-PROCESS DARAZ OAUTH SESSION VERIFICATION")
    print("=" * 65)

    repo = get_marketplace_product_repository()
    prod_count = repo.count_products("daraz")
    print(f"Products in repository: {prod_count}")

    # Inspect disk file directly
    disk_path = os.path.join("backend", "app", "data", "marketplace_products_store.json")
    disk_session_count = 0
    if os.path.exists(disk_path):
        with open(disk_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        disk_sessions = disk_data.get("auth_sessions", [])
        disk_session_count = len(disk_sessions)
        print(f"Direct Disk File Check ({disk_path}):")
        print(f"  Auth sessions in file: {disk_session_count}")
        for s in disk_sessions:
            print(f"  Session ID: {s.get('id')}")
            print(f"  Seller ID: {s.get('seller_id')}")
            print(f"  Account: {s.get('account')}")
            print(f"  Country: {s.get('country')}")
            print(f"  Expires in: {s.get('expires_in')} seconds")
            print(f"  Authorized at: {s.get('authorized_at')}")

    # Inspect via repository methods
    sess = repo.get_auth_session()
    if not sess:
        print("\nRESULT: No active session resolved by repository.")
        return False

    print("\nRepository Resolved Active Session (Metadata Only):")
    print(f"  Session ID: {sess.id}")
    print(f"  Seller ID: {sess.seller_id}")
    print(f"  Account: {sess.account}")
    print(f"  Country: {sess.country}")
    print(f"  Status: {sess.status}")
    print(f"  Expires In: {sess.expires_in}")
    print(f"  Authorized At: {sess.authorized_at}")
    print(f"  Is Test Session: {repo.is_test_session(sess)}")

    return True


if __name__ == "__main__":
    verify_cross_process_session()
