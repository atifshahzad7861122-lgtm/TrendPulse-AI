"""
Centralized Search Limit Configuration for Marketplace Search Pipeline.

Phase 1 Canonical Architecture:
Internal candidate targets are distinct from the dashboard result limit.
The scraper pipeline collects 200 to 250+ candidates across providers
before normalization, data quality scoring, deduplication, and persistence.
The dashboard exposes a maximum of 30 verified products.
"""

MIN_CANDIDATES: int = 200
DEFAULT_CANDIDATE_TARGET: int = 250
DEFAULT_RESULT_LIMIT: int = 30
MAX_RESULT_LIMIT: int = 30
