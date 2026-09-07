import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.repositories.in_memory import data_quality_repo
from backend.app.models.domain import DataQualityValidationResult, DataQualityRuleViolation
from datetime import datetime, timezone

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_repo():
    data_quality_repo.clear()
    now = datetime.now(timezone.utc)

    # Seed 1 Rejected Record
    rej_record = DataQualityValidationResult(
        id="dqr_test_rej_101",
        agent_id="agent_data_quality",
        platform="daraz",
        source_provider="daraz_direct",
        platform_product_id="DARAZ_REJ_999",
        product_title="Fake High Quality Watch",
        product_name="Fake High Quality Watch",
        original_category="Watches",
        normalized_category="Smart Watches",
        data_quality_category="Data Quality Issues",
        product_url="https://daraz.pk/p/999",
        image_url="https://daraz.pk/img/999.jpg",
        price=-500.0,
        currency="PKR",
        rating=12.0,
        review_count=10,
        availability=True,
        overall_score=25.0,
        quality_score=25.0,
        classification="rejected",
        is_trusted=False,
        issues=[
            DataQualityRuleViolation(
                field="price",
                rule_name="impossible_negative_or_zero_price",
                severity="critical",
                message="Impossible price value: -500.0 (must be > 0.0).",
                observed_value=-500.0,
                penalty_score=40.0
            ),
            DataQualityRuleViolation(
                field="rating",
                rule_name="impossible_rating_range",
                severity="critical",
                message="Rating 12.0 is out of valid range [0.0, 5.0].",
                observed_value=12.0,
                penalty_score=35.0
            )
        ],
        rejection_reasons=[
            "Impossible price value: -500.0 (must be > 0.0).",
            "Rating 12.0 is out of valid range [0.0, 5.0]."
        ],
        missing_fields=[],
        invalid_fields=["price", "rating"],
        suspicious_fields=[],
        validated_at=now,
        created_at=now
    )
    data_quality_repo.save_validation_result(rej_record)

    # Seed 1 Valid Record
    val_record = DataQualityValidationResult(
        id="dqr_test_val_202",
        agent_id="agent_data_quality",
        platform="shopify",
        source_provider="shopify_official",
        platform_product_id="SHOP_VAL_888",
        product_title="Anker Soundcore Earbuds",
        product_name="Anker Soundcore Earbuds",
        original_category="Audio",
        normalized_category="Earbuds",
        data_quality_category="",
        product_url="https://shopify.com/p/888",
        image_url="https://shopify.com/img/888.jpg",
        price=7999.0,
        currency="PKR",
        rating=4.7,
        review_count=150,
        availability=True,
        overall_score=95.0,
        quality_score=95.0,
        classification="valid",
        is_trusted=True,
        issues=[],
        warnings=[],
        rejection_reasons=[],
        missing_fields=[],
        invalid_fields=[],
        suspicious_fields=[],
        validated_at=now,
        created_at=now
    )
    data_quality_repo.save_validation_result(val_record)


def test_public_rejected_endpoint():
    response = client.get("/api/v1/public/data-quality/rejected")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["product_name"] == "Fake High Quality Watch"
    assert item["platform"] == "daraz"
    assert item["public_status"] == "Rejected By Data Quality Checks"
    assert item["data_quality_category"] == "Data Quality Issues"
    assert item["normalized_category"] == "Smart Watches"
    assert item["price"] == -500.0
    assert len(item["rejection_reasons"]) == 2
    assert "price" in item["invalid_fields"]
    assert "rating" in item["invalid_fields"]

    # Security check: sensitive keys must not be present in JSON
    assert "workspace_id" not in item
    assert "raw_payload" not in item
    assert "llm_credentials" not in item


def test_public_feed_endpoint_with_filters():
    response = client.get("/api/v1/public/data-quality/feed?platform=shopify")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["product_name"] == "Anker Soundcore Earbuds"
    assert data["items"][0]["public_status"] == "Real Data"


def test_public_stats_endpoint():
    response = client.get("/api/v1/public/data-quality/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_inspected"] == 2
    assert data["total_rejected"] == 1
    assert data["total_valid"] == 1
    assert data["rejection_rate"] == 50.0
    assert data["clean_rate"] == 50.0
    assert len(data["top_rejection_reasons"]) > 0


def test_public_product_history_endpoint():
    response = client.get("/api/v1/public/data-quality/history/daraz/DARAZ_REJ_999")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "daraz"
    assert data["product_id"] == "DARAZ_REJ_999"
    assert data["total_evaluations"] == 1
    assert data["history"][0]["public_status"] == "Rejected By Data Quality Checks"
