"""Daraz Pakistan Marketplace Discovery Engine module."""

from app.discovery.client import DarazDiscoveryClient
from app.discovery.config import DarazDiscoveryConfig, default_discovery_config
from app.discovery.detector import ChallengeDetectionResult, ChallengeDetector, challenge_detector
from app.discovery.engine import DarazDiscoveryEngine
from app.discovery.manual_intervention import ManualInterventionManager, manual_intervention_manager
from app.discovery.models import CategoryTarget, DiscoveryCheckpointState, DiscoveryRun, ProductTarget
from app.discovery.normalizer import (
    canonicalize_product_url,
    extract_category_id_from_url,
    extract_product_id,
    normalize_search_keyword,
    normalize_url,
)
from app.discovery.parser import DarazHTMLParser, PaginationResult, daraz_parser
from app.discovery.queue import ProductTargetQueue
from app.discovery.selectors import DarazSelectors
from app.discovery.strategies import (
    CategoryDiscoveryStrategy,
    KeywordDiscoveryStrategy,
    PaginationRunner,
    PaginationStrategy,
)

__all__ = [
    "DarazDiscoveryClient",
    "DarazDiscoveryConfig",
    "default_discovery_config",
    "ChallengeDetectionResult",
    "ChallengeDetector",
    "challenge_detector",
    "DarazDiscoveryEngine",
    "ManualInterventionManager",
    "manual_intervention_manager",
    "CategoryTarget",
    "DiscoveryCheckpointState",
    "DiscoveryRun",
    "ProductTarget",
    "normalize_url",
    "canonicalize_product_url",
    "extract_product_id",
    "extract_category_id_from_url",
    "normalize_search_keyword",
    "DarazHTMLParser",
    "PaginationResult",
    "daraz_parser",
    "ProductTargetQueue",
    "DarazSelectors",
    "CategoryDiscoveryStrategy",
    "KeywordDiscoveryStrategy",
    "PaginationRunner",
    "PaginationStrategy",
]
