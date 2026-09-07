import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple

from backend.app.models.domain import (
    DarazProviderHealth, MarketplaceProduct, ProductMarketSnapshot
)
from backend.app.repositories.base import MarketplaceProductRepository
from backend.app.services.daraz.base import DarazProvider, DarazFetchResult
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.services.daraz.parse_scraper_provider import DarazParseScraperProvider
from backend.app.services.daraz.fallback_provider import DarazDirectFallbackProvider
from backend.app.services.daraz.database_cache_provider import DarazDatabaseCacheProvider

logger = logging.getLogger(__name__)

class DarazFailoverPool:
    """
    Manages multi-provider prioritization and resilient failover for Daraz integrations:
      P1: Official Daraz Open Platform API
      P2: Parse Daraz Scraper API
      P3: Direct Fallback Scraper
      P4: Database Cache Fallback
    """
    def __init__(
        self,
        repository: Optional[MarketplaceProductRepository] = None,
        providers: Optional[List[DarazProvider]] = None
    ):
        self.repository = repository
        self.providers: List[DarazProvider] = providers or [
            DarazOfficialProvider(marketplace_repo=repository),  # Priority 1
            DarazParseScraperProvider(),                           # Priority 2
            DarazDirectFallbackProvider(),                         # Priority 3
            DarazDatabaseCacheProvider(repository=repository),   # Priority 4
        ]
        # Sort strictly by priority ascending
        self.providers.sort(key=lambda p: p.priority)

    def _calculate_backoff_seconds(self, consecutive_failures: int, is_rate_limited: bool = False) -> int:
        failures = max(1, consecutive_failures)
        if is_rate_limited:
            # 30s, 60s, 120s, 240s, 480s, max 900s
            base = 30 * (2 ** min(failures - 1, 5))
            return min(900, base)
        else:
            # 15s, 30s, 60s, 120s, 240s, max 600s
            base = 15 * (2 ** min(failures - 1, 5))
            return min(600, base)

    def _record_provider_success(self, provider: DarazProvider) -> Optional[DarazProviderHealth]:
        if not self.repository:
            return None
        now = datetime.now(timezone.utc)
        health = self.repository.get_provider_health(provider.name)
        if not health:
            health = DarazProviderHealth(
                id=f"prov_{provider.name}",
                provider_name=provider.name,
                priority=provider.priority,
                enabled=True,
                status="healthy",
                consecutive_failures=0,
                total_requests=1,
                successful_requests=1,
                failed_requests=0,
                rate_limited_requests=0,
                last_success_at=now,
                last_failure_at=None,
                cooldown_until=None,
                last_error_code=None,
                last_error_message=None,
                created_at=now,
                updated_at=now
            )
        else:
            health.status = "healthy"
            health.consecutive_failures = 0
            health.total_requests += 1
            health.successful_requests += 1
            health.last_success_at = now
            health.cooldown_until = None
            health.last_error_code = None
            health.last_error_message = None
            health.updated_at = now

        return self.repository.update_provider_health(health)

    def _record_provider_failure(
        self,
        provider: DarazProvider,
        error_code: Optional[int],
        error_message: Optional[str],
        is_rate_limited: bool = False
    ) -> Optional[DarazProviderHealth]:
        if not self.repository:
            return None
        now = datetime.now(timezone.utc)
        health = self.repository.get_provider_health(provider.name)
        if not health:
            health = DarazProviderHealth(
                id=f"prov_{provider.name}",
                provider_name=provider.name,
                priority=provider.priority,
                enabled=True,
                status="rate_limited" if is_rate_limited else "degraded",
                consecutive_failures=1,
                total_requests=1,
                successful_requests=0,
                failed_requests=1,
                rate_limited_requests=1 if is_rate_limited else 0,
                last_success_at=None,
                last_failure_at=now,
                cooldown_until=now + timedelta(seconds=self._calculate_backoff_seconds(1, is_rate_limited)),
                last_error_code=error_code,
                last_error_message=error_message,
                created_at=now,
                updated_at=now
            )
        else:
            health.total_requests += 1
            health.failed_requests += 1
            if is_rate_limited:
                health.rate_limited_requests += 1
                health.status = "rate_limited"
            else:
                health.status = "unhealthy" if health.consecutive_failures >= 3 else "degraded"

            health.consecutive_failures += 1
            health.last_failure_at = now
            health.last_error_code = error_code
            health.last_error_message = error_message
            health.updated_at = now

            cooldown_secs = self._calculate_backoff_seconds(health.consecutive_failures, is_rate_limited)
            health.cooldown_until = now + timedelta(seconds=cooldown_secs)

        return self.repository.update_provider_health(health)

    def is_provider_available(self, provider: DarazProvider) -> bool:
        if not self.repository:
            return True
        health = self.repository.get_provider_health(provider.name)
        if not health or not health.enabled:
            return True

        now = datetime.now(timezone.utc)
        if health.cooldown_until and now < health.cooldown_until:
            logger.debug(f"Provider {provider.name} in cooldown until {health.cooldown_until.isoformat()}")
            return False

        # Cooldown expired - restore to healthy
        if health.cooldown_until and now >= health.cooldown_until:
            health.cooldown_until = None
            if health.status in ("rate_limited", "unhealthy", "degraded"):
                health.status = "healthy"
            health.updated_at = now
            self.repository.update_provider_health(health)
            logger.info(f"Provider {provider.name} cooldown expired. Restored to healthy.")

        return True

    def execute_with_failover(self, operation_name: str, *args, **kwargs) -> DarazFetchResult:
        """
        Tries providers in strict priority order (P1 -> P2 -> P3 -> P4).
        Falls over on timeouts, 429 rate limits, 401 auth errors, or 5xx failures.
        """
        attempts: List[Dict[str, Any]] = []
        last_error_result: Optional[DarazFetchResult] = None

        for provider in self.providers:
            if not self.is_provider_available(provider):
                attempts.append({
                    "provider": provider.name,
                    "skipped": True,
                    "reason": "cooldown_active"
                })
                continue

            method = getattr(provider, operation_name, None)
            if not method or not callable(method):
                continue

            try:
                res: DarazFetchResult = method(*args, **kwargs)
                if res.success:
                    if not res.is_cached:
                        self._record_provider_success(provider)
                    logger.info(f"Daraz {operation_name} succeeded via {provider.name}")
                    return res
                else:
                    last_error_result = res
                    if not res.is_cached:
                        self._record_provider_failure(
                            provider=provider,
                            error_code=res.error_code,
                            error_message=res.error_message,
                            is_rate_limited=res.is_rate_limited
                        )
                    attempts.append({
                        "provider": provider.name,
                        "error_code": res.error_code,
                        "error_message": res.error_message
                    })
                    logger.warning(f"Daraz provider {provider.name} failed ({res.error_code}): {res.error_message}. Failing over...")

            except Exception as e:
                logger.error(f"Unexpected exception in provider {provider.name}: {e}")
                self._record_provider_failure(provider, 500, str(e), False)
                attempts.append({"provider": provider.name, "error": str(e)})

        if last_error_result:
            return last_error_result

        return DarazFetchResult(
            success=False,
            error_code=503,
            error_message="All Daraz providers in pool failed.",
            provider_name="none"
        )
