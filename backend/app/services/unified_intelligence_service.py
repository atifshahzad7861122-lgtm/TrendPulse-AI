import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
import logging

from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, ProductMatchCandidate, ProductMatchAudit,
    MarketplaceProduct, ShopifyProduct
)
from backend.app.schemas.intelligence import (
    UnifiedProductItem, PlatformListingItem, PriceComparisonItem, PlatformComparisonItem,
    UnifiedProductDetailResponse, UnifiedProductListResponse, UnifiedHistoricalPoint,
    UnifiedProductHistoryResponse, UnifiedSearchResponse
)
from backend.app.repositories.base import (
    UnifiedProductRepository, MarketplaceProductRepository, ShopifyRepository, TaxonomyRepository
)
from backend.app.services.normalization.product_normalizer import ProductNormalizer
from backend.app.services.matching.product_matcher import ProductMatcher, MatchDecision
from backend.app.services.agents.data_quality.agent import DataQualityAgent
from backend.app.services.agents.categorization import ProductCategorizationAgent
from backend.app.services.agents.entity_matching import ProductEntityMatchingAgent

logger = logging.getLogger("trendpulse.unified_intelligence")

class UnifiedProductIntelligenceService:
    """
    Core Product Intelligence service coordinating cross-platform ingestion,
    data quality validation gating (Agent 1), taxonomy classification (Agent 2),
    entity matching & deduplication (Agent 3), canonical entity management, and multi-platform analytics.
    """

    def __init__(
        self,
        unified_repo: UnifiedProductRepository,
        daraz_repo: Optional[MarketplaceProductRepository] = None,
        shopify_repo: Optional[ShopifyRepository] = None,
        data_quality_agent: Optional[DataQualityAgent] = None,
        categorization_agent: Optional[ProductCategorizationAgent] = None,
        taxonomy_repo: Optional[TaxonomyRepository] = None,
        entity_matching_agent: Optional[ProductEntityMatchingAgent] = None
    ):
        self.unified_repo = unified_repo
        self.daraz_repo = daraz_repo
        self.shopify_repo = shopify_repo
        self.data_quality_agent = data_quality_agent
        self.categorization_agent = categorization_agent
        self.taxonomy_repo = taxonomy_repo
        self.entity_matching_agent = entity_matching_agent




    # --------------------------------------------------------------------------
    # Formatting Helpers
    # --------------------------------------------------------------------------

    def _format_price(self, price: float, currency: str = "USD") -> str:
        curr = (currency or "USD").upper()
        if curr in ["PKR", "RS", "RS."]:
            return f"PKR {price:,.0f}"
        elif curr == "EUR":
            return f"€{price:,.2f}"
        elif curr == "GBP":
            return f"£{price:,.2f}"
        else:
            return f"${price:,.2f}"

    def _format_price_range(self, listings: List[ProductPlatformListing]) -> Tuple[float, float, float, str, str]:
        """Calculates lowest, highest, average price, primary currency, and formatted range string."""
        if not listings:
            return 0.0, 0.0, 0.0, "USD", "N/A"
        prices = [l.price for l in listings if l.price > 0]
        if not prices:
            prices = [0.0]
        lowest = min(prices)
        highest = max(prices)
        avg = round(sum(prices) / len(prices), 2)
        primary_curr = listings[0].currency or "USD"

        # Check if multiple currencies exist
        currencies = list(set(l.currency for l in listings if l.currency))
        if len(currencies) > 1:
            range_str = " / ".join(f"{self._format_price(l.price, l.currency)}" for l in listings[:3])
        elif lowest == highest:
            range_str = self._format_price(lowest, primary_curr)
        else:
            range_str = f"{self._format_price(lowest, primary_curr)} - {self._format_price(highest, primary_curr)}"

        return lowest, highest, avg, primary_curr, range_str

    def _build_unified_product_item(self, prod: UnifiedProduct) -> UnifiedProductItem:
        listings = self.unified_repo.list_listings_for_product(prod.unified_product_id)
        lowest, highest, avg, primary_curr, price_range = self._format_price_range(listings)

        ratings = [l.rating for l in listings if l.rating > 0]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
        total_reviews = sum(l.review_count for l in listings)
        platforms = sorted(list(set(l.platform for l in listings)))
        if not platforms:
            platforms = ["Daraz"]

        scores = [l.completeness_score for l in listings if l.completeness_score > 0]
        completeness = round(sum(scores) / len(scores), 2) if scores else 1.0

        # Check taxonomy assignment if available
        tax_path = [prod.category] if prod.category else []
        tax_attrs = {}
        conf = 1.0
        method = "deterministic"
        needs_rev = False

        if self.taxonomy_repo:
            assignment = self.taxonomy_repo.get_assignment_by_unified_product_id(prod.unified_product_id)
            if assignment:
                tax_path = assignment.taxonomy_path
                tax_attrs = assignment.attributes
                conf = assignment.confidence
                method = assignment.classification_method
                needs_rev = assignment.needs_review

        return UnifiedProductItem(
            id=prod.id,
            unified_product_id=prod.unified_product_id,
            canonical_name=prod.canonical_name,
            normalized_name=prod.normalized_name,
            brand=prod.brand,
            category=prod.category,
            subcategory=prod.subcategory,
            product_type=prod.product_type,
            taxonomy_path=tax_path,
            attributes=tax_attrs,
            category_confidence=conf,
            classification_method=method,
            needs_review=needs_rev,
            description=prod.description,
            primary_image=prod.primary_image or (listings[0].image_url if listings else None),
            identifiers=prod.identifiers,
            platforms=platforms,
            platform_count=len(platforms),
            listings_count=len(listings),
            lowest_price=lowest,
            highest_price=highest,
            average_price=avg,
            primary_currency=primary_curr,
            price_range_formatted=price_range,
            avg_rating=avg_rating,
            total_reviews=total_reviews,
            completeness_score=completeness,
            first_seen_at=prod.first_seen_at,
            last_seen_at=prod.last_seen_at,
            last_synced_at=prod.updated_at
        )


    # --------------------------------------------------------------------------
    # Ingestion & Matching Pipeline
    # --------------------------------------------------------------------------

    def match_and_upsert_listing(
        self,
        platform: str,
        platform_product_id: str,
        title: str,
        price: float,
        product_url: str,
        currency: str = "USD",
        original_price: Optional[float] = None,
        discount_percentage: float = 0.0,
        discount_label: Optional[str] = None,
        seller_name: Optional[str] = None,
        vendor: Optional[str] = None,
        rating: float = 0.0,
        review_count: int = 0,
        available: bool = True,
        image_url: Optional[str] = None,
        source_provider: str = "direct",
        category: Optional[str] = None,
        store_domain: Optional[str] = None,
        identifiers: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        allow_llm: bool = True
    ) -> Tuple[UnifiedProduct, ProductPlatformListing, MatchDecision]:
        """
        Main ingestion entrypoint:
          1. Normalizes incoming raw product
          2. Evaluates deterministic matching against existing catalog
          3. Links to existing UnifiedProduct if confident match, or creates a new UnifiedProduct
          4. Upserts ProductPlatformListing
          5. Records MatchAudit or MatchCandidate
        """
        identifiers = identifiers or {}
        raw_dict = {
            "title": title,
            "vendor": vendor or seller_name,
            "brand": identifiers.get("brand"),
            "price": price,
            "product_url": product_url,
            "image_url": image_url,
            "rating": rating
        }

        # Step 0: Data Quality & Validation Agent Gate
        validation_payload = {
            "product_id": platform_product_id,
            "title": title,
            "vendor": vendor or seller_name,
            "seller_name": seller_name,
            "brand": identifiers.get("brand"),
            "price": price,
            "original_price": original_price,
            "currency": currency,
            "rating": rating,
            "review_count": review_count,
            "available": available,
            "product_url": product_url,
            "image_url": image_url,
            "platform": platform,
            "source_provider": source_provider,
            "category": category,
            "identifiers": identifiers,
            "raw_data": raw_data
        }

        quality_score = 100.0
        if self.data_quality_agent:
            dq_result = self.data_quality_agent.validate_product(
                payload=validation_payload,
                platform=platform,
                source_provider=source_provider,
                allow_llm=allow_llm,
                save_result=True
            )
            if dq_result.classification == "rejected":
                logger.warning(
                    f"[DataQualityAgent Gate] REJECTED listing {platform}:{platform_product_id} "
                    f"(score: {dq_result.overall_score}) - Issues: {[i.rule_name for i in dq_result.issues]}"
                )
                rejection_decision = MatchDecision(
                    is_match=False,
                    confidence=0.0,
                    method="data_quality_rejected",
                    status="unmatched",
                    reasons=[f"Data quality rejected: {i.message}" for i in dq_result.issues]
                )
                return None, None, rejection_decision
            quality_score = dq_result.overall_score

        # Step 1: Normalize
        norm = ProductNormalizer.normalize_product(raw_dict, platform=platform)
        if quality_score < 100.0:
            norm["completeness_score"] = round(quality_score / 100.0, 2)
        now = datetime.now(timezone.utc)


        # Step 2: Check if this exact listing already exists
        existing_listing = self.unified_repo.get_platform_listing(
            platform=platform,
            platform_product_id=platform_product_id,
            store_domain=store_domain
        )

        matched_unified_product: Optional[UnifiedProduct] = None
        match_decision: Optional[MatchDecision] = None

        if existing_listing:
            # Re-associate with existing unified product
            matched_unified_product = self.unified_repo.get_unified_product(existing_listing.unified_product_id)
            match_decision = MatchDecision(
                is_match=True,
                confidence=1.0,
                method="existing_listing_re_sync",
                status="matched",
                reasons=[f"Existing listing found for {platform}:{platform_product_id}"]
            )

        # Step 3: Search candidates across catalog if not already linked
        if not matched_unified_product:
            if self.entity_matching_agent:
                # Agent 3: Product Entity Matching & Deduplication Agent
                agent_payload = {
                    "product_name": title,
                    "title": title,
                    "brand": identifiers.get("brand") or norm.get("brand"),
                    "category": category or norm.get("category"),
                    "subcategory": norm.get("subcategory") or (raw_data or {}).get("subcategory"),
                    "product_type": norm.get("product_type") or (raw_data or {}).get("product_type"),
                    "description": description,
                    "platform": platform,
                    "platform_product_id": platform_product_id,
                    "store_domain": store_domain,
                    "identifiers": identifiers,
                    "attributes": (raw_data or {}).get("attributes", {}),
                    "price": price,
                    "currency": currency,
                    "image_url": image_url
                }
                pmd_decision, matched_unified_product = self.entity_matching_agent.match_listing(
                    payload=agent_payload,
                    allow_llm=allow_llm
                )
                match_decision = MatchDecision(
                    is_match=(pmd_decision.decision in ["EXACT_MATCH", "HIGH_CONFIDENCE_MATCH", "PROBABLE_MATCH", "VARIANT"]),
                    confidence=pmd_decision.confidence,
                    method=pmd_decision.match_method,
                    status="matched" if pmd_decision.decision in ["EXACT_MATCH", "HIGH_CONFIDENCE_MATCH"] else ("probable" if pmd_decision.decision in ["PROBABLE_MATCH", "NEEDS_REVIEW"] else "rejected"),
                    candidate_id=matched_unified_product.unified_product_id if matched_unified_product else None,
                    reasons=pmd_decision.reasons
                )
            else:
                all_unified = self.unified_repo.list_unified_products(limit=500)
                best_decision: Optional[MatchDecision] = None
                best_candidate: Optional[UnifiedProduct] = None

                for candidate in all_unified:
                    cand_norm = {
                        "canonical_name": candidate.canonical_name,
                        "normalized_name": candidate.normalized_name,
                        "brand": candidate.brand,
                        "model_number": candidate.identifiers.get("model_number"),
                        "tokens": set(candidate.canonical_name.lower().split())
                    }
                    decision = ProductMatcher.evaluate_match(
                        item_norm=norm,
                        candidate_norm=cand_norm,
                        item_identifiers=identifiers,
                        candidate_identifiers=candidate.identifiers
                    )

                    if decision.is_match:
                        if best_decision is None or decision.confidence > best_decision.confidence:
                            best_decision = decision
                            best_candidate = candidate
                            decision.candidate_id = candidate.unified_product_id
                    elif decision.status == "probable":
                        # Record candidate for audit/review
                        cand_rec = ProductMatchCandidate(
                            id=f"cand_{uuid.uuid4().hex[:12]}",
                            unified_product_id=candidate.unified_product_id,
                            candidate_unified_id=candidate.unified_product_id,
                            platform=platform,
                            platform_product_id=platform_product_id,
                            confidence_score=decision.confidence,
                            method=decision.method,
                            status="probable",
                            reasons=decision.reasons,
                            created_at=now
                        )
                        self.unified_repo.record_match_candidate(cand_rec)

                if best_candidate and best_decision and best_decision.is_match:
                    matched_unified_product = best_candidate
                    match_decision = best_decision
                else:
                    match_decision = MatchDecision(
                        is_match=False,
                        confidence=0.0,
                        method="new_canonical_product",
                        status="matched",
                        reasons=["Created new canonical unified product"]
                    )


        # Step 4: Create or update UnifiedProduct
        if not matched_unified_product:
            # Generate deterministic unified ID
            up_id = f"up_{uuid.uuid4().hex[:12]}"
            unified_prod = UnifiedProduct(
                id=up_id,
                unified_product_id=up_id,
                canonical_name=norm["canonical_name"],
                normalized_name=norm["normalized_name"],
                brand=norm["brand"],
                category=category,
                description=description,
                primary_image=image_url,
                identifiers={
                    **identifiers,
                    "model_number": norm.get("model_number"),
                    "brand": norm.get("brand")
                },
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now
            )
            matched_unified_product = self.unified_repo.upsert_unified_product(unified_prod)
        else:
            # Update last_seen_at & metadata
            matched_unified_product.last_seen_at = now
            if not matched_unified_product.primary_image and image_url:
                matched_unified_product.primary_image = image_url
            if not matched_unified_product.category and category:
                matched_unified_product.category = category
            if identifiers:
                matched_unified_product.identifiers.update(identifiers)
            matched_unified_product = self.unified_repo.upsert_unified_product(matched_unified_product)

        # Step 5: Upsert Platform Listing
        listing_id = existing_listing.id if existing_listing else f"list_{uuid.uuid4().hex[:12]}"
        listing = ProductPlatformListing(
            id=listing_id,
            unified_product_id=matched_unified_product.unified_product_id,
            platform=platform,
            platform_product_id=platform_product_id,
            store_domain=store_domain,
            product_url=product_url,
            title=title,
            normalized_title=norm["canonical_name"],
            price=price,
            original_price=original_price,
            currency=currency,
            discount_percentage=discount_percentage,
            discount_label=discount_label,
            seller_name=seller_name,
            vendor=vendor,
            rating=rating,
            review_count=review_count,
            available=available,
            image_url=image_url,
            source_provider=source_provider,
            last_synced_at=now,
            completeness_score=norm["completeness_score"],
            raw_data=raw_data or {},
            created_at=existing_listing.created_at if existing_listing else now,
            updated_at=now
        )
        saved_listing = self.unified_repo.upsert_platform_listing(listing)

        # Step 5b: Agent 2 Product Categorization & Taxonomy Gate
        if self.categorization_agent:
            cat_payload = {
                "unified_product_id": matched_unified_product.unified_product_id,
                "product_id": platform_product_id,
                "product_name": title,
                "description": description or "",
                "brand": norm.get("brand") or identifiers.get("brand") or vendor or seller_name,
                "original_category": category,
                "tags": norm.get("tags") or [],
                "attributes": identifiers or {},
                "platform": platform,
                "source_provider": source_provider
            }
            try:
                cat_assignment = self.categorization_agent.classify_product(
                    payload=cat_payload,
                    unified_product_id=matched_unified_product.unified_product_id,
                    allow_llm=allow_llm,
                    save_result=True
                )
                if cat_assignment and cat_assignment.confidence >= 0.50:
                    matched_unified_product.category = cat_assignment.category
                    matched_unified_product.subcategory = cat_assignment.subcategory
                    matched_unified_product.product_type = cat_assignment.product_type
                    if cat_assignment.brand:
                        matched_unified_product.brand = cat_assignment.brand
                    self.unified_repo.upsert_unified_product(matched_unified_product)
            except Exception as e:
                logger.warning(f"Failed to execute Agent 2 categorization: {e}")

        # Step 6: Record Match Audit

        if match_decision and match_decision.method != "existing_listing_re_sync":
            audit = ProductMatchAudit(
                id=f"audit_{uuid.uuid4().hex[:12]}",
                unified_product_id=matched_unified_product.unified_product_id,
                platform=platform,
                platform_product_id=platform_product_id,
                matching_method=match_decision.method,
                matching_confidence=match_decision.confidence,
                matched_at=now,
                details={
                    "reasons": match_decision.reasons,
                    "normalized_name": norm["normalized_name"],
                    "brand": norm["brand"]
                },
                created_at=now
            )
            self.unified_repo.record_match_audit(audit)

        return matched_unified_product, saved_listing, match_decision

    def ingest_daraz_product(self, prod: Any) -> Tuple[UnifiedProduct, ProductPlatformListing, MatchDecision]:
        """Ingests a real Daraz product into Unified Intelligence."""
        p_id = getattr(prod, "product_id", getattr(prod, "item_id", ""))
        title = getattr(prod, "product_name", getattr(prod, "name", getattr(prod, "title", "")))
        price = float(getattr(prod, "price", 0.0))
        orig_price = getattr(prod, "original_price", None)
        orig_price_float = float(orig_price) if orig_price is not None else None
        discount = float(getattr(prod, "discount_percentage", 0.0))
        discount_label = getattr(prod, "discount_label", None)
        seller = getattr(prod, "seller_name", None)
        if not seller and hasattr(prod, "seller") and prod.seller:
            seller = getattr(prod.seller, "name", getattr(prod.seller, "seller_name", None))
        rating = float(getattr(prod, "rating", 0.0))
        reviews = int(getattr(prod, "review_count", 0))
        url = getattr(prod, "product_url", "")
        img = getattr(prod, "image_url", getattr(prod, "main_image", None))
        cat = getattr(prod, "category", None)
        raw = getattr(prod, "raw_data", {})

        return self.match_and_upsert_listing(
            platform="Daraz",
            platform_product_id=str(p_id),
            title=title,
            price=price,
            product_url=url or f"https://www.daraz.pk/products/-i{p_id}.html",
            currency="PKR",
            original_price=orig_price_float,
            discount_percentage=discount,
            discount_label=discount_label,
            seller_name=seller,
            rating=rating,
            review_count=reviews,
            available=True,
            image_url=img,
            source_provider=getattr(prod, "source_provider", "parse_daraz_api"),
            category=cat,
            raw_data=raw if isinstance(raw, dict) else {}
        )

    def ingest_shopify_product(self, prod: ShopifyProduct) -> Tuple[UnifiedProduct, ProductPlatformListing, MatchDecision]:
        """Ingests a real Shopify product into Unified Intelligence."""
        return self.match_and_upsert_listing(
            platform="Shopify",
            platform_product_id=prod.product_id,
            store_domain=prod.store_domain,
            title=prod.title,
            price=prod.price,
            product_url=prod.product_url,
            currency=prod.currency or "USD",
            original_price=prod.compare_at_price,
            discount_percentage=prod.discount_percentage,
            discount_label=prod.discount_label,
            vendor=prod.vendor,
            rating=prod.rating,
            review_count=prod.review_count,
            available=prod.available,
            image_url=prod.image_url,
            source_provider=prod.source_provider,
            category=prod.category or prod.product_type,
            raw_data=prod.raw_data or {}
        )

    # --------------------------------------------------------------------------
    # Catalog Queries & Detail Views
    # --------------------------------------------------------------------------

    def list_products(
        self,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        platform: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        available: Optional[bool] = None,
        min_rating: Optional[float] = None,
        sort_by: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> UnifiedProductListResponse:
        offset = (page - 1) * limit
        items = self.unified_repo.list_unified_products(
            category=category,
            brand=brand,
            platform=platform,
            search=search,
            min_price=min_price,
            max_price=max_price,
            available=available,
            min_rating=min_rating,
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )
        total = self.unified_repo.count_unified_products(
            category=category,
            brand=brand,
            platform=platform,
            search=search,
            min_price=min_price,
            max_price=max_price,
            available=available,
            min_rating=min_rating
        )

        built_items = [self._build_unified_product_item(p) for p in items]
        total_pages = max(1, (total + limit - 1) // limit)

        return UnifiedProductListResponse(
            items=built_items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            filters_applied={
                "category": category,
                "brand": brand,
                "platform": platform,
                "search": search,
                "min_price": min_price,
                "max_price": max_price,
                "available": available,
                "min_rating": min_rating,
                "sort_by": sort_by
            }
        )

    def get_product_detail(self, unified_product_id: str) -> Optional[UnifiedProductDetailResponse]:
        prod = self.unified_repo.get_unified_product(unified_product_id)
        if not prod:
            return None

        item = self._build_unified_product_item(prod)
        listings = self.unified_repo.list_listings_for_product(unified_product_id)

        # Platform Listings
        listing_items = []
        price_comparison = []
        platform_comparison = []

        for l in listings:
            p_formatted = self._format_price(l.price, l.currency)
            orig_formatted = self._format_price(l.original_price, l.currency) if l.original_price else None

            listing_items.append(PlatformListingItem(
                id=l.id,
                unified_product_id=l.unified_product_id,
                platform=l.platform,
                platform_product_id=l.platform_product_id,
                store_domain=l.store_domain,
                product_url=l.product_url,
                title=l.title,
                normalized_title=l.normalized_title,
                price=l.price,
                price_formatted=p_formatted,
                original_price=l.original_price,
                original_price_formatted=orig_formatted,
                currency=l.currency,
                discount_percentage=l.discount_percentage,
                discount_label=l.discount_label,
                seller_name=l.seller_name,
                vendor=l.vendor,
                rating=l.rating,
                review_count=l.review_count,
                available=l.available,
                image_url=l.image_url,
                source_provider=l.source_provider,
                last_synced_at=l.last_synced_at,
                completeness_score=l.completeness_score,
                raw_data=l.raw_data
            ))

            price_comparison.append(PriceComparisonItem(
                platform=l.platform,
                store_domain=l.store_domain,
                price=l.price,
                price_formatted=p_formatted,
                original_price=l.original_price,
                original_price_formatted=orig_formatted,
                currency=l.currency,
                discount_percentage=l.discount_percentage,
                discount_label=l.discount_label,
                available=l.available,
                seller_or_vendor=l.vendor or l.seller_name,
                product_url=l.product_url,
                last_updated=l.last_synced_at
            ))

            platform_comparison.append(PlatformComparisonItem(
                platform=l.platform,
                store_domain=l.store_domain,
                title=l.title,
                price=l.price,
                price_formatted=p_formatted,
                currency=l.currency,
                discount_percentage=l.discount_percentage,
                rating=l.rating,
                review_count=l.review_count,
                available=l.available,
                seller_name=l.seller_name,
                vendor=l.vendor,
                product_url=l.product_url,
                image_url=l.image_url,
                source_provider=l.source_provider
            ))

        audit = self.unified_repo.get_match_audit(unified_product_id)

        return UnifiedProductDetailResponse(
            unified_product=item,
            platform_listings=listing_items,
            price_comparison=price_comparison,
            platform_comparison=platform_comparison,
            match_audit=audit.model_dump(mode="json") if audit else None
        )

    def get_product_history(self, unified_product_id: str) -> Optional[UnifiedProductHistoryResponse]:
        """Aggregates real historical observations across linked platform snapshots."""
        prod = self.unified_repo.get_unified_product(unified_product_id)
        if not prod:
            return None

        listings = self.unified_repo.list_listings_for_product(unified_product_id)
        timeline: List[UnifiedHistoricalPoint] = []
        platforms = set()

        for l in listings:
            platforms.add(l.platform)
            if l.platform.lower() == "daraz" and self.daraz_repo:
                try:
                    snaps = self.daraz_repo.get_snapshots("daraz", l.platform_product_id)
                    for s in snaps:
                        timeline.append(UnifiedHistoricalPoint(
                            timestamp=s.observed_at,
                            platform="Daraz",
                            store_domain="daraz.pk",
                            price=s.price,
                            currency="PKR",
                            available=s.stock_status != "out_of_stock",
                            rating=s.rating,
                            review_count=s.review_count,
                            source_provider=s.source_provider
                        ))
                except Exception:
                    pass
            elif l.platform.lower() == "shopify" and self.shopify_repo:
                try:
                    snaps = self.shopify_repo.get_snapshots(l.store_domain or "", l.platform_product_id)
                    for s in snaps:
                        timeline.append(UnifiedHistoricalPoint(
                            timestamp=s.observed_at,
                            platform="Shopify",
                            store_domain=s.store_domain,
                            price=s.price,
                            currency=l.currency or "USD",
                            available=s.available,
                            rating=s.rating,
                            review_count=s.review_count,
                            source_provider=s.source_provider
                        ))
                except Exception:
                    pass

            # If no snapshots exist yet, add current observation
            if not timeline:
                timeline.append(UnifiedHistoricalPoint(
                    timestamp=l.last_synced_at,
                    platform=l.platform,
                    store_domain=l.store_domain,
                    price=l.price,
                    currency=l.currency,
                    available=l.available,
                    rating=l.rating,
                    review_count=l.review_count,
                    source_provider=l.source_provider
                ))

        timeline.sort(key=lambda x: x.timestamp)

        return UnifiedProductHistoryResponse(
            unified_product_id=prod.unified_product_id,
            canonical_name=prod.canonical_name,
            timeline=timeline,
            total_observations=len(timeline),
            platforms=sorted(list(platforms))
        )

    def search(self, query: str, page: int = 1, limit: int = 50) -> UnifiedSearchResponse:
        res = self.list_products(search=query, page=page, limit=limit)
        return UnifiedSearchResponse(
            query=query,
            total_matches=res.total,
            items=res.items,
            page=page,
            limit=limit
        )
