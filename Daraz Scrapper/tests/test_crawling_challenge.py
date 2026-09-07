"""Unit tests for multi-tier anti-bot and challenge detection across marketplaces."""

import pytest
from app.crawling.challenge import UniversalChallengeDetector


def test_detect_clean_page():
    detector = UniversalChallengeDetector()
    html = "<html><body><h1 id='productTitle'>Great Product</h1></body></html>"
    res = detector.detect(200, html, "https://www.amazon.com/dp/B08N5WRWNW")
    assert res.is_challenge is False
    assert res.is_blocked is False


def test_detect_cloudflare_and_akamai_tier1():
    detector = UniversalChallengeDetector()

    # Cloudflare challenge
    cf_html = "<html><form id='challenge-form' action='?__cf_chl_f_tk=123'></form></html>"
    res_cf = detector.detect(200, cf_html)
    assert res_cf.is_challenge is True
    assert res_cf.waf_provider == "Cloudflare"

    # Akamai block
    ak_html = "<html><body>Reference #18.2d351ab8.1557333295.a4e16ab</body></html>"
    res_ak = detector.detect(200, ak_html)
    assert res_ak.is_challenge is True
    assert res_ak.waf_provider == "Akamai"


def test_detect_amazon_and_daraz_challenges():
    detector = UniversalChallengeDetector()

    # Amazon Robot Check
    amz_html = "<html><body>Type the characters you see in this image to continue</body></html>"
    res_amz = detector.detect(200, amz_html)
    assert res_amz.is_challenge is True
    assert res_amz.waf_provider == "Amazon"

    # Daraz / Alibaba slider
    daraz_html = "<html><div class='nc_1_n1z'>Please slide to verify</div></html>"
    res_daraz = detector.detect(200, daraz_html)
    assert res_daraz.is_challenge is True
    assert res_daraz.waf_provider == "Alibaba"


def test_detect_http_403_and_429():
    detector = UniversalChallengeDetector()
    res_403 = detector.detect(403, "Access Denied")
    assert res_403.is_challenge is True
    assert res_403.status_code == 403

    res_429 = detector.detect(429, "Too Many Requests")
    assert res_429.is_challenge is True
    assert res_429.status_code == 429
