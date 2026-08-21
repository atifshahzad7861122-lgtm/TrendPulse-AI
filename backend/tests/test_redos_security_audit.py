import os
os.environ["DATA_BACKEND"] = "in_memory"

import time
import re
import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import settings
settings.DATA_BACKEND = "in_memory"

from backend.app.main import app
from backend.app.domain.data_quality import SPAM_PATTERNS
from backend.app.domain.matching import ProductMatchingEngine
from backend.app.domain.classification import CategoryClassificationService

client = TestClient(app)

# Safe execution threshold per regex evaluation: 50 milliseconds
MAX_EXECUTION_TIME_SECONDS = 0.05

def test_data_quality_spam_patterns_redos_resilience():
    """
    Test SPAM_PATTERNS against adversarial bounded strings of increasing lengths
    (100, 500, 1000, 2000, 5000 chars) with repeated whitespace and partial prefix matches.
    """
    lengths = [100, 500, 1000, 2000, 5000]
    
    for pattern in SPAM_PATTERNS:
        compiled = re.compile(pattern)
        for length in lengths:
            # 1. Adversarial string: repeated spaces and trailing non-match
            payload_spaces = "free" + (" " * length) + "not_money"
            start = time.perf_counter()
            compiled.search(payload_spaces)
            elapsed = time.perf_counter() - start
            assert elapsed < MAX_EXECUTION_TIME_SECONDS, f"Pattern {pattern} took {elapsed:.4f}s on {length} chars (spaces)"

            # 2. Adversarial string: repeated prefix
            payload_repetition = ("telegram" * (length // 8)) + ":no_at"
            start = time.perf_counter()
            compiled.search(payload_repetition)
            elapsed = time.perf_counter() - start
            assert elapsed < MAX_EXECUTION_TIME_SECONDS, f"Pattern {pattern} took {elapsed:.4f}s on {length} chars (repetition)"

            # 3. Adversarial string: alternating matching characters
            payload_alternating = ("a " * (length // 2)) + "!"
            start = time.perf_counter()
            compiled.search(payload_alternating)
            elapsed = time.perf_counter() - start
            assert elapsed < MAX_EXECUTION_TIME_SECONDS, f"Pattern {pattern} took {elapsed:.4f}s on {length} chars (alternating)"

def test_matching_and_classification_regex_resilience():
    r"""
    Test character class sanitizer r'[^\w\s]' on long adversarial strings.
    """
    clean_regex = re.compile(r'[^\w\s]')
    lengths = [100, 500, 1000, 2000, 5000]

    for length in lengths:
        # Adversarial special characters
        adversarial_special = ("!@#$%^&*()_+{}:\"<>?[];',./" * (length // 26 + 1))[:length]
        start = time.perf_counter()
        clean_regex.sub(' ', adversarial_special.lower())
        elapsed = time.perf_counter() - start
        assert elapsed < MAX_EXECUTION_TIME_SECONDS, f"Sanitization regex took {elapsed:.4f}s on {length} chars"

def test_api_search_adversarial_redos_resilience():
    """
    Send adversarial and long search queries to the search API to verify no ReDoS or performance freeze.
    """
    adversarial_queries = [
        "a" * 500,
        "a" * 2000,
        ("a+ " * 200) + "b",
        (".*" * 100) + "x",
        ("(([a-z])+)+" * 50),
        ("(?=.*[a-z])" * 100)
    ]

    for query in adversarial_queries:
        start = time.perf_counter()
        res = client.get("/api/v1/search", params={"q": query})
        elapsed = time.perf_counter() - start
        # Either 200 (if <= 200 chars) or 422 (if > 200 chars due to max_length constraint)
        assert res.status_code in [200, 422]
        assert elapsed < 0.2, f"Search API took {elapsed:.4f}s on adversarial query"

def test_api_auth_adversarial_email_resilience():
    """
    Verify that adversarial email strings do not cause exponential backtracking in validation.
    """
    adversarial_emails = [
        ("a" * 60) + "@" + ("b" * 60) + ".com",
        ("a." * 50) + "b@example.com",
        "invalid_email_" + ("!" * 200) + "@example.com",
        ("a" * 200) + "@" + ("b." * 30) + "com"
    ]

    for email in adversarial_emails:
        start = time.perf_counter()
        res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        elapsed = time.perf_counter() - start
        # Either 422 (invalid email format) or 401 (not found)
        assert res.status_code in [401, 422]
        assert elapsed < 0.1, f"Auth validation took {elapsed:.4f}s on email {email[:30]}..."
