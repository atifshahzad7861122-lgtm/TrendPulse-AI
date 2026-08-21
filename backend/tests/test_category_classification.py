from backend.app.domain.classification import CategoryClassificationService

def test_classify_beauty_products():
    res = CategoryClassificationService.classify("HydroGlow Thermal Lip Serum color shift swatch")
    assert res.category == "Beauty & Personal Care"
    assert "Skincare" in res.subcategory or "Cosmetics" in res.subcategory
    assert res.confidence >= 0.5
    assert len(res.tags) > 0

def test_classify_sports_gear():
    res = CategoryClassificationService.classify("TitanFlex running vest for marathon training and hydration")
    assert res.category == "Sports & Outdoor"
    assert "Athletic" in res.subcategory or "Hydration" in res.subcategory
    assert res.confidence >= 0.5

def test_classify_electronics():
    res = CategoryClassificationService.classify("MagSnap foldable 3-in-1 magsafe wireless charger stand")
    assert res.category == "Consumer Electronics"
    assert "Mobile" in res.subcategory or "Audio" in res.subcategory
    assert res.confidence >= 0.5

def test_classify_home_kitchen():
    res = CategoryClassificationService.classify("Ceremonial Japanese matcha green tea whisk preparation")
    assert res.category in ["Home & Living", "Home & Kitchen"]
    assert "Beverage" in res.subcategory or "Ergonomics" in res.subcategory
    assert res.confidence >= 0.5
