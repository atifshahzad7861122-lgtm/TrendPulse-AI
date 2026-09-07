"""Smart retry policy with exponential backoff and jitter for transient crawl errors."""

from datetime import datetime, timedelta, timezone
import random
from typing import Optional, Tuple

from app.orchestration.models import CrawlTask


class SmartRetryPolicy:
    """
    Intelligent retry engine determining retry eligibility and backoff schedule.
    Prevents retry storms while ensuring transient errors recover automatically.
    """

    TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}
    NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 405, 410, 422}

    def __init__(self, base_backoff_sec: float = 1.5, max_backoff_sec: float = 30.0, max_retries: int = 3):
        self.base_backoff_sec = base_backoff_sec
        self.max_backoff_sec = max_backoff_sec
        self.max_retries = max_retries

    def should_retry(self, task: CrawlTask, status_code: int, error_message: str) -> Tuple[bool, Optional[datetime], Optional[str]]:
        """
        Evaluate if a failed task qualifies for retry.
        Returns (should_retry, next_retry_timestamp, reason).
        """
        if task.attempt_count >= task.max_retries:
            return False, None, f"Exceeded maximum retries ({task.max_retries})"

        err_lower = error_message.lower() if error_message else ""

        # 1. Permanent Non-Retryable Check
        if status_code in self.NON_RETRYABLE_STATUS_CODES:
            return False, None, f"Non-retryable HTTP status {status_code}"

        if any(term in err_lower for term in ["not found", "invalid url", "validation error", "mandatory product title missing"]):
            return False, None, f"Permanent validation or target failure: {error_message}"

        # 2. Transient Check
        is_transient = (
            status_code in self.TRANSIENT_STATUS_CODES
            or status_code == 0
            or any(t in err_lower for t in ["timeout", "connection reset", "temporarily unavailable", "network error", "rate limit"])
        )

        if not is_transient and status_code == 200:
            # General unexpected extraction error on 200 response -> allow 1 retry in case of partial render
            if task.attempt_count < 2:
                is_transient = True

        if is_transient:
            # Exponential backoff with jitter
            exponent = min(task.attempt_count, 6)
            raw_backoff = min(self.max_backoff_sec, self.base_backoff_sec * (2 ** exponent))
            # Jitter: 50% to 100% of calculated backoff
            jittered_sec = raw_backoff * (0.5 + 0.5 * random.random())
            next_retry = datetime.now(timezone.utc) + timedelta(seconds=jittered_sec)
            return True, next_retry, f"Transient failure ({error_message}); retrying in {jittered_sec:.1f}s"

        return False, None, f"Unclassified error not eligible for retry: {error_message}"
