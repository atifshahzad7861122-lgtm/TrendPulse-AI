"""Historical observation storage layer for TrendPulse 30-day collection and 365-day retention."""

from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.crawling.models import MarketplaceType
from app.history.models import HistoricalObservation, RetentionResult


class BaseHistoricalStore(ABC):
    """Abstract interface for historical observation storage and retention."""

    @abstractmethod
    async def save_observation(self, observation: HistoricalObservation) -> None:
        """Persist a single historical observation."""
        pass

    @abstractmethod
    async def save_observations(self, observations: List[HistoricalObservation]) -> int:
        """Bulk persist historical observations. Returns count saved."""
        pass

    @abstractmethod
    async def get_latest_observation(
        self, marketplace: MarketplaceType, product_id: str
    ) -> Optional[HistoricalObservation]:
        """Retrieve the most recent observation for a product."""
        pass

    @abstractmethod
    async def get_observations_in_window(
        self,
        marketplace: MarketplaceType,
        product_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> List[HistoricalObservation]:
        """Retrieve all observations for a product within a timestamp window."""
        pass

    @abstractmethod
    async def get_all_observations_for_product(
        self, marketplace: MarketplaceType, product_id: str
    ) -> List[HistoricalObservation]:
        """Retrieve chronological history for a product."""
        pass

    @abstractmethod
    async def list_tracked_products(
        self, marketplace: Optional[MarketplaceType] = None
    ) -> List[Tuple[MarketplaceType, str]]:
        """Return list of (marketplace, product_id) pairs currently tracked."""
        pass

    @abstractmethod
    async def delete_expired(self, cutoff_date: datetime, dry_run: bool = False) -> RetentionResult:
        """Prune observations older than cutoff_date. Supports dry-run."""
        pass

    @abstractmethod
    async def get_store_statistics(self) -> Dict[str, Any]:
        """Retrieve summary statistics of historical records."""
        pass


class InMemoryHistoricalStore(BaseHistoricalStore):
    """In-memory implementation of historical observation store for fast unit testing."""

    def __init__(self):
        # Key: (marketplace, product_id) -> List[HistoricalObservation] (sorted by observed_at)
        self._records: Dict[Tuple[MarketplaceType, str], List[HistoricalObservation]] = {}
        self._observation_ids: Set[str] = set()
        self._lock = asyncio.Lock()

    async def save_observation(self, observation: HistoricalObservation) -> None:
        async with self._lock:
            key = (observation.marketplace, observation.product_id)
            if observation.observation_id in self._observation_ids:
                return  # Deduplicated

            if key not in self._records:
                self._records[key] = []

            self._records[key].append(observation)
            # Maintain chronological order
            self._records[key].sort(key=lambda o: o.observed_at)
            self._observation_ids.add(observation.observation_id)

    async def save_observations(self, observations: List[HistoricalObservation]) -> int:
        saved_count = 0
        async with self._lock:
            for obs in observations:
                if obs.observation_id in self._observation_ids:
                    continue
                key = (obs.marketplace, obs.product_id)
                if key not in self._records:
                    self._records[key] = []
                self._records[key].append(obs)
                self._observation_ids.add(obs.observation_id)
                saved_count += 1

            for key in self._records:
                self._records[key].sort(key=lambda o: o.observed_at)
        return saved_count

    async def get_latest_observation(
        self, marketplace: MarketplaceType, product_id: str
    ) -> Optional[HistoricalObservation]:
        async with self._lock:
            key = (marketplace, product_id)
            history = self._records.get(key, [])
            return history[-1] if history else None

    async def get_observations_in_window(
        self,
        marketplace: MarketplaceType,
        product_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> List[HistoricalObservation]:
        async with self._lock:
            key = (marketplace, product_id)
            history = self._records.get(key, [])
            end = end_date or datetime.now(timezone.utc)
            return [obs for obs in history if start_date <= obs.observed_at <= end]

    async def get_all_observations_for_product(
        self, marketplace: MarketplaceType, product_id: str
    ) -> List[HistoricalObservation]:
        async with self._lock:
            key = (marketplace, product_id)
            return list(self._records.get(key, []))

    async def list_tracked_products(
        self, marketplace: Optional[MarketplaceType] = None
    ) -> List[Tuple[MarketplaceType, str]]:
        async with self._lock:
            if marketplace:
                return [k for k in self._records.keys() if k[0] == marketplace]
            return list(self._records.keys())

    async def delete_expired(self, cutoff_date: datetime, dry_run: bool = False) -> RetentionResult:
        async with self._lock:
            total_inspected = 0
            expired_count = 0
            preserved_count = 0
            oldest_preserved: Optional[datetime] = None

            for key, history in list(self._records.items()):
                new_history = []
                for obs in history:
                    total_inspected += 1
                    if obs.observed_at < cutoff_date:
                        expired_count += 1
                    else:
                        preserved_count += 1
                        new_history.append(obs)
                        if oldest_preserved is None or obs.observed_at < oldest_preserved:
                            oldest_preserved = obs.observed_at

                if not dry_run:
                    if new_history:
                        self._records[key] = new_history
                    else:
                        del self._records[key]

            deleted_count = 0 if dry_run else expired_count
            return RetentionResult(
                total_inspected=total_inspected,
                expired_count=expired_count,
                deleted_count=deleted_count,
                preserved_count=preserved_count,
                oldest_preserved_date=oldest_preserved,
                is_dry_run=dry_run,
            )

    async def get_store_statistics(self) -> Dict[str, Any]:
        async with self._lock:
            total_obs = sum(len(h) for h in self._records.values())
            products_count = len(self._records)
            return {
                "store_type": "in_memory",
                "tracked_products": products_count,
                "total_observations": total_obs,
            }


class DiskJsonlHistoricalStore(BaseHistoricalStore):
    """
    Production disk-based JSON-Lines historical observation store.
    Files are grouped per product:
        data/history/observations/{marketplace}_{product_id}.jsonl
    """

    def __init__(self, base_dir: str = "data/history/observations"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _get_filepath(self, marketplace: MarketplaceType, product_id: str) -> Path:
        safe_mkt = marketplace.value if isinstance(marketplace, MarketplaceType) else str(marketplace)
        safe_pid = "".join(c for c in product_id if c.isalnum() or c in ("-", "_")).rstrip()
        return self.base_dir / f"{safe_mkt}_{safe_pid}.jsonl"

    async def save_observation(self, observation: HistoricalObservation) -> None:
        await self.save_observations([observation])

    async def save_observations(self, observations: List[HistoricalObservation]) -> int:
        if not observations:
            return 0

        saved = 0
        async with self._lock:
            # Group by file
            grouped: Dict[Path, List[HistoricalObservation]] = {}
            for obs in observations:
                path = self._get_filepath(obs.marketplace, obs.product_id)
                if path not in grouped:
                    grouped[path] = []
                grouped[path].append(obs)

            for path, obs_list in grouped.items():
                existing_ids: Set[str] = set()
                if path.exists():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    rec = json.loads(line)
                                    if "observation_id" in rec:
                                        existing_ids.add(rec["observation_id"])
                    except Exception:
                        pass

                to_write = [o for o in obs_list if o.observation_id not in existing_ids]
                if to_write:
                    with open(path, "a", encoding="utf-8") as f:
                        for o in to_write:
                            f.write(o.model_dump_json() + "\n")
                    saved += len(to_write)

        return saved

    async def get_all_observations_for_product(
        self, marketplace: MarketplaceType, product_id: str
    ) -> List[HistoricalObservation]:
        path = self._get_filepath(marketplace, product_id)
        if not path.exists():
            return []

        observations: List[HistoricalObservation] = []
        async with self._lock:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            observations.append(HistoricalObservation.model_validate(data))
            except Exception:
                return []

        observations.sort(key=lambda o: o.observed_at)
        return observations

    async def get_latest_observation(
        self, marketplace: MarketplaceType, product_id: str
    ) -> Optional[HistoricalObservation]:
        observations = await self.get_all_observations_for_product(marketplace, product_id)
        return observations[-1] if observations else None

    async def get_observations_in_window(
        self,
        marketplace: MarketplaceType,
        product_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> List[HistoricalObservation]:
        observations = await self.get_all_observations_for_product(marketplace, product_id)
        end = end_date or datetime.now(timezone.utc)
        return [obs for obs in observations if start_date <= obs.observed_at <= end]

    async def list_tracked_products(
        self, marketplace: Optional[MarketplaceType] = None
    ) -> List[Tuple[MarketplaceType, str]]:
        tracked: List[Tuple[MarketplaceType, str]] = []
        if not self.base_dir.exists():
            return []

        for p in self.base_dir.glob("*.jsonl"):
            stem = p.stem  # e.g. "daraz_100200"
            parts = stem.split("_", 1)
            if len(parts) == 2:
                try:
                    mkt = MarketplaceType(parts[0])
                    if marketplace is None or mkt == marketplace:
                        tracked.append((mkt, parts[1]))
                except ValueError:
                    continue
        return tracked

    async def delete_expired(self, cutoff_date: datetime, dry_run: bool = False) -> RetentionResult:
        total_inspected = 0
        expired_count = 0
        preserved_count = 0
        oldest_preserved: Optional[datetime] = None

        if not self.base_dir.exists():
            return RetentionResult(is_dry_run=dry_run)

        async with self._lock:
            files = list(self.base_dir.glob("*.jsonl"))
            for filepath in files:
                valid_lines: List[str] = []
                file_modified = False

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            line_str = line.strip()
                            if not line_str:
                                continue
                            total_inspected += 1
                            try:
                                data = json.loads(line_str)
                                obs_time_str = data.get("observed_at")
                                obs_time = (
                                    datetime.fromisoformat(obs_time_str.replace("Z", "+00:00"))
                                    if obs_time_str
                                    else None
                                )

                                if obs_time and obs_time < cutoff_date:
                                    expired_count += 1
                                    file_modified = True
                                else:
                                    preserved_count += 1
                                    valid_lines.append(line_str)
                                    if obs_time and (oldest_preserved is None or obs_time < oldest_preserved):
                                        oldest_preserved = obs_time
                            except Exception:
                                valid_lines.append(line_str)
                                preserved_count += 1

                    if not dry_run and file_modified:
                        if valid_lines:
                            with open(filepath, "w", encoding="utf-8") as f:
                                for v in valid_lines:
                                    f.write(v + "\n")
                        else:
                            filepath.unlink(missing_ok=True)
                except Exception:
                    continue

        deleted_count = 0 if dry_run else expired_count
        return RetentionResult(
            total_inspected=total_inspected,
            expired_count=expired_count,
            deleted_count=deleted_count,
            preserved_count=preserved_count,
            oldest_preserved_date=oldest_preserved,
            is_dry_run=dry_run,
        )

    async def get_store_statistics(self) -> Dict[str, Any]:
        total_obs = 0
        files_count = 0
        total_bytes = 0

        if self.base_dir.exists():
            for p in self.base_dir.glob("*.jsonl"):
                files_count += 1
                try:
                    total_bytes += p.stat().st_size
                    with open(p, "r", encoding="utf-8") as f:
                        total_obs += sum(1 for line in f if line.strip())
                except Exception:
                    pass

        return {
            "store_type": "disk_jsonl",
            "base_dir": str(self.base_dir),
            "tracked_products": files_count,
            "total_observations": total_obs,
            "total_size_bytes": total_bytes,
        }
