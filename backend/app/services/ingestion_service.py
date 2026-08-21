import time
import logging
import threading
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
from backend.app.domain.signals import PlatformSignal, IngestionResult, SignalBatch
from backend.app.domain.matching import ProductMatchingEngine
from backend.app.domain.data_quality import DataQualityService
from backend.app.domain.classification import CategoryClassificationService
from backend.app.domain.prediction import TrendPredictionService
from backend.app.connectors.base import DataSourceConnector
from backend.app.connectors.youtube_connector import YouTubeDataConnector
from backend.app.connectors.mock_connectors import (
    MockTikTokConnector, MockDarazConnector, MockInstagramConnector, MockFacebookConnector
)
from backend.app.repositories.base import (
    ProductRepository, DataSourceRepository, AlertRepository, NotificationRepository
)
from backend.app.services.intelligence import ProductIntelligenceEngine
from backend.app.services.alert_service import AlertService
from backend.app.services.notification_service import NotificationService
from backend.app.core.config import settings

logger = logging.getLogger("trendpulse.ingestion")

class IngestionPipeline:
    """
    Production-grade multi-stage ingestion pipeline with thread-safe concurrency locks,
    data quality validation, product entity matching, taxonomy classification,
    trend trajectory prediction, and automatic downstream intelligence/alert triggers.
    """

    def __init__(
        self,
        product_repo: ProductRepository,
        datasource_repo: DataSourceRepository,
        intelligence_engine: ProductIntelligenceEngine,
        alert_service: AlertService,
        notification_service: NotificationService,
        connectors: Optional[Dict[str, DataSourceConnector]] = None
    ):
        self.products = product_repo
        self.sources = datasource_repo
        self.intelligence = intelligence_engine
        self.alerts = alert_service
        self.notifications = notification_service
        self.connectors: Dict[str, DataSourceConnector] = connectors or {}

        # Prepopulate default connectors
        if "youtube" not in self.connectors:
            self.connectors["youtube"] = YouTubeDataConnector()
        if "tiktok" not in self.connectors:
            self.connectors["tiktok"] = MockTikTokConnector()
        if "daraz" not in self.connectors:
            self.connectors["daraz"] = MockDarazConnector()
        if "instagram" not in self.connectors:
            self.connectors["instagram"] = MockInstagramConnector()
        if "facebook" not in self.connectors:
            self.connectors["facebook"] = MockFacebookConnector()

        # Concurrency & Deduplication tracking
        self._lock = threading.Lock()
        self._active_syncs: Set[str] = set()
        self._processed_dedup_keys: Set[str] = set()

    def register_connector(self, slug: str, connector: DataSourceConnector) -> None:
        self.connectors[slug] = connector

    def sync_source(self, slug: str, limit: int = 50, query: Optional[str] = None) -> IngestionResult:
        """
        Executes a single data source sync run through all intelligence agents.
        """
        start_time = time.time()
        start_dt = datetime.now(timezone.utc)

        # 1. Thread concurrency check
        with self._lock:
            if slug in self._active_syncs:
                return IngestionResult(
                    source=slug,
                    is_live=False,
                    started_at=start_dt,
                    completed_at=datetime.now(timezone.utc),
                    duration_seconds=0.0,
                    status="Skipped",
                    errors=[f"Sync for '{slug}' is already running. Concurrency collision prevented."]
                )
            self._active_syncs.add(slug)

        try:
            connector = self.connectors.get(slug)
            if not connector:
                return IngestionResult(
                    source=slug,
                    is_live=False,
                    started_at=start_dt,
                    completed_at=datetime.now(timezone.utc),
                    duration_seconds=round(time.time() - start_time, 2),
                    status="Failed",
                    errors=[f"No registered connector found for source '{slug}'"]
                )

            # 2. Fetch external signals
            is_live = False
            fetch_error = None
            if hasattr(connector, "fetch_signals_with_mode"):
                raw_signals, is_live, fetch_error = connector.fetch_signals_with_mode(limit=limit, query=query)
            else:
                raw_signals = connector.fetch_signals(limit=limit)
                is_live = getattr(connector, "is_live_configured", False)

            errors: List[str] = []
            if fetch_error:
                errors.append(fetch_error)

            records_received = len(raw_signals)
            records_normalized = 0
            records_matched = 0
            records_unmatched = 0
            records_ambiguous = 0
            records_inserted = 0
            records_updated = 0
            records_skipped = 0
            records_failed = 0
            alerts_created = 0
            notifications_created = 0

            catalog = self.products.list()

            # 3. Process each signal through Intelligence Agents
            for signal in raw_signals:
                # Agent A: Data Quality Validation
                is_valid, quality_score, quality_reasons, quality_warnings = DataQualityService.evaluate_quality(signal)
                if not is_valid:
                    records_failed += 1
                    errors.extend(quality_reasons)
                    continue

                records_normalized += 1

                # Agent B: Product Matching Engine
                match_res = ProductMatchingEngine.match_content_detailed(signal.product_name, catalog)
                
                if match_res.match_type == "matched":
                    records_matched += 1
                    target_product = match_res.product
                elif match_res.match_type == "ambiguous":
                    records_ambiguous += 1
                    target_product = match_res.product
                else:
                    records_unmatched += 1
                    target_product = None

                # If unmatched, do not contaminate catalog
                if not target_product:
                    continue

                # Agent C: Category Classification
                class_res = CategoryClassificationService.classify(
                    f"{signal.product_name} {target_product.name}",
                    target_product.category
                )
                signal.category = class_res.category

                # Agent D: Deduplication Check
                dedup_key = signal.deduplication_key
                with self._lock:
                    if dedup_key in self._processed_dedup_keys:
                        records_skipped += 1
                        continue
                    self._processed_dedup_keys.add(dedup_key)

                # Mutate Catalog Product Telemetry
                target_product.volume += signal.volume
                target_product.signals_count += 1
                if signal.platform not in target_product.platforms:
                    target_product.platforms.append(signal.platform)

                # Recalculate Product Intelligence
                enriched = self.intelligence._enrich_product(target_product)
                self.products.update(enriched)
                records_updated += 1
                records_inserted += 1

                # Agent E: Trend Prediction Evaluation
                prediction = TrendPredictionService.predict_product_trajectory(enriched)
                if hasattr(enriched, "raw_data") and isinstance(enriched.raw_data, dict):
                    enriched.raw_data["prediction"] = prediction.to_dict()

                # Agent F: Anomaly Alert Evaluation
                new_alert = self.alerts.evaluate_product_signals(enriched)
                if new_alert:
                    alerts_created += 1
                    self.notifications.dispatch(
                        title=new_alert.title,
                        message=new_alert.description,
                        type_="alert",
                        link=f"/products/{new_alert.product_id}" if new_alert.product_id else None
                    )
                    notifications_created += 1

            # 4. Update Data Source Telemetry in repository
            source_rec = self.sources.get_by_slug(slug)
            if source_rec:
                source_rec.records_synced += records_inserted
                source_rec.status = "Connected"
                source_rec.health_score = 98 if is_live else 92
                self.sources.update(source_rec)

            duration = round(time.time() - start_time, 2)
            status = "Success" if not errors else ("Partial" if records_inserted > 0 else "Failed")

            return IngestionResult(
                source=slug,
                is_live=is_live,
                started_at=start_dt,
                completed_at=datetime.now(timezone.utc),
                duration_seconds=duration,
                records_received=records_received,
                records_normalized=records_normalized,
                records_matched=records_matched,
                records_unmatched=records_unmatched,
                records_ambiguous=records_ambiguous,
                records_inserted=records_inserted,
                records_updated=records_updated,
                records_skipped=records_skipped,
                records_failed=records_failed,
                alerts_created=alerts_created,
                notifications_created=notifications_created,
                status=status,
                errors=errors
            )

        finally:
            with self._lock:
                self._active_syncs.discard(slug)

    def sync_all(self, limit_per_source: int = 50) -> Dict[str, Any]:
        """
        Syncs all registered/connected data sources.
        """
        all_sources = self.sources.list()
        connected = [s for s in all_sources if s.status == "Connected"]
        
        total_ingested = 0
        results: List[Dict[str, Any]] = []

        for src in connected:
            res = self.sync_source(src.slug, limit=limit_per_source)
            total_ingested += res.records_inserted
            results.append(res.model_dump())

        return {
            "total_records": total_ingested,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "results": results
        }

    def run_ingestion_cycle(self) -> SignalBatch:
        """
        Backward compatibility helper returning SignalBatch.
        """
        summary = self.sync_all()
        return SignalBatch(
            source_slug="all",
            ingested_at=datetime.now(timezone.utc),
            signals=[],
            total_records=summary["total_records"]
        )
