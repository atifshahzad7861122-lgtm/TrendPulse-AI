import pytest
from backend.app.domain.classification import CategoryClassificationService

def test_category_3_tier_hierarchy():
    res = CategoryClassificationService.classify("HydroGlow thermal active lip serum formulation test")
    assert res.category == "Beauty & Personal Care"
    assert res.subcategory == "Skincare & Cosmetics"
    assert res.product_type == "Facial Serums & Lip Treatments"
    assert res.confidence >= 0.70
    assert res.classification_version == "2.4.0"

def test_category_fallback_unclassified():
    res = CategoryClassificationService.classify("Random generic unstructured words xyz 987")
    assert res.category == "Unclassified"
    assert res.subcategory == "Needs Review"
    assert res.product_type == "Unspecified Item"
    assert res.confidence < 0.50

def test_category_preserves_baseline_when_specified():
    res = CategoryClassificationService.classify("Vague text description", current_category="Consumer Electronics")
    assert res.category == "Consumer Electronics"
