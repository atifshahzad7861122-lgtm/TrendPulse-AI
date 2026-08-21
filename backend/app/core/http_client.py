import time
import logging
from typing import Dict, Any, Optional
import httpx
from backend.app.core.config import settings

logger = logging.getLogger("trendpulse.http_client")

class RateLimitException(Exception):
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after

class QuotaExceededException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class AuthenticationException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class ResilientHTTPClient:
    """
    Production-grade HTTP client with configurable timeouts,
    exponential backoff retries on transient errors, 429 rate limit detection,
    and quota exceeded error parsing.
    """

    TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}

    def __init__(
        self,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None
    ):
        self.timeout = timeout or settings.DATA_SOURCE_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.DATA_SOURCE_MAX_RETRIES
        self.backoff_factor = backoff_factor or settings.DATA_SOURCE_RETRY_BACKOFF_FACTOR

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Executes a resilient GET request with retries.
        """
        attempt = 0
        last_exception = None

        while attempt <= self.max_retries:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params=params, headers=headers)
                    
                    # 1. Handle 401/403 Authentication or Quota Exceeded
                    if response.status_code in {401, 403}:
                        try:
                            err_data = response.json()
                            err_msg = err_data.get("error", {}).get("message", response.text)
                            reasons = [e.get("reason") for e in err_data.get("error", {}).get("errors", [])]
                            if "quotaExceeded" in reasons or "rateLimitExceeded" in reasons:
                                raise QuotaExceededException(f"YouTube API quota exceeded: {err_msg}")
                            if response.status_code == 401 or "keyInvalid" in reasons:
                                raise AuthenticationException(f"YouTube API authentication failed (invalid API key).")
                        except (ValueError, KeyError):
                            pass
                        if response.status_code == 401:
                            raise AuthenticationException("YouTube API authentication failed (HTTP 401).")
                        if response.status_code == 403:
                            raise QuotaExceededException(f"YouTube API access forbidden/quota exceeded (HTTP 403).")

                    # 2. Handle 429 Rate Limiting
                    if response.status_code == 429:
                        retry_after_hdr = response.headers.get("Retry-After")
                        retry_after = int(retry_after_hdr) if retry_after_hdr and retry_after_hdr.isdigit() else 5
                        if attempt < self.max_retries:
                            sleep_time = retry_after or (self.backoff_factor ** attempt)
                            logger.warning(f"Rate limited (429). Retrying after {sleep_time}s...")
                            time.sleep(sleep_time)
                            attempt += 1
                            continue
                        raise RateLimitException(f"Rate limit exceeded (429) for provider", retry_after=retry_after)

                    # 3. Handle 5xx Transient Server Errors
                    if response.status_code in self.TRANSIENT_STATUS_CODES:
                        if attempt < self.max_retries:
                            sleep_time = self.backoff_factor ** attempt
                            logger.warning(f"Transient error ({response.status_code}). Retrying in {sleep_time:.1f}s...")
                            time.sleep(sleep_time)
                            attempt += 1
                            continue
                        response.raise_for_status()

                    # 4. Handle other 4xx client errors
                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor ** attempt
                    logger.warning(f"Request timeout. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    attempt += 1
                    continue
                raise TimeoutError(f"HTTP request timed out after {self.timeout}s") from e

            except (RateLimitException, QuotaExceededException, AuthenticationException):
                raise

            except httpx.HTTPStatusError as e:
                if e.response.status_code in {400, 401, 403, 404}:
                    raise e
                last_exception = e
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor ** attempt
                    time.sleep(sleep_time)
                    attempt += 1
                    continue
                raise e

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor ** attempt
                    time.sleep(sleep_time)
                    attempt += 1
                    continue
                raise e

        if last_exception:
            raise last_exception
        raise RuntimeError("Failed to complete HTTP request after maximum retries")
