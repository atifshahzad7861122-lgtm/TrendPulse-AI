from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_data_quality_repository
from backend.app.repositories.base import DataQualityRepository
from backend.app.schemas.data_quality import (
    PublicDataQualityProductItem,
    PublicDataQualityFeedResponse,
    PublicDataQualityStatsResponse,
    PublicDataQualityHistoryResponse
)

router = APIRouter()

@router.get(
    "/rejected",
    response_model=PublicDataQualityFeedResponse,
    summary="Public Feed of Rejected Products",
    description="Public transparent audit feed of real marketplace products that failed Data Quality checks. Excludes sensitive system data."
)
def get_public_rejected_products(
    platform: Optional[str] = Query(None, description="Filter by platform (e.g. daraz, shopify, amazon, ebay)"),
    provider: Optional[str] = Query(None, description="Filter by source provider (e.g. daraz_direct, shopify_official)"),
    category: Optional[str] = Query(None, description="Filter by original or normalized category"),
    rejection_reason: Optional[str] = Query(None, description="Filter by rejection reason keyword"),
    search: Optional[str] = Query(None, description="Search by product name, product ID, or category"),
    min_score: Optional[float] = Query(None, description="Minimum quality score"),
    max_score: Optional[float] = Query(None, description="Maximum quality score"),
    date_from: Optional[datetime] = Query(None, description="Validated after timestamp"),
    date_to: Optional[datetime] = Query(None, description="Validated before timestamp"),
    sort_by: Optional[str] = Query("validated_at_desc", description="Sort order: validated_at_desc, validated_at_asc, score_asc, score_desc, price_asc, price_desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    repo: DataQualityRepository = Depends(get_data_quality_repository)
):
    offset = (page - 1) * page_size
    items, total = repo.get_public_feed(
        platform=platform,
        provider=provider,
        classification="rejected",
        normalized_category=category,
        rejection_reason=rejection_reason,
        search=search,
        min_score=min_score,
        max_score=max_score,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        limit=page_size,
        offset=offset
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    formatted_items = [
        PublicDataQualityProductItem(
            id=item.id,
            product_id=item.product_id or "",
            product_name=item.product_name,
            platform=item.platform,
            provider=item.provider,
            data_quality_category=item.data_quality_category or "Data Quality Issues",
            original_category=item.original_category,
            normalized_category=item.normalized_category or "Unknown",
            price=item.price,
            currency=item.currency,
            rating=item.rating,
            review_count=item.review_count,
            availability=item.availability,
            image=item.image,
            product_url=item.product_url,
            quality_score=item.quality_score,
            classification=item.classification,
            public_status=item.public_status,
            issues=item.issues,
            warnings=item.warnings,
            rejection_reasons=item.rejection_reasons,
            missing_fields=item.missing_fields,
            invalid_fields=item.invalid_fields,
            suspicious_fields=item.suspicious_fields,
            llm_used=item.llm_used,
            last_validated_time=item.last_validated_time
        )
        for item in items
    ]

    return PublicDataQualityFeedResponse(
        items=formatted_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get(
    "/feed",
    response_model=PublicDataQualityFeedResponse,
    summary="Public Multi-Status Validation Feed",
    description="Public transparent audit feed showing real marketplace records across validation statuses (valid, warning, review, rejected)."
)
def get_public_validation_feed(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    provider: Optional[str] = Query(None, description="Filter by source provider"),
    classification: Optional[str] = Query(None, description="Filter by classification (valid, valid_with_warnings, needs_review, rejected, all)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    rejection_reason: Optional[str] = Query(None, description="Filter by rejection reason"),
    search: Optional[str] = Query(None, description="Search by product name, product ID, or category"),
    min_score: Optional[float] = Query(None, description="Minimum quality score"),
    max_score: Optional[float] = Query(None, description="Maximum quality score"),
    date_from: Optional[datetime] = Query(None, description="Validated after timestamp"),
    date_to: Optional[datetime] = Query(None, description="Validated before timestamp"),
    sort_by: Optional[str] = Query("validated_at_desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    repo: DataQualityRepository = Depends(get_data_quality_repository)
):
    offset = (page - 1) * page_size
    items, total = repo.get_public_feed(
        platform=platform,
        provider=provider,
        classification=classification if classification != "all" else None,
        normalized_category=category,
        rejection_reason=rejection_reason,
        search=search,
        min_score=min_score,
        max_score=max_score,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        limit=page_size,
        offset=offset
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    formatted_items = [
        PublicDataQualityProductItem(
            id=item.id,
            product_id=item.product_id or "",
            product_name=item.product_name,
            platform=item.platform,
            provider=item.provider,
            data_quality_category=item.data_quality_category,
            original_category=item.original_category,
            normalized_category=item.normalized_category or "Unknown",
            price=item.price,
            currency=item.currency,
            rating=item.rating,
            review_count=item.review_count,
            availability=item.availability,
            image=item.image,
            product_url=item.product_url,
            quality_score=item.quality_score,
            classification=item.classification,
            public_status=item.public_status,
            issues=item.issues,
            warnings=item.warnings,
            rejection_reasons=item.rejection_reasons,
            missing_fields=item.missing_fields,
            invalid_fields=item.invalid_fields,
            suspicious_fields=item.suspicious_fields,
            llm_used=item.llm_used,
            last_validated_time=item.last_validated_time
        )
        for item in items
    ]

    return PublicDataQualityFeedResponse(
        items=formatted_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get(
    "/stats",
    response_model=PublicDataQualityStatsResponse,
    summary="Public Transparency Statistics",
    description="Aggregated public audit metrics detailing real product inspection volumes, rejection rates, top failure modes, and platform health."
)
def get_public_stats(
    repo: DataQualityRepository = Depends(get_data_quality_repository)
):
    return repo.get_public_stats()

@router.get(
    "/history/{platform}/{product_id}",
    response_model=PublicDataQualityHistoryResponse,
    summary="Public Product Audit History",
    description="Permanent audit trail for a single marketplace product showing its evaluation history over time."
)
def get_product_validation_history(
    platform: str,
    product_id: str,
    limit: int = Query(50, ge=1, le=100),
    page: int = Query(1, ge=1),
    repo: DataQualityRepository = Depends(get_data_quality_repository)
):
    offset = (page - 1) * limit
    history_records = repo.get_product_validation_history(
        platform=platform,
        platform_product_id=product_id,
        limit=limit,
        offset=offset
    )

    status_map = {
        "rejected": "Rejected By Data Quality Checks",
        "valid_with_warnings": "Real Data With Warnings",
        "needs_review": "Needs Review",
        "valid": "Real Data"
    }

    formatted_history = []
    for r in history_records:
        pub_status = status_map.get(r.classification.lower(), "Real Data")
        dq_cat = "Data Quality Issues" if r.classification.lower() == "rejected" else (r.data_quality_category or "")
        norm_cat = r.normalized_category or "Unknown"
        reasons = r.rejection_reasons or ([iss.message for iss in r.issues] if r.classification.lower() == "rejected" else [])

        issues_dict = [iss.model_dump(mode="json") if hasattr(iss, "model_dump") else iss for iss in (r.issues or [])]
        warnings_dict = [w.model_dump(mode="json") if hasattr(w, "model_dump") else w for w in (r.warnings or [])]

        formatted_history.append(
            PublicDataQualityProductItem(
                id=r.id,
                product_id=r.platform_product_id or "",
                product_name=r.product_name or r.product_title or "Untitled Product",
                platform=r.platform,
                provider=r.source_provider,
                data_quality_category=dq_cat,
                original_category=r.original_category,
                normalized_category=norm_cat,
                price=r.price,
                currency=r.currency or "PKR",
                rating=r.rating,
                review_count=r.review_count or 0,
                availability=r.availability,
                image=r.image_url,
                product_url=r.product_url,
                quality_score=r.quality_score or r.overall_score,
                classification=r.classification,
                public_status=pub_status,
                issues=issues_dict,
                warnings=warnings_dict,
                rejection_reasons=reasons,
                missing_fields=r.missing_fields or [],
                invalid_fields=r.invalid_fields or [],
                suspicious_fields=r.suspicious_fields or [],
                llm_used=r.llm_used or r.used_llm,
                last_validated_time=r.validated_at
            )
        )

    return PublicDataQualityHistoryResponse(
        platform=platform,
        product_id=product_id,
        total_evaluations=len(formatted_history),
        history=formatted_history
    )
