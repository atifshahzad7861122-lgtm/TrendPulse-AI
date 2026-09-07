"""Tests for SessionManager state, cookie persistence, and isolation."""

import os
import shutil
import tempfile
import time
import pytest
from app.core.session import SessionManager, SessionState


@pytest.fixture
def temp_session_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_session_manager_in_memory():
    manager = SessionManager(default_ttl_seconds=3600)
    session = await manager.get_or_create_session("test-sess-1", user_agent="CustomUA/1.0")

    assert session.session_id == "test-sess-1"
    assert session.user_agent == "CustomUA/1.0"
    assert session.is_expired is False

    # Update cookies
    cookies = [{"name": "daraz_token", "value": "xyz123", "domain": ".daraz.pk"}]
    await manager.update_cookies("test-sess-1", cookies)

    retrieved = await manager.get_or_create_session("test-sess-1")
    assert len(retrieved.cookies) == 1
    assert retrieved.cookies[0]["name"] == "daraz_token"

    # Clear session
    await manager.clear_session("test-sess-1")
    fresh = await manager.get_or_create_session("test-sess-1")
    assert len(fresh.cookies) == 0


@pytest.mark.asyncio
async def test_session_manager_disk_persistence(temp_session_dir):
    manager = SessionManager(storage_dir=temp_session_dir, default_ttl_seconds=3600)
    session = await manager.get_or_create_session("persist-sess")
    session.storage_state = {"cookies": [{"name": "auth", "value": "token_abc"}]}
    await manager.save_session(session)

    # Instantiate new manager pointing to same directory
    new_manager = SessionManager(storage_dir=temp_session_dir)
    loaded = await new_manager.get_or_create_session("persist-sess")

    assert loaded.session_id == "persist-sess"
    assert loaded.storage_state["cookies"][0]["value"] == "token_abc"


@pytest.mark.asyncio
async def test_session_manager_expiration():
    manager = SessionManager(default_ttl_seconds=0.05)
    session = await manager.get_or_create_session("expiring-sess")
    assert session.is_expired is False

    time.sleep(0.08)
    assert session.is_expired is True

    # Retrieving expired session returns a renewed session
    renewed = await manager.get_or_create_session("expiring-sess")
    assert renewed.is_expired is False
