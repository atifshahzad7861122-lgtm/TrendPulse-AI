"""Unit tests for deterministic FieldConfidenceScore and ConfidenceCalculator."""

import pytest

from app.extraction.confidence import (
    ConfidenceCalculator,
    ExtractionSource,
    FieldConfidenceScore,
)


def test_confidence_source_base_scores():
    score_struct = ConfidenceCalculator.score_field("title", ExtractionSource.STRUCTURED_DATA, has_value=True)
    score_jsonld = ConfidenceCalculator.score_field("title", ExtractionSource.JSON_LD, has_value=True)
    score_dom = ConfidenceCalculator.score_field("title", ExtractionSource.DOM, has_value=True)
    score_og = ConfidenceCalculator.score_field("title", ExtractionSource.OPENGRAPH, has_value=True)
    score_fallback = ConfidenceCalculator.score_field("title", ExtractionSource.FALLBACK, has_value=True)

    assert score_struct.confidence == 0.98
    assert score_jsonld.confidence == 0.95
    assert score_dom.confidence == 0.88
    assert score_og.confidence == 0.78
    assert score_fallback.confidence == 0.55


def test_confidence_missing_field_zero():
    score = ConfidenceCalculator.score_field("price", ExtractionSource.DOM, has_value=False)
    assert score.confidence == 0.0
    assert score.is_valid is False


def test_calculate_overall_weighted_confidence():
    field_scores = {
        "title": ConfidenceCalculator.score_field("title", ExtractionSource.STRUCTURED_DATA, has_value=True),
        "price": ConfidenceCalculator.score_field("price", ExtractionSource.STRUCTURED_DATA, has_value=True),
        "images": ConfidenceCalculator.score_field("images", ExtractionSource.JSON_LD, has_value=True),
        "seller": ConfidenceCalculator.score_field("seller", ExtractionSource.DOM, has_value=True),
        "category": ConfidenceCalculator.score_field("category", ExtractionSource.DOM, has_value=True),
        "rating": ConfidenceCalculator.score_field("rating", ExtractionSource.JSON_LD, has_value=True),
        "description": ConfidenceCalculator.score_field("description", ExtractionSource.DOM, has_value=True),
        "specifications": ConfidenceCalculator.score_field("specifications", ExtractionSource.DOM, has_value=True),
    }

    overall = ConfidenceCalculator.calculate_overall_confidence(field_scores)
    assert 0.90 <= overall <= 1.0
