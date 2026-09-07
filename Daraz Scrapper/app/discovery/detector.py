"""Anti-bot, CAPTCHA, and blocked response detection for Daraz marketplace discovery crawls."""

from dataclasses import dataclass
from typing import Optional
from app.core.constants import CHALLENGE_KEYWORDS, CHALLENGE_STATUS_CODES
from app.discovery.config import DarazDiscoveryConfig, default_discovery_config


@dataclass
class ChallengeDetectionResult:
    """Outcome of response analysis for security challenges and access blocks."""

    is_challenge: bool = False
    is_captcha: bool = False
    is_blocked: bool = False
    is_rate_limited: bool = False
    reason: Optional[str] = None
    trigger_text: Optional[str] = None


class ChallengeDetector:
    """Inspects response status, headers, URLs, and HTML bodies for anti-bot barriers."""

    def __init__(self, config: Optional[DarazDiscoveryConfig] = None):
        self.config = config or default_discovery_config

    def detect(
        self,
        status_code: int,
        html_content: str,
        current_url: str = "",
    ) -> ChallengeDetectionResult:
        """Evaluate whether a fetched page contains a human verification challenge or block."""
        url_lower = current_url.lower() if current_url else ""
        html_lower = html_content.lower() if html_content else ""

        # 1. Check HTTP Rate Limit (429)
        if status_code == 429:
            return ChallengeDetectionResult(
                is_challenge=True,
                is_rate_limited=True,
                reason="HTTP 429 Too Many Requests",
            )

        # 2. Check HTTP Block (403, 503 challenge)
        if status_code in (403, 503) and ("cloudflare" in html_lower or status_code == 403):
            return ChallengeDetectionResult(
                is_challenge=True,
                is_blocked=True,
                reason=f"HTTP {status_code} Forbidden/Blocked Access",
            )

        # 3. Check Punish / CAPTCHA URL redirect
        for indicator in self.config.CAPTCHA_INDICATORS:
            if indicator in url_lower:
                return ChallengeDetectionResult(
                    is_challenge=True,
                    is_captcha=True,
                    reason=f"CAPTCHA / Punish redirect URL matched: {indicator}",
                    trigger_text=indicator,
                )

        # 4. Check CAPTCHA / Human Verification signatures in HTML body
        indicators = list(self.config.CAPTCHA_INDICATORS) + [k for k in CHALLENGE_KEYWORDS if k not in self.config.CAPTCHA_INDICATORS]
        for indicator in indicators:
            if indicator in html_lower:
                return ChallengeDetectionResult(
                    is_challenge=True,
                    is_captcha=True,
                    reason=f"CAPTCHA challenge keyword detected in HTML: '{indicator}'",
                    trigger_text=indicator,
                )

        # 5. Check Blocked signatures in HTML body
        for indicator in self.config.BLOCKED_INDICATORS:
            if indicator in html_lower:
                return ChallengeDetectionResult(
                    is_challenge=True,
                    is_blocked=True,
                    reason=f"Access blocked keyword detected in HTML: '{indicator}'",
                    trigger_text=indicator,
                )

        # 6. Check empty body on 200 OK (often a silent bot drop)
        if status_code == 200 and len(html_content.strip()) == 0:
            return ChallengeDetectionResult(
                is_challenge=True,
                is_blocked=True,
                reason="Empty HTTP 200 response body (suspicious bot drop)",
            )

        return ChallengeDetectionResult()


# Default singleton instance
challenge_detector = ChallengeDetector()
