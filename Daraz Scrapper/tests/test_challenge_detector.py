"""Tests for ChallengeDetector and security barrier classifications."""

import pytest
from app.core.challenge_detector import ChallengeDetector
from app.core.exceptions import ChallengeDetectedError


def test_challenge_detector_clean_response():
    result = ChallengeDetector.inspect_response(
        status_code=200,
        headers={"content-type": "text/html"},
        body="<html><body><div id='root'><h1>Product Name</h1><p>Genuine store data</p></div></body></html>",
        url="https://www.daraz.pk/products/test-i123.html",
    )
    assert result.is_challenge is False
    assert result.challenge_type is None


def test_challenge_detector_http_429():
    result = ChallengeDetector.inspect_response(
        status_code=429,
        headers={"retry-after": "10"},
        body="Too Many Requests",
        url="https://www.daraz.pk/catalog/",
    )
    assert result.is_challenge is True
    assert result.challenge_type == "RATE_LIMITED"


def test_challenge_detector_cloudflare_challenge():
    result = ChallengeDetector.inspect_response(
        status_code=403,
        headers={"cf-ray": "84849202a0"},
        body="<html><title>Attention Required! | Cloudflare</title><body>cf-browser-verification</body></html>",
        url="https://www.daraz.pk/products/item.html",
    )
    assert result.is_challenge is True
    assert result.challenge_type == "CLOUDFLARE_BLOCK"

    with pytest.raises(ChallengeDetectedError) as exc_info:
        ChallengeDetector.verify_or_raise(
            status_code=403,
            headers={"cf-ray": "84849202a0"},
            body="<html><title>Attention Required! | Cloudflare</title><body>cf-browser-verification</body></html>",
            url="https://www.daraz.pk/products/item.html",
        )
    assert exc_info.value.challenge_type == "CLOUDFLARE_BLOCK"


def test_challenge_detector_daraz_punish_url():
    result = ChallengeDetector.inspect_response(
        status_code=302,
        headers={"location": "https://sec.daraz.pk/punish?x=1"},
        body="",
        url="https://sec.daraz.pk/punish?from=risk",
    )
    assert result.is_challenge is True
    assert result.challenge_type == "DARAZ_PUNISH"


def test_challenge_detector_captcha_keyword():
    result = ChallengeDetector.inspect_response(
        status_code=200,
        headers={"content-type": "text/html"},
        body="<html><body>Please slide to verify you are human before proceeding</body></html>",
        url="https://www.daraz.pk/products/item.html",
    )
    assert result.is_challenge is True
    assert result.challenge_type == "CAPTCHA_CHALLENGE"


def test_challenge_detector_empty_blocked_response():
    result = ChallengeDetector.inspect_response(
        status_code=200,
        headers={"content-type": "text/html"},
        body="<html></html>",
        url="https://www.daraz.pk/products/item.html",
    )
    assert result.is_challenge is True
    assert result.challenge_type == "EMPTY_BLOCKED_RESPONSE"
