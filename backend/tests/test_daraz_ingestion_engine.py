import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from backend.app.models.domain import (
    MarketplaceProduct, ProductMarketSnapshot, DarazIngestionRun,
    DarazDailyQuota, DarazTrainingDataset, DarazAuthSession, DarazSeller
)
from backend.app.repositories.in_memory import (
    InMemoryMarketplaceProductRepository, InMemoryDataQualityRepository
)
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.services.daraz.ingestion_engine import (
    DarazIngestionEngine, DarazIngestionConfig, IngestionProgressSummary
)


@pytest.fixture
def mock_repo():
    repo = InMemoryMarketplaceProductRepository(storage_file=":memory:")
    return repo


@pytest.fixture
def mock_dq_repo():
    return InMemoryDataQualityRepository(data_file=":memory:")


@pytest.fixture
def mock_official_provider(mock_repo):
    prov = DarazOfficialProvider(
        app_key="test_key_123",
        app_secret="test_secret_abc",
        access_token="test_valid_access_token",
        repository=mock_repo
    )
    return prov


def generate_mock_products(count: int, offset: int = 0) -> List[Dict[str, Any]]:
    items = []
    for i in range(count):
        idx = offset + i + 1
        items.append({
            "item_id": str(100000 + idx),
            "product_id": str(100000 + idx),
            "name": f"Daraz Test Product {idx}",
            "rating": 4.5 if idx % 2 == 0 else 3.8,
            "review_count": 25 if idx % 2 == 0 else 2,
            "seller_name": f"Test Seller {idx % 5}",
            "seller_id": f"seller_{idx % 5}",
            "attributes": {
                "name": f"Daraz Test Product {idx}",
                "brand": f"Brand {idx % 3}",
                "category_name": "Electronics",
                "Images": [f"https://img.daraz.pk/p/img_{idx}.jpg"]
            },
            "skus": [{
                "price": 1500.0 + idx * 10,
                "original_price": 2000.0 + idx * 10,
                "quantity": 10,
                "SellerSku": f"SKU-{idx}"
            }]
        })
    return items


def test_ingestion_engine_pagination_and_batch_processing(mock_official_provider, mock_repo, mock_dq_repo):
    """Test that the engine properly traverses multiple pages/offsets up to target_count."""
    config = DarazIngestionConfig(target_count=150, batch_size=50, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=mock_official_provider,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    call_offsets = []

    def mock_api_call(api_path, params, require_auth=True, method="GET"):
        offset = int(params.get("offset", 0))
        limit = int(params.get("limit", 50))
        call_offsets.append(offset)
        items = generate_mock_products(limit, offset=offset)
        return True, {"data": {"products": items, "total_products": 500}}, 200, None

    mock_official_provider._execute_api_call = mock_api_call

    progress = engine.execute_batch_ingestion(target_count=150)

    assert progress.status == "completed"
    assert progress.products_fetched == 150
    assert progress.products_inserted == 150
    assert progress.api_requests_consumed == 3
    assert call_offsets == [0, 50, 100]
    assert mock_repo.count_products(platform="daraz") == 150


def test_ingestion_engine_checkpoint_and_resume(mock_official_provider, mock_repo, mock_dq_repo):
    """Test that an interrupted run saves a checkpoint and resumes seamlessly."""
    config = DarazIngestionConfig(target_count=100, batch_size=50, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=mock_official_provider,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    call_count = 0

    def mock_api_call_with_interruption(api_path, params, require_auth=True, method="GET"):
        nonlocal call_count
        call_count += 1
        offset = int(params.get("offset", 0))
        if call_count == 1:
            items = generate_mock_products(50, offset=offset)
            return True, {"data": {"products": items, "total_products": 300}}, 200, None
        return False, None, 500, "Simulated transient upstream failure"

    mock_official_provider._execute_api_call = mock_api_call_with_interruption

    progress1 = engine.execute_batch_ingestion(target_count=100)
    assert progress1.status == "failed"
    assert progress1.products_fetched == 50
    assert progress1.current_offset == 50

    run_id = progress1.run_id
    saved_run = mock_repo.get_ingestion_run(run_id)
    assert saved_run is not None
    assert saved_run.metadata_json["current_offset"] == 50

    # Resume run
    def mock_api_call_resumed(api_path, params, require_auth=True, method="GET"):
        offset = int(params.get("offset", 0))
        items = generate_mock_products(50, offset=offset)
        return True, {"data": {"products": items, "total_products": 300}}, 200, None

    mock_official_provider._execute_api_call = mock_api_call_resumed

    progress2 = engine.execute_batch_ingestion(run_id=run_id, target_count=100, resume_from_checkpoint=True)
    assert progress2.status == "completed"
    assert progress2.products_fetched == 100
    assert mock_repo.count_products(platform="daraz") == 100


def test_ingestion_engine_duplicate_prevention_and_snapshots(mock_official_provider, mock_repo, mock_dq_repo):
    """Test idempotent re-ingestion: updates products without duplicating, creates snapshots."""
    config = DarazIngestionConfig(target_count=50, batch_size=50, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=mock_official_provider,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    items = generate_mock_products(50, offset=0)
    mock_official_provider._execute_api_call = lambda api_path, params, require_auth, method="GET": (
        True, {"data": {"products": items, "total_products": 50}}, 200, None
    )

    # First run
    p1 = engine.execute_batch_ingestion(target_count=50)
    assert p1.products_inserted == 50
    assert p1.duplicates_prevented == 0
    assert mock_repo.count_products(platform="daraz") == 50

    # Second run with same products
    p2 = engine.execute_batch_ingestion(target_count=50)
    assert p2.products_inserted == 0
    assert p2.products_updated == 50
    assert p2.duplicates_prevented == 50
    assert mock_repo.count_products(platform="daraz") == 50  # No duplicates created
    assert p2.snapshots_created == 50


def test_ingestion_engine_quota_safety_guard(mock_official_provider, mock_repo, mock_dq_repo):
    """Test that ingestion safely stops when daily quota margin is reached."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mock_repo._quotas[today_str] = DarazDailyQuota(
        id=f"quota_{today_str}",
        date=today_str,
        requests_used=5995000,
        daily_limit=6000000,
        remaining=5000,  # Below safety threshold of 10,000
        rate_limit_hits=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    config = DarazIngestionConfig(target_count=100, safety_quota_margin=10000, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=mock_official_provider,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    progress = engine.execute_batch_ingestion(target_count=100)
    assert progress.status == "partial"
    assert "Daily quota safety margin reached" in (progress.error_message or "")
    assert progress.products_fetched == 0


def test_ingestion_engine_rate_limit_backoff_and_recovery(mock_official_provider, mock_repo, mock_dq_repo):
    """Test handling 429 rate limit with backoff and eventual recovery."""
    config = DarazIngestionConfig(target_count=50, batch_size=50, max_retries=3, base_backoff_seconds=0.01, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=mock_official_provider,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    attempts = 0

    def mock_api_call_with_rate_limit(api_path, params, require_auth=True, method="GET"):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return False, None, 429, "Official Daraz API rate limit exceeded."
        items = generate_mock_products(50)
        return True, {"data": {"products": items, "total_products": 50}}, 200, None

    mock_official_provider._execute_api_call = mock_api_call_with_rate_limit

    progress = engine.execute_batch_ingestion(target_count=50)
    assert progress.status == "completed"
    assert progress.products_fetched == 50
    assert attempts == 3


def test_ingestion_engine_token_expiration_blocked_authorization(mock_official_provider, mock_repo, mock_dq_repo):
    """Test that token expiration immediately sets blocked_authorization state."""
    config = DarazIngestionConfig(target_count=50, batch_size=50, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=mock_official_provider,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    mock_official_provider._execute_api_call = lambda api_path, params, require_auth, method="GET": (
        False, None, 401, "AccessTokenExpired: The access token has expired."
    )

    progress = engine.execute_batch_ingestion(target_count=50)
    assert progress.status == "blocked_authorization"
    assert progress.error_code == 401
    assert "authorization required" in progress.error_message.lower()


def test_ingestion_engine_agent1_data_quality_and_training_filtering(mock_official_provider, mock_repo, mock_dq_repo):
    """Test that products flow through Agent 1 and only qualified items enter training dataset."""
    config = DarazIngestionConfig(target_count=20, batch_size=20, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=mock_official_provider,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    items = generate_mock_products(20)
    mock_official_provider._execute_api_call = lambda api_path, params, require_auth, method="GET": (
        True, {"data": {"products": items, "total_products": 20}}, 200, None
    )

    progress = engine.execute_batch_ingestion(target_count=20)
    assert progress.status == "completed"
    assert progress.agent1_valid > 0
    assert progress.training_eligible == 10
    training_items = mock_repo.list_training_dataset()
    assert len(training_items) == 10


def test_ingestion_engine_pause_and_stop_controls(mock_official_provider, mock_repo, mock_dq_repo):
    """Test pause and stop controls during execution."""
    config = DarazIngestionConfig(target_count=100, batch_size=20, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=mock_official_provider,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    chunk_count = 0

    def mock_api_call(api_path, params, require_auth=True, method="GET"):
        nonlocal chunk_count
        chunk_count += 1
        if chunk_count == 2:
            engine.pause()
        offset = int(params.get("offset", 0))
        items = generate_mock_products(20, offset=offset)
        return True, {"data": {"products": items, "total_products": 200}}, 200, None

    mock_official_provider._execute_api_call = mock_api_call

    progress = engine.execute_batch_ingestion(target_count=100)
    assert progress.status == "paused"
    assert progress.products_fetched == 40


def test_persisted_oauth_session_retrieval_and_standalone_runner(mock_repo, mock_dq_repo):
    """Test that provider and ingestion engine without in-memory token fetch persisted OAuth session."""
    # 1. Save an active OAuth session into repository
    now = datetime.now(timezone.utc)
    session = DarazAuthSession(
        id="daraz_sess_test_99",
        seller_id="seller_test_pk",
        account="Official Seller PK",
        access_token="persisted_live_access_token_12345",
        refresh_token="persisted_refresh_token_67890",
        expires_in=86400,
        status="authorized",
        authorized_at=now,
        created_at=now,
        updated_at=now
    )
    mock_repo.save_auth_session(session)

    # 2. Instantiate provider WITHOUT in-memory token
    unauthenticated_prov = DarazOfficialProvider(
        app_key="test_key_123",
        app_secret="test_secret_abc",
        access_token=None,
        repository=mock_repo
    )

    # 3. Provider resolves active token from repository session
    token, err = unauthenticated_prov.get_active_token()
    assert err is None
    assert token == "persisted_live_access_token_12345"

    # 4. Ingestion Engine executes using persisted session
    config = DarazIngestionConfig(target_count=20, batch_size=20, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=unauthenticated_prov,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    items = generate_mock_products(20)
    unauthenticated_prov._execute_api_call = lambda api_path, params, require_auth=True, method="GET": (
        True, {"data": {"products": items, "total_products": 20}}, 200, None
    )

    progress = engine.execute_batch_ingestion(target_count=20)
    assert progress.status == "completed"
    assert progress.products_fetched == 20


def test_missing_oauth_session_results_in_blocked_authorization(mock_repo, mock_dq_repo):
    """Test that missing session results in immediate blocked_authorization without calling API."""
    empty_prov = DarazOfficialProvider(
        app_key="test_key_123",
        app_secret="test_secret_abc",
        access_token=None,
        repository=mock_repo
    )

    api_called = False

    def mock_api_call(api_path, params, require_auth=True, method="GET"):
        nonlocal api_called
        api_called = True
        return True, {"data": {"products": []}}, 200, None

    empty_prov._execute_api_call = mock_api_call

    config = DarazIngestionConfig(target_count=50, batch_size=50, delay_between_requests=0.0)
    engine = DarazIngestionEngine(
        provider=empty_prov,
        repository=mock_repo,
        dq_repository=mock_dq_repo,
        config=config
    )

    progress = engine.execute_batch_ingestion(target_count=50)
    assert progress.status == "blocked_authorization"
    assert progress.error_code == 401
    assert "authorization required" in progress.error_message.lower()
    assert not api_called  # /products/get must NEVER be called without credentials


def test_expired_oauth_session_auto_refreshes_token(mock_repo, mock_dq_repo):
    """Test that expired session automatically triggers refresh_token flow."""
    past_time = datetime.now(timezone.utc) - timedelta(hours=25)
    expired_session = DarazAuthSession(
        id="daraz_sess_expired",
        seller_id="seller_exp",
        account="Exp Seller",
        access_token="old_expired_access_token",
        refresh_token="valid_refresh_token_123",
        expires_in=86400,  # 24h expired
        status="authorized",
        authorized_at=past_time,
        created_at=past_time,
        updated_at=past_time
    )
    mock_repo.save_auth_session(expired_session)

    prov = DarazOfficialProvider(
        app_key="test_key_123",
        app_secret="test_secret_abc",
        access_token=None,
        repository=mock_repo
    )

    # Mock refresh endpoint
    with patch.object(prov, "refresh_access_token") as mock_refresh:
        mock_refresh.return_value = (
            True,
            {"access_token": "newly_refreshed_access_token_999", "refresh_token": "valid_refresh_token_123", "expires_in": 86400},
            None
        )

        token, err = prov.get_active_token()
        assert err is None
        assert token == "newly_refreshed_access_token_999"
        mock_refresh.assert_called_once_with("valid_refresh_token_123")

        # Check that refreshed session was persisted back into repository
        saved = mock_repo.get_auth_session()
        assert saved.access_token == "newly_refreshed_access_token_999"


def test_expired_oauth_session_without_refresh_token_blocked(mock_repo, mock_dq_repo):
    """Test that expired session without refresh token gracefully blocks."""
    past_time = datetime.now(timezone.utc) - timedelta(hours=30)
    expired_session = DarazAuthSession(
        id="daraz_sess_no_refresh",
        seller_id="seller_no_ref",
        account="No Ref Seller",
        access_token="old_token",
        refresh_token=None,
        expires_in=86400,
        status="authorized",
        authorized_at=past_time,
        created_at=past_time,
        updated_at=past_time
    )
    mock_repo.save_auth_session(expired_session)

    prov = DarazOfficialProvider(
        app_key="test_key_123",
        app_secret="test_secret_abc",
        access_token=None,
        repository=mock_repo
    )

    token, err = prov.get_active_token()
    assert token is None
    assert "no refresh token is available" in (err or "").lower()


def test_token_secrecy_in_telemetry_and_metadata(mock_official_provider, mock_repo):
    """Test that secret and token parameters are NEVER recorded in telemetry or run metadata."""
    mock_official_provider._record_telemetry_and_quota(
        endpoint="/products/get",
        status_code=200,
        latency_ms=120.0,
        success=True,
        request_params={
            "app_key": "505830",
            "sign": "SECRET_SIGNATURE_HASH",
            "access_token": "SECRET_ACCESS_TOKEN",
            "filter": "all",
            "limit": "50"
        }
    )

    telemetry = mock_repo.get_api_telemetry()
    assert len(telemetry) == 1
    # Check that access_token, sign, app_key are absent from logged params
    logged = str(telemetry[0].model_dump())
    assert "SECRET_ACCESS_TOKEN" not in logged
    assert "SECRET_SIGNATURE_HASH" not in logged
