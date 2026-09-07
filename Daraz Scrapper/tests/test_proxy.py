"""Tests for ProxyProvider, ProxyConfig, rotation, health, and cooldown."""

import asyncio
import pytest
from app.core.proxy import ProxyConfig, ProxyHealth, ProxyProvider


@pytest.mark.asyncio
async def test_proxy_provider_disabled():
    provider = ProxyProvider(enabled=False)
    assert provider.has_proxies is False
    assert await provider.get_next_proxy() is None
    assert provider.get_httpx_proxy(None) is None
    assert provider.get_playwright_proxy(None) is None


@pytest.mark.asyncio
async def test_proxy_provider_rotation():
    p1 = ProxyConfig(url="http://proxy1.example.com:8080")
    p2 = ProxyConfig(url="http://proxy2.example.com:8080", username="user", password="pwd")
    provider = ProxyProvider(proxies=[p1, p2], enabled=True)

    assert provider.has_proxies is True

    chosen1 = await provider.get_next_proxy()
    chosen2 = await provider.get_next_proxy()
    chosen3 = await provider.get_next_proxy()

    assert chosen1.url == "http://proxy1.example.com:8080"
    assert chosen2.url == "http://proxy2.example.com:8080"
    assert chosen3.url == "http://proxy1.example.com:8080"

    # Test formatted URL and formats
    assert p2.formatted_url == "http://user:pwd@proxy2.example.com:8080"
    httpx_proxy = provider.get_httpx_proxy(p2)
    assert httpx_proxy == "http://user:pwd@proxy2.example.com:8080"

    pw_proxy = provider.get_playwright_proxy(p2)
    assert pw_proxy["server"] == "http://proxy2.example.com:8080"
    assert pw_proxy["username"] == "user"
    assert pw_proxy["password"] == "pwd"


@pytest.mark.asyncio
async def test_proxy_failure_and_cooldown():
    p1 = ProxyConfig(url="http://proxy1.example.com:8080", max_failures=2, cooldown_seconds=0.1)
    provider = ProxyProvider(proxies=[p1], enabled=True)

    # First failure
    await provider.record_failure(p1.url, RuntimeError("Conn refused"))
    assert provider._health[p1.url].is_healthy is True

    # Second failure -> triggers cooldown
    await provider.record_failure(p1.url, RuntimeError("Conn refused"))
    assert provider._health[p1.url].is_healthy is False

    # No healthy proxies available during cooldown
    assert await provider.get_next_proxy() is None

    # Wait for cooldown to expire
    await asyncio.sleep(0.15)
    reinstated = await provider.get_next_proxy()
    assert reinstated is not None
    assert reinstated.url == p1.url
    assert provider._health[p1.url].is_healthy is True
