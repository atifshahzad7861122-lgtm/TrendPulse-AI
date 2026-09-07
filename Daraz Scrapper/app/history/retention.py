"""Rolling 365-day retention manager for historical product observations."""

from datetime import datetime, timedelta, timezone
import time
from typing import Any, Dict, Optional

from app.history.models import RetentionResult
from app.history.store import BaseHistoricalStore


class HistoricalRetentionManager:
    """
    Enforces a rolling 365-day retention policy on historical observations.
    Permanently prunes records older than 365 days while strictly preserving
    all active observation history within the 365-day rolling window.
    """

    DEFAULT_RETENTION_DAYS = 365

    def __init__(self, store: BaseHistoricalStore, default_retention_days: int = DEFAULT_RETENTION_DAYS):
        self.store = store
        self.retention_days = default_retention_days

    async def preview_expired(self, cutoff_days: Optional[int] = None) -> RetentionResult:
        """
        Preview expired observation records slated for deletion without modifying disk state (Dry-Run).
        """
        days = cutoff_days if cutoff_days is not None else self.retention_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return await self.store.delete_expired(cutoff_date=cutoff_date, dry_run=True)

    async def delete_expired(self, cutoff_days: Optional[int] = None) -> RetentionResult:
        """
        Permanently delete expired observation records older than cutoff_days (Default 365 days).
        """
        days = cutoff_days if cutoff_days is not None else self.retention_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return await self.store.delete_expired(cutoff_date=cutoff_date, dry_run=False)

    async def run_retention(self, cutoff_days: Optional[int] = None, dry_run: bool = False) -> RetentionResult:
        """
        Execute the retention policy, returning structured metrics and execution latency.
        """
        t_start = time.monotonic()
        days = cutoff_days if cutoff_days is not None else self.retention_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        res = await self.store.delete_expired(cutoff_date=cutoff_date, dry_run=dry_run)
        elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)

        return RetentionResult(
            total_inspected=res.total_inspected,
            expired_count=res.expired_count,
            deleted_count=res.deleted_count,
            preserved_count=res.preserved_count,
            oldest_preserved_date=res.oldest_preserved_date,
            is_dry_run=dry_run,
            execution_time_ms=elapsed_ms,
        )

    async def get_retention_statistics(self) -> Dict[str, Any]:
        """
        Retrieve current storage footprint and statistics.
        """
        store_stats = await self.store.get_store_statistics()
        return {
            "retention_policy_days": self.retention_days,
            **store_stats,
        }
