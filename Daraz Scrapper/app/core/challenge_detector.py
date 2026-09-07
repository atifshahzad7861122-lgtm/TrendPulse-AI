"""Centralized anti-bot challenge and security barrier detector."""

from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Set
from app.core.constants import CHALLENGE_KEYWORDS
from app.core.exceptions import ChallengeDetectedError
from app.core.logging import logger


@dataclass
class ChallengeResult:
    """Outcome of an anti-bot challenge inspection."""
    is_challenge: bool
    challenge_type: Optional[str] = None
    reason: Optional[str] = None
    status_code: Optional[int] = None
    url: Optional[str] = None


class ChallengeDetector:
    """Inspects HTTP responses and browser page contents to detect security challenges."""

    DARAZ_PUNISH_PATTERNS = [
        re.compile(r"/punish[/?]", re.IGNORECASE),
        re.compile(r"sec\.daraz\.", re.IGNORECASE),
        re.compile(r"shield\.daraz\.", re.IGNORECASE),
        re.compile(r"passport\.daraz\.", re.IGNORECASE),
    ]

    CLOUDFLARE_PATTERNS = [
        re.compile(r"cf-browser-verification", re.IGNORECASE),
        re.compile(r"cf-ray", re.IGNORECASE),
        re.compile(r"challenge-running", re.IGNORECASE),
        re.compile(r"cloudflare", re.IGNORECASE),
        re.compile(r"turnstile", re.IGNORECASE),
    ]

    AKAMAI_PATTERNS = [
        re.compile(r"akamai-bm", re.IGNORECASE),
        re.compile(r"akamaighost", re.IGNORECASE),
        re.compile(r"access denied", re.IGNORECASE),
        re.compile(r"reference #", re.IGNORECASE),
    ]

    CAPTCHA_PATTERNS = [
        re.compile(r"please slide to verify", re.IGNORECASE),
        re.compile(r"verify you are human", re.IGNORECASE),
        re.compile(r"security verification", re.IGNORECASE),
        re.compile(r"g-recaptcha", re.IGNORECASE),
        re.compile(r"hcaptcha", re.IGNORECASE),
        re.compile(r"datadome", re.IGNORECASE),
    ]

    @classmethod
    def inspect_response(
        self,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        url: Optional[str] = None,
    ) -> ChallengeResult:
        """Analyze HTTP status, headers, and body for challenge triggers."""
        headers = headers or {}
        body_text = body or ""
        lower_body = body_text.lower()
        url_str = url or ""

        # 1. URL-based punish redirect check
        for pattern in self.DARAZ_PUNISH_PATTERNS:
            if pattern.search(url_str):
                return ChallengeResult(
                    is_challenge=True,
                    challenge_type="DARAZ_PUNISH",
                    reason=f"Punish redirect URL detected: {url_str}",
                    status_code=status_code,
                    url=url_str,
                )

        # 2. HTTP Status Code Checks
        if status_code == 429:
            return ChallengeResult(
                is_challenge=True,
                challenge_type="RATE_LIMITED",
                reason="HTTP 429 Too Many Requests",
                status_code=status_code,
                url=url_str,
            )

        if status_code == 403:
            # Determine provider if possible
            if any(p.search(lower_body) for p in self.CLOUDFLARE_PATTERNS) or "cf-ray" in headers:
                ctype = "CLOUDFLARE_BLOCK"
            elif any(p.search(lower_body) for p in self.AKAMAI_PATTERNS) or "server" in headers and "akamai" in headers["server"].lower():
                ctype = "AKAMAI_BLOCK"
            else:
                ctype = "HTTP_403_FORBIDDEN"

            return ChallengeResult(
                is_challenge=True,
                challenge_type=ctype,
                reason=f"HTTP 403 Forbidden challenge: {ctype}",
                status_code=status_code,
                url=url_str,
            )

        # 3. Keyword & Content Inspection
        for pattern in self.CAPTCHA_PATTERNS:
            if pattern.search(lower_body):
                return ChallengeResult(
                    is_challenge=True,
                    challenge_type="CAPTCHA_CHALLENGE",
                    reason=f"CAPTCHA pattern detected in response body: {pattern.pattern}",
                    status_code=status_code,
                    url=url_str,
                )

        for pattern in self.CLOUDFLARE_PATTERNS:
            if pattern.search(lower_body):
                return ChallengeResult(
                    is_challenge=True,
                    challenge_type="CLOUDFLARE_CHALLENGE",
                    reason=f"Cloudflare challenge detected: {pattern.pattern}",
                    status_code=status_code,
                    url=url_str,
                )

        # 4. Empty / blocked HTML verification
        if status_code == 200 and len(lower_body.strip()) < 50 and "html" in headers.get("content-type", ""):
            return ChallengeResult(
                is_challenge=True,
                challenge_type="EMPTY_BLOCKED_RESPONSE",
                reason="Suspiciously empty HTML response received (under 50 bytes)",
                status_code=status_code,
                url=url_str,
            )

        return ChallengeResult(is_challenge=False, status_code=status_code, url=url_str)

    @classmethod
    def verify_or_raise(
        self,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        """Inspect response and raise ChallengeDetectedError if a challenge is found."""
        result = self.inspect_response(status_code=status_code, headers=headers, body=body, url=url)
        if result.is_challenge:
            logger.warning(
                f"Anti-Bot Challenge Detected! Type: {result.challenge_type} on {url}",
                extra={
                    "event": "anti_bot_challenge_detected",
                    "challenge_type": result.challenge_type,
                    "url": url,
                    "status": status_code,
                    "reason": result.reason,
                },
            )
            raise ChallengeDetectedError(
                message=f"Anti-bot challenge triggered: {result.reason}",
                url=url,
                challenge_type=result.challenge_type,
                status_code=status_code,
            )
