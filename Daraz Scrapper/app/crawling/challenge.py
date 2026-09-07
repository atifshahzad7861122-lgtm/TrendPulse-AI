"""Universal multi-tier challenge and anti-bot detector across marketplaces."""

import re
from typing import Optional, Tuple
from pydantic import BaseModel

from app.core.logging import logger


class ChallengeDetectionResult(BaseModel):
    """Detection output assessing bot walls and challenge screens."""
    is_challenge: bool
    is_blocked: bool
    status_code: int
    reason: Optional[str] = None
    waf_provider: Optional[str] = None  # e.g. 'Cloudflare', 'Akamai', 'PerimeterX', 'DataDome'


class UniversalChallengeDetector:
    """
    Multi-tier anti-bot detection heuristics for marketplace crawl results.
    Adapted from Crawl4AI antibot_detector and ecommerce defense signatures.
    """

    # Tier 1: High-confidence structural markers (single signal sufficient)
    TIER1_PATTERNS = [
        # Akamai
        (re.compile(r"Reference\s*#\s*[\d]+\.[0-9a-f]+\.\d+\.[0-9a-f]+", re.IGNORECASE), "Akamai block (Reference #)", "Akamai"),
        (re.compile(r"Pardon\s+Our\s+Interruption", re.IGNORECASE), "Akamai challenge (Pardon Our Interruption)", "Akamai"),
        # Cloudflare
        (re.compile(r"challenge-form.*?__cf_chl_f_tk=", re.IGNORECASE | re.DOTALL), "Cloudflare challenge form", "Cloudflare"),
        (re.compile(r'<span\s+class="cf-error-code">\d{4}</span>', re.IGNORECASE), "Cloudflare firewall block", "Cloudflare"),
        (re.compile(r"/cdn-cgi/challenge-platform/\S+orchestrate", re.IGNORECASE), "Cloudflare JS challenge", "Cloudflare"),
        (re.compile(r"ray\s*id:?\s*[0-9a-f]{16}", re.IGNORECASE), "Cloudflare ray challenge", "Cloudflare"),
        # PerimeterX / HUMAN
        (re.compile(r"window\._pxAppId\s*=", re.IGNORECASE), "PerimeterX block", "PerimeterX"),
        (re.compile(r"captcha\.px-cdn\.net", re.IGNORECASE), "PerimeterX captcha", "PerimeterX"),
        # DataDome
        (re.compile(r"captcha-delivery\.com", re.IGNORECASE), "DataDome captcha", "DataDome"),
        # Amazon Robot Check
        (re.compile(r"images-amazon\.com/captcha/", re.IGNORECASE), "Amazon CAPTCHA check", "Amazon"),
        (re.compile(r"<title>\s*Robot\s+Check\s*</title>", re.IGNORECASE), "Amazon Robot Check title", "Amazon"),
        (re.compile(r"/errors/validateCaptcha", re.IGNORECASE), "Amazon validateCaptcha form", "Amazon"),
        (re.compile(r"Type\s+the\s+characters\s+you\s+see\s+in\s+this\s+image", re.IGNORECASE), "Amazon CAPTCHA image prompt", "Amazon"),
        (re.compile(r"Sorry,\s+we\s+just\s+need\s+to\s+make\s+sure\s+you're\s+not\s+a\s+robot", re.IGNORECASE), "Amazon Bot Detection Page", "Amazon"),
        # Daraz / Alibaba slide verification
        (re.compile(r"nc_1_n1z", re.IGNORECASE), "Alibaba / Daraz slider challenge", "Alibaba"),
        (re.compile(r"baxia-dialog", re.IGNORECASE), "Daraz Baxia Security Challenge", "Alibaba"),
        (re.compile(r"punish\?punishType", re.IGNORECASE), "Alibaba / Daraz punish redirect", "Alibaba"),
        (re.compile(r"sec-cpt", re.IGNORECASE), "Alibaba Security Captcha", "Alibaba"),
    ]

    # Tier 2: Medium-confidence patterns on small pages (< 15KB) or status >= 400
    TIER2_PATTERNS = [
        (re.compile(r"Access\s+Denied", re.IGNORECASE), "Access Denied", "Generic"),
        (re.compile(r"Checking\s+your\s+browser", re.IGNORECASE), "Cloudflare browser check", "Cloudflare"),
        (re.compile(r"Just\s+a\s+moment\.\.\.", re.IGNORECASE), "Cloudflare 'Just a moment'", "Cloudflare"),
        (re.compile(r"Security\s+Verification", re.IGNORECASE), "Security verification screen", "Generic"),
        (re.compile(r"Please\s+verify\s+you\s+are\s+a\s+human", re.IGNORECASE), "Human verification check", "Generic"),
        (re.compile(r"Robot\s+Check", re.IGNORECASE), "Robot Check", "Generic"),
    ]

    def detect(self, status_code: int, html_content: str, current_url: str = "") -> ChallengeDetectionResult:
        """
        Evaluate HTTP response against multi-tier detection signatures.
        """
        # 1. HTTP Status 403 or 429
        if status_code in (403, 429):
            reason = f"Blocked with HTTP status {status_code}"
            return ChallengeDetectionResult(
                is_challenge=True,
                is_blocked=True,
                status_code=status_code,
                reason=reason,
                waf_provider="HTTP Status",
            )

        content = html_content or ""
        content_len = len(content)

        # 2. Check Tier 1 Structural Markers (applies regardless of page size)
        for pattern, reason, provider in self.TIER1_PATTERNS:
            if pattern.search(content):
                return ChallengeDetectionResult(
                    is_challenge=True,
                    is_blocked=True,
                    status_code=status_code,
                    reason=reason,
                    waf_provider=provider,
                )

        # 3. Check Tier 2 Medium-Confidence Patterns (on pages < 15KB or error status)
        if content_len < 15000 or status_code >= 400:
            for pattern, reason, provider in self.TIER2_PATTERNS:
                if pattern.search(content):
                    return ChallengeDetectionResult(
                        is_challenge=True,
                        is_blocked=True,
                        status_code=status_code,
                        reason=reason,
                        waf_provider=provider,
                    )

        # 4. Check URL Redirects indicating challenge / block
        lower_url = current_url.lower()
        if any(w in lower_url for w in ["validateCaptcha", "punish", "waf_challenge", "blocked", "captcha"]):
            return ChallengeDetectionResult(
                is_challenge=True,
                is_blocked=True,
                status_code=status_code,
                reason=f"Challenge detected in URL path: {current_url}",
                waf_provider="URL Signatures",
            )

        return ChallengeDetectionResult(
            is_challenge=False,
            is_blocked=False,
            status_code=status_code,
        )
