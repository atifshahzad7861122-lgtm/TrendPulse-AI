import time
import uuid
import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from backend.app.models.domain import (
    ShopifyProduct, ShopifyProductSnapshot, ShopifyProviderHealth, ShopifySyncRun
)
from backend.app.repositories.base import ShopifyRepository
from backend.app.services.shopify.base import ShopifyProvider, ShopifyFetchResult
from backend.app.services.shopify.providers import (
    ShopifyScoutProvider,
    ShopScraperProvider,
    ShopifyAppsSpyProvider,
    XtractoShopifyProvider,
    BornooShopifyProvider,
)
from backend.app.services.shopify.providers.scout_provider import clean_domain

class ShopifyFailoverPool:
    def __init__(
        self,
        repository: ShopifyRepository,
        providers: Optional[List[ShopifyProvider]] = None
    ):
        self.repository = repository
        self.providers: List[ShopifyProvider] = providers or [
            ShopifyScoutProvider(),      # Priority 1
            ShopScraperProvider(),       # Priority 2
            ShopifyAppsSpyProvider(),    # Priority 3
            XtractoShopifyProvider(),    # Priority 4
            BornooShopifyProvider(),     # Priority 5
        ]
        # Sort providers strictly by priority ascending (1 is highest)
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

    def _record_provider_success(self, provider: ShopifyProvider) -> ShopifyProviderHealth:
        now = datetime.now(timezone.utc)
        health = self.repository.get_provider_health(provider.name)
        if not health:
            health = ShopifyProviderHealth(
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
        provider: ShopifyProvider,
        error_code: Optional[int],
        error_message: Optional[str],
        is_rate_limited: bool = False
    ) -> ShopifyProviderHealth:
        now = datetime.now(timezone.utc)
        health = self.repository.get_provider_health(provider.name)
        if not health:
            health = ShopifyProviderHealth(
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
            health.consecutive_failures += 1
            health.last_failure_at = now
            health.last_error_code = error_code
            health.last_error_message = error_message
            if is_rate_limited:
                health.rate_limited_requests += 1
                health.status = "rate_limited"
            else:
                health.status = "degraded" if health.consecutive_failures < 3 else "unhealthy"

            backoff_sec = self._calculate_backoff_seconds(health.consecutive_failures, is_rate_limited)
            health.cooldown_until = now + timedelta(seconds=backoff_sec)
            health.updated_at = now

        return self.repository.update_provider_health(health)

    def execute_sync(
        self,
        store_domain: str,
        limit: int = 50,
        page: int = 1,
        collection: Optional[str] = None,
        force_live: bool = False
    ) -> Tuple[List[ShopifyProduct], str, bool, str, List[Dict[str, Any]], ShopifySyncRun]:
        """
        Ordered failover synchronization algorithm.
        Returns:
            (products, source_provider, is_live, status, provider_attempts, sync_run)
        """
        domain = clean_domain(store_domain)
        started_at = datetime.now(timezone.utc)
        attempts: List[Dict[str, Any]] = []
        winning_provider: Optional[ShopifyProvider] = None
        fetch_result: Optional[ShopifyFetchResult] = None

        now = datetime.now(timezone.utc)

        # 1. Iterate through providers in strict priority order
        for provider in self.providers:
            health = self.repository.get_provider_health(provider.name)
            if health and not health.enabled:
                attempts.append({
                    "provider_name": provider.name,
                    "priority": provider.priority,
                    "status": "disabled",
                    "error_message": "Provider is disabled"
                })
                continue

            # Check cooldown expiration
            if health and health.cooldown_until and health.cooldown_until > now and not force_live:
                rem_sec = int((health.cooldown_until - now).total_seconds())
                attempts.append({
                    "provider_name": provider.name,
                    "priority": provider.priority,
                    "status": "skipped_cooldown",
                    "error_message": f"In active cooldown ({rem_sec}s remaining)",
                    "cooldown_remaining_seconds": rem_sec
                })
                continue

            # Attempt fetch with this provider
            t0 = time.time()
            try:
                res = provider.fetch_products(
                    store_domain=domain,
                    limit=limit,
                    page=page,
                    collection=collection
                )
                duration_ms = round((time.time() - t0) * 1000, 2)
            except Exception as e:
                duration_ms = round((time.time() - t0) * 1000, 2)
                res = ShopifyFetchResult(
                    success=False,
                    error_code=500,
                    error_message=f"Exception during fetch: {str(e)}"
                )

            if res.success:
                # SUCCESS: Record health, stop chain immediately
                self._record_provider_success(provider)
                attempts.append({
                    "provider_name": provider.name,
                    "priority": provider.priority,
                    "status": "success",
                    "products_count": len(res.products),
                    "duration_ms": duration_ms
                })
                winning_provider = provider
                fetch_result = res
                break
            else:
                # FAILURE: Record health and cooldown, continue to next provider
                self._record_provider_failure(
                    provider=provider,
                    error_code=res.error_code,
                    error_message=res.error_message,
                    is_rate_limited=res.is_rate_limited
                )
                attempts.append({
                    "provider_name": provider.name,
                    "priority": provider.priority,
                    "status": "rate_limited" if res.is_rate_limited else "failed",
                    "error_code": res.error_code,
                    "error_message": res.error_message,
                    "duration_ms": duration_ms
                })

        completed_at = datetime.now(timezone.utc)

        # 2. Process outcome
        if winning_provider and fetch_result and fetch_result.success:
            # Upsert products and create snapshots
            products = fetch_result.products
            inserted_count = 0
            updated_count = 0
            snapshots: List[ShopifyProductSnapshot] = []

            for p in products:
                existing = self.repository.get_product(p.store_domain, p.product_id)
                if existing:
                    updated_count += 1
                else:
                    inserted_count += 1

                snap = ShopifyProductSnapshot(
                    id=f"sps_{uuid.uuid4().hex[:16]}",
                    shopify_product_id=p.id,
                    store_domain=p.store_domain,
                    product_id=p.product_id,
                    price=p.price,
                    compare_at_price=p.compare_at_price,
                    available=p.available,
                    rating=p.rating,
                    review_count=p.review_count,
                    inventory_status="in_stock" if p.available else "out_of_stock",
                    source_provider=winning_provider.name,
                    observed_at=completed_at,
                    raw_data=p.raw_data or {},
                    created_at=completed_at
                )
                snapshots.append(snap)

            persisted_products = self.repository.batch_upsert_products(products)
            if snapshots:
                self.repository.batch_create_snapshots(snapshots)

            # Auto-ingest into Unified Product Intelligence
            try:
                from backend.app.api.deps import get_unified_repository
                from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
                u_repo = get_unified_repository()
                u_service = UnifiedProductIntelligenceService(unified_repo=u_repo)
                for p in persisted_products:
                    u_service.ingest_shopify_product(p)
            except Exception as e:
                logger.debug(f"Unified intelligence auto-ingestion hook (Shopify): {e}")

            sync_run = ShopifySyncRun(
                id=f"ssr_{uuid.uuid4().hex[:16]}",
                store_domain=domain,
                provider_name=winning_provider.name,
                status="success",
                products_fetched=len(products),
                products_inserted=inserted_count,
                products_updated=updated_count,
                snapshots_created=len(snapshots),
                provider_attempts=attempts,
                error_code=None,
                error_message=None,
                started_at=started_at,
                completed_at=completed_at,
                created_at=completed_at
            )
            self.repository.record_sync_run(sync_run)

            return persisted_products, winning_provider.name, True, "success", attempts, sync_run

        else:
            # ALL PROVIDERS FAILED -> Query Persistent Database Cache Fallback
            cached_products = self.repository.list_products(store_domain=domain, limit=limit)
            last_err = attempts[-1].get("error_message") if attempts else "All providers unavailable"
            last_code = attempts[-1].get("error_code") if attempts else 503

            if cached_products:
                sync_run = ShopifySyncRun(
                    id=f"ssr_{uuid.uuid4().hex[:16]}",
                    store_domain=domain,
                    provider_name="database_cache",
                    status="cached",
                    products_fetched=0,
                    products_inserted=0,
                    products_updated=0,
                    snapshots_created=0,
                    provider_attempts=attempts,
                    error_code=last_code,
                    error_message=f"Failover exhausted. Cached fallback returned. {last_err}",
                    started_at=started_at,
                    completed_at=completed_at,
                    created_at=completed_at
                )
                self.repository.record_sync_run(sync_run)
                return cached_products, "database_cache", False, "cached", attempts, sync_run
            else:
                sync_run = ShopifySyncRun(
                    id=f"ssr_{uuid.uuid4().hex[:16]}",
                    store_domain=domain,
                    provider_name="none",
                    status="unavailable",
                    products_fetched=0,
                    products_inserted=0,
                    products_updated=0,
                    snapshots_created=0,
                    provider_attempts=attempts,
                    error_code=last_code,
                    error_message=f"All providers failed and no cache available. {last_err}",
                    started_at=started_at,
                    completed_at=completed_at,
                    created_at=completed_at
                )
                self.repository.record_sync_run(sync_run)
                return [], "none", False, "unavailable", attempts, sync_run

    def get_pool_status(self) -> Dict[str, Any]:
        """Return comprehensive health status of the failover pool."""
        health_records = self.repository.list_provider_health()
        now = datetime.now(timezone.utc)
        items = []
        active_count = 0
        preferred = "None"

        for h in health_records:
            is_in_cd = bool(h.cooldown_until and h.cooldown_until > now)
            cd_rem = int((h.cooldown_until - now).total_seconds()) if is_in_cd else 0
            if h.enabled and not is_in_cd and preferred == "None":
                preferred = h.provider_name
            if h.enabled and not is_in_cd:
                active_count += 1

            total = h.total_requests
            succ = h.successful_requests
            rate = round((succ / total * 100.0), 1) if total > 0 else 100.0

            # Find display name from provider list
            dname = h.provider_name
            for p in self.providers:
                if p.name == h.provider_name:
                    dname = p.display_name
                    break

            items.append({
                "provider_name": h.provider_name,
                "display_name": dname,
                "priority": h.priority,
                "enabled": h.enabled,
                "status": h.status,
                "consecutive_failures": h.consecutive_failures,
                "total_requests": h.total_requests,
                "successful_requests": h.successful_requests,
                "failed_requests": h.failed_requests,
                "rate_limited_requests": h.rate_limited_requests,
                "success_rate": rate,
                "last_success_at": h.last_success_at,
                "last_failure_at": h.last_failure_at,
                "cooldown_until": h.cooldown_until,
                "is_in_cooldown": is_in_cd,
                "cooldown_remaining_seconds": cd_rem,
                "last_error_code": h.last_error_code,
                "last_error_message": h.last_error_message
            })

        overall = "healthy"
        if active_count == 0:
            overall = "all_down"
        elif active_count < len(self.providers):
            overall = "degraded"

        return {
            "overall_status": overall,
            "preferred_provider": preferred,
            "active_providers_count": active_count,
            "providers": items
        }
