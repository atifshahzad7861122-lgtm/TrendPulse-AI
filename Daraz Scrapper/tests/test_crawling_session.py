"""Unit tests for UniversalSessionManager and session persistence."""

import pytest
from app.crawling.models import MarketplaceType
from app.crawling.session import UniversalSessionManager


def test_session_creation_and_cookie_update(tmp_path):
    mgr = UniversalSessionManager(persistence_dir=tmp_path)
    session = mgr.get_or_create_session(MarketplaceType.AMAZON, session_id="amazon_test_session")

    assert session.session_id == "amazon_test_session"
    assert session.marketplace == MarketplaceType.AMAZON
    assert len(session.cookies) == 0

    mgr.update_cookies("amazon_test_session", {"session-id": "123-456-789", "ubid-main": "987-654"})
    
    # Reload from disk
    mgr2 = UniversalSessionManager(persistence_dir=tmp_path)
    reloaded = mgr2.get_or_create_session(MarketplaceType.AMAZON, session_id="amazon_test_session")
    assert reloaded.cookies["session-id"] == "123-456-789"
    assert reloaded.cookies["ubid-main"] == "987-654"
