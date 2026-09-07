import time
import random
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Callable
from pydantic import BaseModel, Field

from backend.app.models.domain import (
    MarketplaceProduct, ProductMarketSnapshot, DarazSeller, DarazCategory,
    DarazReview, DarazIngestionRun, DarazApiTelemetry, DarazDailyQuota,
    DarazTrainingDataset
)
from backend.app.repositories.base import (
    MarketplaceProductRepository, DataQualityRepository
)
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.services.agents.data_quality.agent import DataQualityAgent

logger = logging.getLogger("trendpulse.daraz.ingestion_engine")


class DarazIngestionConfig(BaseModel):
    """Configuration for Daraz Ingestion Engine runs."""
    target_count: int = 1000
    batch_size: int = 50  # Fetch chunk size (max 50 per Official Daraz /products/get)
    persistence_batch_size: int = 100
    safety_quota_margin: int = 10000  # Stop if remaining daily quota falls below this threshold
    max_retries: int = 5
    base_backoff_seconds: float = 1.5
    jitter: bool = True
    delay_between_requests: float = 0.25  # Polite pacing between requests
    search_filter: str = "all"
    category_id: Optional[str] = None
    search_query: Optional[str] = None


class IngestionProgressSummary(BaseModel):
    """Real-time progress telemetry for an ingestion run."""
    run_id: str
    status: str  # pending, running, paused, completed, partial, failed, blocked_authorization
    target_count: int
    products_fetched: int = 0
    products_inserted: int = 0
    products_updated: int = 0
    duplicates_prevented: int = 0
    snapshots_created: int = 0
    sellers_persisted: int = 0
    categories_persisted: int = 0
    reviews_persisted: int = 0
    agent1_valid: int = 0
    agent1_warning: int = 0
    agent1_needs_review: int = 0
    agent1_rejected: int = 0
    training_eligible: int = 0
    api_requests_consumed: int = 0
    daily_quota_remaining: int = 6000000
    current_offset: int = 0
    current_page: int = 1
    has_more: bool = True
    elapsed_seconds: float = 0.0
    products_per_second: float = 0.0
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    last_checkpoint_at: Optional[datetime] = None


class DarazIngestionEngine:
    """
    Enterprise-grade, resumable, quota-protected, and memory-safe ingestion engine
    for the Official Daraz Open Platform.
    """

    def __init__(
        self,
        provider: DarazOfficialProvider,
        repository: MarketplaceProductRepository,
        dq_repository: Optional[DataQualityRepository] = None,
        config: Optional[DarazIngestionConfig] = None
    ):
        self.provider = provider
        self.repository = repository
        self.dq_repository = dq_repository
        self.dq_agent = DataQualityAgent(repository=dq_repository) if dq_repository else None
        self.config = config or DarazIngestionConfig()

        self._active_run_id: Optional[str] = None
        self._pause_requested: bool = False
        self._stop_requested: bool = False
        self._lock = threading.RLock()
        self._current_progress: Optional[IngestionProgressSummary] = None

    # ----------------------------------------------------------------------
    # Core Ingestion Execution Lifecycle
    # ----------------------------------------------------------------------

    def execute_batch_ingestion(
        self,
        run_id: Optional[str] = None,
        target_count: Optional[int] = None,
        resume_from_checkpoint: bool = True
    ) -> IngestionProgressSummary:
        """
        Executes a controlled, resumable ingestion run up to target_count products.
        """
        with self._lock:
            if self._active_run_id and self._current_progress and self._current_progress.status == "running":
                raise RuntimeError(f"An ingestion run ({self._active_run_id}) is already in progress.")
            self._pause_requested = False
            self._stop_requested = False

        effective_target = target_count or self.config.target_count

        # 1. Initialize or Resume Ingestion Run
        ingestion_run, progress = self._prepare_run(run_id, effective_target, resume_from_checkpoint)
        self._active_run_id = ingestion_run.id
        self._current_progress = progress

        start_time = time.time()
        logger.info(f"Starting Daraz Ingestion Run {ingestion_run.id}: Target={effective_target}, Offset={progress.current_offset}")

        # Verify seller authentication context
        active_token, auth_err = self.provider.get_active_token()
        if not active_token:
            logger.warning(f"Ingestion run {ingestion_run.id} blocked: {auth_err}")
            progress.status = "blocked_authorization"
            progress.error_code = 401
            progress.error_message = f"Daraz OAuth authorization required: {auth_err}"
            self._save_checkpoint(ingestion_run, progress)
            with self._lock:
                self._active_run_id = None
            return progress

        try:
            while progress.products_fetched < effective_target and progress.has_more:
                # Check for user pause/stop signals
                if self._pause_requested:
                    logger.info(f"Ingestion run {ingestion_run.id} paused by user.")
                    progress.status = "paused"
                    self._save_checkpoint(ingestion_run, progress)
                    break

                if self._stop_requested:
                    logger.info(f"Ingestion run {ingestion_run.id} stopped by user.")
                    progress.status = "partial"
                    self._save_checkpoint(ingestion_run, progress)
                    break

                # 2. Check Daily Quota Protection
                quota_ok, quota_msg, quota_obj = self._check_quota_guard()
                if not quota_ok:
                    logger.warning(f"Quota safety guard triggered: {quota_msg}")
                    progress.status = "partial"
                    progress.error_message = quota_msg
                    self._save_checkpoint(ingestion_run, progress)
                    break

                progress.daily_quota_remaining = quota_obj.remaining

                # 3. Fetch Next Chunk from Official Daraz API with Exponential Backoff
                limit = min(self.config.batch_size, effective_target - progress.products_fetched)
                fetch_success, raw_items, total_in_source, err_code, err_msg = self._fetch_chunk_with_retry(
                    offset=progress.current_offset,
                    limit=limit
                )

                if not fetch_success:
                    if err_code in (401, 403) or "IllegalAccessToken" in (err_msg or "") or "AccessTokenExpired" in (err_msg or "") or "access_token" in (err_msg or "").lower():
                        progress.status = "blocked_authorization"
                        progress.error_code = 401
                        progress.error_message = f"Daraz OAuth authorization required: {err_msg}"
                    else:
                        progress.status = "failed"
                        progress.error_code = err_code
                        progress.error_message = err_msg

                    logger.error(f"Ingestion chunk fetch failed: {progress.error_message}")
                    self._save_checkpoint(ingestion_run, progress)
                    break

                progress.api_requests_consumed += 1

                if not raw_items:
                    logger.info(f"Official Daraz API returned 0 items at offset {progress.current_offset}. Reached end of catalog.")
                    progress.has_more = False
                    break

                # 4. Normalize & Batch Persist into Repository / Supabase
                batch_inserted, batch_updated, batch_duplicates, batch_snapshots = self._persist_product_batch(raw_items)
                
                progress.products_fetched += len(raw_items)
                progress.products_inserted += batch_inserted
                progress.products_updated += batch_updated
                progress.duplicates_prevented += batch_duplicates
                progress.snapshots_created += batch_snapshots
                progress.current_offset += len(raw_items)
                progress.current_page = (progress.current_offset // self.config.batch_size) + 1

                # Check if total available reached
                if total_in_source and progress.current_offset >= total_in_source:
                    progress.has_more = False

                # 5. Agent 1 Data Quality Validation & Training Dataset Filtering
                self._run_agent1_pipeline(raw_items, progress)

                # 6. Periodic Checkpointing
                progress.elapsed_seconds = round(time.time() - start_time, 2)
                if progress.elapsed_seconds > 0:
                    progress.products_per_second = round(progress.products_fetched / progress.elapsed_seconds, 2)
                self._save_checkpoint(ingestion_run, progress)

                # Polite rate pacing
                if self.config.delay_between_requests > 0:
                    time.sleep(self.config.delay_between_requests)

            # Mark completed if target reached or catalog exhausted without errors
            if progress.status == "running":
                progress.status = "completed"
                self._save_checkpoint(ingestion_run, progress)

        except Exception as e:
            logger.exception(f"Unhandled exception during ingestion run {ingestion_run.id}: {e}")
            progress.status = "failed"
            progress.error_message = str(e)
            self._save_checkpoint(ingestion_run, progress)

        finally:
            progress.elapsed_seconds = round(time.time() - start_time, 2)
            if progress.elapsed_seconds > 0:
                progress.products_per_second = round(progress.products_fetched / progress.elapsed_seconds, 2)
            self._save_checkpoint(ingestion_run, progress)
            with self._lock:
                self._active_run_id = None

        return progress

    # ----------------------------------------------------------------------
    # Control API Handlers
    # ----------------------------------------------------------------------

    def pause(self) -> bool:
        """Requests active ingestion to pause at the next checkpoint."""
        with self._lock:
            if self._active_run_id:
                self._pause_requested = True
                return True
            return False

    def stop(self) -> bool:
        """Requests active ingestion to abort cleanly at the next checkpoint."""
        with self._lock:
            if self._active_run_id:
                self._stop_requested = True
                return True
            return False

    def get_status(self, run_id: Optional[str] = None) -> Optional[IngestionProgressSummary]:
        """Returns the current progress or loads status from a specific run."""
        if self._current_progress and (not run_id or self._current_progress.run_id == run_id):
            return self._current_progress

        if run_id:
            db_run = self.repository.get_ingestion_run(run_id)
            if db_run:
                meta = db_run.metadata_json or {}
                return IngestionProgressSummary(
                    run_id=db_run.id,
                    status=db_run.status,
                    target_count=meta.get("target_count", 0),
                    products_fetched=db_run.products_fetched,
                    products_inserted=db_run.products_inserted,
                    products_updated=db_run.products_updated,
                    duplicates_prevented=meta.get("duplicates_prevented", 0),
                    snapshots_created=db_run.snapshots_created,
                    agent1_valid=meta.get("agent1_valid", 0),
                    agent1_warning=meta.get("agent1_warning", 0),
                    agent1_needs_review=meta.get("agent1_needs_review", 0),
                    agent1_rejected=meta.get("agent1_rejected", 0),
                    training_eligible=meta.get("training_eligible", 0),
                    api_requests_consumed=meta.get("api_requests_consumed", 0),
                    daily_quota_remaining=meta.get("daily_quota_remaining", 6000000),
                    current_offset=meta.get("current_offset", 0),
                    current_page=meta.get("current_page", 1),
                    has_more=meta.get("has_more", False),
                    elapsed_seconds=meta.get("elapsed_seconds", 0.0),
                    products_per_second=meta.get("products_per_second", 0.0),
                    error_code=db_run.error_code,
                    error_message=db_run.error_message,
                    last_checkpoint_at=meta.get("last_checkpoint_at")
                )
        return None

    def list_history(self, limit: int = 20) -> List[DarazIngestionRun]:
        """Retrieves history of past ingestion runs."""
        return self.repository.list_ingestion_runs(limit=limit)

    # ----------------------------------------------------------------------
    # Helper Methods & Pipeline Stages
    # ----------------------------------------------------------------------

    def _prepare_run(
        self,
        run_id: Optional[str],
        target_count: int,
        resume_from_checkpoint: bool
    ) -> Tuple[DarazIngestionRun, IngestionProgressSummary]:
        now = datetime.now(timezone.utc)

        if run_id and resume_from_checkpoint:
            existing = self.repository.get_ingestion_run(run_id)
            if existing:
                meta = existing.metadata_json or {}
                progress = IngestionProgressSummary(
                    run_id=existing.id,
                    status="running",
                    target_count=meta.get("target_count", target_count),
                    products_fetched=existing.products_fetched,
                    products_inserted=existing.products_inserted,
                    products_updated=existing.products_updated,
                    duplicates_prevented=meta.get("duplicates_prevented", 0),
                    snapshots_created=existing.snapshots_created,
                    agent1_valid=meta.get("agent1_valid", 0),
                    agent1_warning=meta.get("agent1_warning", 0),
                    agent1_needs_review=meta.get("agent1_needs_review", 0),
                    agent1_rejected=meta.get("agent1_rejected", 0),
                    training_eligible=meta.get("training_eligible", 0),
                    api_requests_consumed=meta.get("api_requests_consumed", 0),
                    daily_quota_remaining=meta.get("daily_quota_remaining", 6000000),
                    current_offset=meta.get("current_offset", 0),
                    current_page=meta.get("current_page", 1),
                    has_more=meta.get("has_more", True),
                    last_checkpoint_at=now
                )
                existing.status = "running"
                self.repository.update_ingestion_run(existing)
                return existing, progress

        # Create fresh run
        new_id = run_id or f"daraz_run_{int(time.time())}_{random.randint(100, 999)}"
        new_run = DarazIngestionRun(
            id=new_id,
            provider_name="daraz_official_open_platform",
            status="running",
            trigger_type="manual",
            search_query=self.config.search_query or self.config.search_filter,
            products_fetched=0,
            products_inserted=0,
            products_updated=0,
            snapshots_created=0,
            metadata_json={
                "target_count": target_count,
                "current_offset": 0,
                "current_page": 1,
                "duplicates_prevented": 0,
                "api_requests_consumed": 0,
                "has_more": True,
                "created_at": now.isoformat()
            },
            started_at=now,
            created_at=now
        )
        self.repository.create_ingestion_run(new_run)

        progress = IngestionProgressSummary(
            run_id=new_id,
            status="running",
            target_count=target_count,
            daily_quota_remaining=6000000,
            current_offset=0,
            current_page=1,
            has_more=True,
            last_checkpoint_at=now
        )
        return new_run, progress

    def _check_quota_guard(self) -> Tuple[bool, str, DarazDailyQuota]:
        quota = self.repository.get_or_create_daily_quota()
        if quota.remaining <= self.config.safety_quota_margin:
            return False, f"Daily quota safety margin reached: {quota.remaining} remaining (Safety limit: {self.config.safety_quota_margin})", quota
        return True, "Quota OK", quota

    def _fetch_chunk_with_retry(
        self,
        offset: int,
        limit: int
    ) -> Tuple[bool, List[Dict[str, Any]], int, Optional[int], Optional[str]]:
        """
        Fetches a single chunk of products via Official Daraz Open Platform /products/get
        with exponential backoff, jitter, and Retry-After support.
        """
        params: Dict[str, Any] = {
            "filter": self.config.search_filter,
            "limit": str(limit),
            "offset": str(offset)
        }
        if self.config.search_query:
            params["search"] = self.config.search_query
        if self.config.category_id:
            params["category_id"] = self.config.category_id

        for attempt in range(1, self.config.max_retries + 1):
            success, res_data, status_code, err = self.provider._execute_api_call(
                api_path="/products/get",
                params=params,
                require_auth=True
            )

            if success and res_data:
                data_block = res_data.get("data", {})
                products = data_block.get("products", []) if isinstance(data_block, dict) else []
                total = int(data_block.get("total_products", len(products)) if isinstance(data_block, dict) else len(products))
                return True, products, total, 200, None

            # Check for Rate Limit 429
            if status_code == 429:
                sleep_sec = (self.config.base_backoff_seconds ** attempt)
                if self.config.jitter:
                    sleep_sec += random.uniform(0.1, 0.8)
                logger.warning(f"Daraz rate limit (429) on attempt {attempt}/{self.config.max_retries}. Backing off for {sleep_sec:.2f}s")
                if attempt >= self.config.max_retries:
                    return False, [], 0, 429, "Rate limit exceeded after maximum retries."
                time.sleep(sleep_sec)
                continue

            # Check for Auth Failure
            if status_code in (401, 403):
                return False, [], 0, status_code, err or "Daraz OAuth authorization failed or expired."

            # Network / Upstream 5xx retries
            if status_code >= 500 or status_code in (502, 503, 504):
                sleep_sec = 1.0 * attempt
                if attempt >= self.config.max_retries:
                    return False, [], 0, status_code, err or f"Upstream error HTTP {status_code}"
                time.sleep(sleep_sec)
                continue

            # Unrecoverable error
            return False, [], 0, status_code, err or "Failed to fetch products."

        return False, [], 0, 500, "Fetch failed after retries."

    def _persist_product_batch(self, raw_items: List[Dict[str, Any]]) -> Tuple[int, int, int, int]:
        """
        Idempotently persists a batch of normalized Daraz products and market snapshots.
        """
        inserted_count = 0
        updated_count = 0
        duplicate_prevented_count = 0
        snapshots_created = 0

        now = datetime.now(timezone.utc)
        products_to_upsert: List[MarketplaceProduct] = []
        snapshots_to_create: List[ProductMarketSnapshot] = []

        for item in raw_items:
            p_id = str(item.get("item_id") or item.get("product_id") or "")
            if not p_id:
                continue

            attr = item.get("attributes", {})
            skus = item.get("skus", [])
            primary_sku = skus[0] if skus else {}

            price = float(primary_sku.get("price") or primary_sku.get("special_price") or attr.get("price") or 0.0)
            orig_price = float(primary_sku.get("original_price") or primary_sku.get("price") or price)
            discount = round(((orig_price - price) / orig_price * 100), 1) if (orig_price > price > 0) else 0.0

            title = str(attr.get("name") or item.get("name") or "Daraz Product")
            img = str(
                attr.get("Images", [""])[0] if isinstance(attr.get("Images"), list) and attr.get("Images") else
                primary_sku.get("Images", [""])[0] if isinstance(primary_sku.get("Images"), list) and primary_sku.get("Images") else ""
            )

            # Check idempotency / duplicates
            existing = self.repository.get_product(platform="daraz", product_id=p_id)
            if existing:
                duplicate_prevented_count += 1
                updated_count += 1
            else:
                inserted_count += 1

            mp_prod = MarketplaceProduct(
                id=f"daraz_{p_id}",
                platform="daraz",
                product_id=p_id,
                product_name=title,
                price=price,
                original_price=orig_price,
                discount_percentage=discount,
                discount_label=f"{int(discount)}% OFF" if discount > 0 else None,
                currency="PKR",
                rating=float(item.get("rating") or attr.get("rating") or 4.5),
                review_count=int(item.get("review_count") or attr.get("review_count") or 0),
                seller_name=str(item.get("seller_name") or "Daraz Official Seller"),
                seller_id=str(item.get("seller_id") or ""),
                category=str(attr.get("category_name") or "General"),
                image_url=img,
                product_url=f"https://www.daraz.pk/products/-i{p_id}.html",
                in_stock=primary_sku.get("quantity", 1) > 0,
                stock_status="in_stock" if primary_sku.get("quantity", 1) > 0 else "out_of_stock",
                raw_source_data=item,
                created_at=now,
                updated_at=now
            )
            products_to_upsert.append(mp_prod)

            # Create historical snapshot
            snap = ProductMarketSnapshot(
                id=f"snap_{p_id}_{int(time.time())}_{random.randint(100, 999)}",
                product_id=p_id,
                platform="daraz",
                price=price,
                original_price=orig_price,
                discount=discount,
                rating=mp_prod.rating,
                review_count=mp_prod.review_count,
                stock_status=mp_prod.stock_status,
                observed_at=now,
                created_at=now
            )
            snapshots_to_create.append(snap)
            snapshots_created += 1

        # Execute Batched Database Writes
        if products_to_upsert:
            self.repository.batch_upsert_products(products_to_upsert)
        if snapshots_to_create:
            self.repository.batch_create_snapshots(snapshots_to_create)

        return inserted_count, updated_count, duplicate_prevented_count, snapshots_created

    def _run_agent1_pipeline(self, raw_items: List[Dict[str, Any]], progress: IngestionProgressSummary) -> None:
        """
        Passes ingested batch through Agent 1 Data Quality rules and checks training eligibility.
        """
        if not self.dq_agent:
            return

        for item in raw_items:
            p_id = str(item.get("item_id") or item.get("product_id") or "")
            attr = item.get("attributes", {})
            skus = item.get("skus", [])
            primary_sku = skus[0] if skus else {}

            price = float(primary_sku.get("price") or primary_sku.get("special_price") or attr.get("price") or 0.0)
            title = str(attr.get("name") or item.get("name") or "Daraz Product")
            rating = float(item.get("rating") or attr.get("rating") or 4.5)
            review_count = int(item.get("review_count") or attr.get("review_count") or 0)
            brand = str(attr.get("brand") or "")
            category = str(attr.get("category_name") or "General")

            payload = {
                "id": p_id,
                "platform_product_id": p_id,
                "platform": "daraz",
                "name": title,
                "title": title,
                "price": price,
                "rating": rating,
                "review_count": review_count,
                "reviews_count": review_count,
                "brand": brand,
                "category": category,
                "product_url": f"https://www.daraz.pk/products/-i{p_id}.html",
                "in_stock": primary_sku.get("quantity", 1) > 0
            }

            try:
                dq_res = self.dq_agent.validate_product(payload, allow_llm=False)
                classification = str(dq_res.classification).lower() if hasattr(dq_res, "classification") else "valid"
                
                if "valid" in classification:
                    progress.agent1_valid += 1
                elif "warn" in classification:
                    progress.agent1_warning += 1
                elif "review" in classification:
                    progress.agent1_needs_review += 1
                else:
                    progress.agent1_rejected += 1

                # Strict Training Eligibility Rule: valid + rating >= 4.0 + reviews >= 5 + price > 0
                if "valid" in classification and rating >= 4.0 and review_count >= 5 and price > 0:
                    tr = DarazTrainingDataset(
                        product_id=p_id,
                        title=title,
                        category=category,
                        brand=brand if brand else None,
                        price=price,
                        rating=rating,
                        review_count=review_count,
                        features={"title": title, "price": price, "rating": rating, "reviews": review_count, "brand": brand},
                        agent_label="high_quality_live_product"
                    )
                    self.repository.add_training_dataset_item(tr)
                    progress.training_eligible += 1
            except Exception as e:
                logger.warning(f"Agent 1 validation error on product {p_id}: {e}")

    def _save_checkpoint(self, run: DarazIngestionRun, progress: IngestionProgressSummary) -> None:
        """Persists atomic checkpoint state to repository."""
        now = datetime.now(timezone.utc)
        run.status = progress.status
        run.products_fetched = progress.products_fetched
        run.products_inserted = progress.products_inserted
        run.products_updated = progress.products_updated
        run.snapshots_created = progress.snapshots_created
        run.error_code = progress.error_code
        run.error_message = progress.error_message

        if progress.status in ("completed", "failed", "blocked_authorization"):
            run.completed_at = now

        meta = run.metadata_json or {}
        meta.update({
            "target_count": progress.target_count,
            "current_offset": progress.current_offset,
            "current_page": progress.current_page,
            "duplicates_prevented": progress.duplicates_prevented,
            "agent1_valid": progress.agent1_valid,
            "agent1_warning": progress.agent1_warning,
            "agent1_needs_review": progress.agent1_needs_review,
            "agent1_rejected": progress.agent1_rejected,
            "training_eligible": progress.training_eligible,
            "api_requests_consumed": progress.api_requests_consumed,
            "daily_quota_remaining": progress.daily_quota_remaining,
            "elapsed_seconds": progress.elapsed_seconds,
            "products_per_second": progress.products_per_second,
            "has_more": progress.has_more,
            "last_checkpoint_at": now.isoformat()
        })
        run.metadata_json = meta
        progress.last_checkpoint_at = now

        try:
            self.repository.update_ingestion_run(run)
        except Exception as e:
            logger.error(f"Failed to persist checkpoint for run {run.id}: {e}")
