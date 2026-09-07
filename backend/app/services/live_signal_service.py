import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from threading import Lock
from datetime import datetime, timezone

from backend.app.schemas.signals import LiveSignalItem, LiveSignalsResponse
from backend.app.schemas.daraz import DarazProductItem, DarazSearchResponse
from backend.app.services.daraz_service import DarazService

logger = logging.getLogger(__name__)

class LiveSignalService:
    """
    Service responsible for generating real-time, factual market signals from connected data sources.
    Extracts high-fidelity signals (pricing, ratings, merchant metrics, inventory availability)
    from live Daraz marketplace products without fabricating demo data or fake percentages.
    """

    DEFAULT_DISCOVERY_QUERIES = ["wireless earbuds", "laptop", "smart watch", "pen", "gaming keyboard"]

    def __init__(
        self,
        daraz_service: Optional[DarazService] = None,
        cache_ttl_seconds: int = 60
    ):
        self.daraz_service = daraz_service
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, Tuple[LiveSignalsResponse, float]] = {}
        self._cache_lock = Lock()

    def _get_from_cache(self, key: str) -> Optional[LiveSignalsResponse]:
        with self._cache_lock:
            if key in self._cache:
                val, expiry = self._cache[key]
                if time.time() < expiry:
                    return val
                del self._cache[key]
        return None

    def _set_cache(self, key: str, val: LiveSignalsResponse, ttl: int) -> None:
        with self._cache_lock:
            self._cache[key] = (val, time.time() + ttl)

    def generate_signals_from_daraz_product(self, product: DarazProductItem) -> List[LiveSignalItem]:
        """
        Extracts factual, platform-neutral signal items from a single normalized Daraz product.
        """
        signals: List[LiveSignalItem] = []
        clean_name = product.name.strip()
        # Shorten long titles for clean ticker display
        display_name = clean_name if len(clean_name) <= 65 else clean_name[:62] + "..."
        now_iso = datetime.now(timezone.utc).isoformat()
        prod_id = f"daraz_{product.product_id}" if product.product_id else None

        # 1. Price Signal
        if product.price > 0:
            price_formatted = f"PKR {int(product.price):,}" if product.price.is_integer() else f"PKR {product.price:,.2f}"
            discount_suffix = f" ({product.discount_label})" if product.discount_label else ""
            signals.append(
                LiveSignalItem(
                    id=f"sig_price_{product.product_id}",
                    type="PRICE",
                    platform="daraz",
                    title="PRICE UPDATE",
                    description=f"{display_name} • {price_formatted}{discount_suffix}",
                    product_id=prod_id,
                    product_name=clean_name,
                    signal_value=price_formatted,
                    timestamp=now_iso,
                    source="daraz.pk",
                    metadata={"price": product.price, "currency": product.currency, "discount": product.discount}
                )
            )

        # 2. Rating / Acclaim Signal
        if product.rating > 0:
            rating_text = f"{product.rating:.1f}★"
            review_text = f" ({product.review_count:,} reviews)" if product.review_count > 0 else ""
            signals.append(
                LiveSignalItem(
                    id=f"sig_rating_{product.product_id}",
                    type="RATING",
                    platform="daraz",
                    title="BUYER ACCLAIM",
                    description=f"{display_name} • {rating_text}{review_text}",
                    product_id=prod_id,
                    product_name=clean_name,
                    signal_value=rating_text,
                    timestamp=now_iso,
                    source="daraz.pk",
                    metadata={"rating": product.rating, "review_count": product.review_count}
                )
            )

        # 3. Seller Signal
        if product.seller_name and product.seller_name != "No Brand":
            signals.append(
                LiveSignalItem(
                    id=f"sig_seller_{product.product_id}",
                    type="SELLER",
                    platform="daraz",
                    title="MERCHANT TRUST",
                    description=f"{product.seller_name} listed {display_name}",
                    product_id=prod_id,
                    product_name=clean_name,
                    signal_value=product.seller_name,
                    timestamp=now_iso,
                    source="daraz.pk",
                    metadata={"seller_name": product.seller_name, "seller_id": product.seller_id}
                )
            )

        # 4. Supply / Availability Signal
        if product.in_stock:
            loc_suffix = f" • {product.location}" if product.location else ""
            signals.append(
                LiveSignalItem(
                    id=f"sig_stock_{product.product_id}",
                    type="AVAILABILITY",
                    platform="daraz",
                    title="MARKET SUPPLY",
                    description=f"{display_name} • In Stock{loc_suffix}",
                    product_id=prod_id,
                    product_name=clean_name,
                    signal_value="In Stock",
                    timestamp=now_iso,
                    source="daraz.pk",
                    metadata={"in_stock": True, "location": product.location}
                )
            )

        return signals

    def get_live_signals(self, limit: int = 20) -> LiveSignalsResponse:
        """
        Aggregates live market signals across connected sources (Daraz, YouTube, TikTok, etc.).
        Returns genuine signals without fabricating data.
        """
        cache_key = f"live_signals_feed:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        all_signals: List[LiveSignalItem] = []

        # Ingest from Daraz if service available
        if self.daraz_service:
            try:
                # 1. First extract signals from any already-cached searches
                with self.daraz_service._cache_lock:
                    for _ck, (cached_res, exp) in list(self.daraz_service._cache.items()):
                        if exp > time.time() and isinstance(cached_res, DarazSearchResponse) and cached_res.products:
                            for p in cached_res.products[:4]:
                                prod_signals = self.generate_signals_from_daraz_product(p)
                                all_signals.extend(prod_signals)

                # 2. If we need more signals, query discovery queries (e.g. "wireless earbuds")
                if len(all_signals) < limit:
                    for q in self.DEFAULT_DISCOVERY_QUERIES[:2]:
                        try:
                            search_res = self.daraz_service.search_products(query=q, page=1)
                            if search_res and search_res.products:
                                for p in search_res.products[:5]:
                                    prod_signals = self.generate_signals_from_daraz_product(p)
                                    all_signals.extend(prod_signals)
                                if len(all_signals) >= limit:
                                    break
                        except Exception as err:
                            logger.warning(f"Error querying Daraz products for query '{q}': {err}")

            except Exception as e:
                logger.error(f"LiveSignalService Daraz ingestion error: {e}")

        # Interleave or diversify signals so different types alternate
        diversified_signals: List[LiveSignalItem] = []
        seen_types: Dict[str, int] = {}
        seen_ids = set()

        for s in all_signals:
            if s.id in seen_ids:
                continue
            seen_ids.add(s.id)
            seen_types[s.type] = seen_types.get(s.type, 0) + 1
            diversified_signals.append(s)
            if len(diversified_signals) >= limit:
                break

        response = LiveSignalsResponse(
            signals=diversified_signals,
            total=len(diversified_signals),
            generated_at=datetime.now(timezone.utc).isoformat()
        )

        self._set_cache(cache_key, response, ttl=self.cache_ttl_seconds)
        return response
