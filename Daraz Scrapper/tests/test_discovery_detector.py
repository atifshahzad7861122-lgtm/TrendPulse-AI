"""Tests for anti-bot, CAPTCHA, and blocked page detection."""

from pathlib import Path
from app.discovery.detector import ChallengeDetector

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "daraz"


def test_detect_clean_page():
    detector = ChallengeDetector()
    html = "<html><body><h1>Welcome to Daraz</h1><p>Items listed here</p></body></html>"
    res = detector.detect(status_code=200, html_content=html, current_url="https://www.daraz.pk")

    assert res.is_challenge is False
    assert res.is_captcha is False
    assert res.is_blocked is False


def test_detect_captcha_page():
    detector = ChallengeDetector()
    html = (FIXTURES_DIR / "captcha_challenge.html").read_text(encoding="utf-8")
    res = detector.detect(status_code=200, html_content=html, current_url="https://www.daraz.pk/punish?...")

    assert res.is_challenge is True
    assert res.is_captcha is True
    assert "captcha" in res.reason.lower() or "punish" in res.reason.lower()


def test_detect_403_blocked_page():
    detector = ChallengeDetector()
    html = (FIXTURES_DIR / "blocked_page.html").read_text(encoding="utf-8")
    res = detector.detect(status_code=403, html_content=html, current_url="https://www.daraz.pk/category")

    assert res.is_challenge is True
    assert res.is_blocked is True
    assert "403" in res.reason


def test_detect_429_rate_limit():
    detector = ChallengeDetector()
    res = detector.detect(status_code=429, html_content="", current_url="https://www.daraz.pk")

    assert res.is_challenge is True
    assert res.is_rate_limited is True
