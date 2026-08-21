import concurrent.futures
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.repositories.in_memory import credit_repo, subscription_repo, user_repo
from backend.app.services.credit_service import CreditService
from backend.app.services.subscription_service import SubscriptionService

client = TestClient(app)

@pytest.fixture
def test_user_id():
    return "usr_credit_tester_101"

@pytest.fixture
def credit_service():
    return CreditService(credit_repo)

@pytest.fixture
def subscription_service(credit_service):
    return SubscriptionService(subscription_repo, credit_service)

def test_credit_account_creation_and_balance(credit_service, test_user_id):
    acc = credit_service.get_balance(test_user_id)
    assert acc.user_id == test_user_id
    assert acc.current_balance >= 0

def test_credit_grant_and_ledger(credit_service, test_user_id):
    initial_balance = credit_service.get_balance(test_user_id).current_balance
    tx = credit_service.grant_credits(
        user_id=test_user_id,
        amount=250,
        reason="Promotional bonus grant",
        reference_type="admin_grant",
        reference_id="promo_2026"
    )
    assert tx.amount == 250
    assert tx.transaction_type == "grant"
    assert tx.balance_before == initial_balance
    assert tx.balance_after == initial_balance + 250

    new_acc = credit_service.get_balance(test_user_id)
    assert new_acc.current_balance == initial_balance + 250

def test_credit_consume_success_and_ledger(credit_service, test_user_id):
    credit_service.grant_credits(test_user_id, 100, "Seed for consumption")
    balance_before = credit_service.get_balance(test_user_id).current_balance

    tx = credit_service.consume_credits(
        user_id=test_user_id,
        amount=30,
        feature="report_generation",
        action="export_pdf",
        reference_type="report_job",
        reference_id="rep_9999"
    )
    assert tx.amount == -30
    assert tx.transaction_type == "usage"
    assert tx.balance_before == balance_before
    assert tx.balance_after == balance_before - 30

    usage_history = credit_service.get_usage_history(test_user_id)
    assert any(u.reference_id == "rep_9999" and u.credits_used == 30 for u in usage_history)

def test_credit_consume_insufficient_and_negative_prevention(credit_service, test_user_id):
    acc = credit_service.get_balance(test_user_id)
    excess_amount = acc.current_balance + 5000

    with pytest.raises(Exception) as exc_info:
        credit_service.consume_credits(
            user_id=test_user_id,
            amount=excess_amount,
            feature="ai_analysis",
            action="deep_synthesis"
        )
    assert "Insufficient credits" in str(exc_info.value)
    # Ensure balance was not mutated
    assert credit_service.get_balance(test_user_id).current_balance == acc.current_balance

def test_credit_consumption_idempotency(credit_service, test_user_id):
    credit_service.grant_credits(test_user_id, 200, "Seed for idempotency test")
    initial_balance = credit_service.get_balance(test_user_id).current_balance

    # First request
    tx1 = credit_service.consume_credits(
        user_id=test_user_id,
        amount=50,
        feature="trend_prediction",
        action="forecast_velocity",
        reference_type="prediction_task",
        reference_id="pred_idempotent_01"
    )
    assert tx1.balance_after == initial_balance - 50

    # Duplicate request with same reference
    tx2 = credit_service.consume_credits(
        user_id=test_user_id,
        amount=50,
        feature="trend_prediction",
        action="forecast_velocity",
        reference_type="prediction_task",
        reference_id="pred_idempotent_01"
    )
    assert tx2.id == tx1.id
    # Ensure balance was NOT deducted again
    final_balance = credit_service.get_balance(test_user_id).current_balance
    assert final_balance == initial_balance - 50

def test_credit_refund_and_adjustment(credit_service, test_user_id):
    acc = credit_service.get_balance(test_user_id)
    bal_start = acc.current_balance

    # Refund
    refund_tx = credit_service.refund_credits(test_user_id, 40, "Failed prediction refund", reference_id="rep_9999")
    assert refund_tx.amount == 40
    assert refund_tx.transaction_type == "refund"
    assert refund_tx.balance_after == bal_start + 40

    # Positive Adjustment
    adj_tx = credit_service.adjust_credits(test_user_id, 10, "Manual balance correction")
    assert adj_tx.amount == 10
    assert adj_tx.balance_after == bal_start + 50

    # Negative Adjustment exceeding balance should fail
    with pytest.raises(Exception):
        credit_service.adjust_credits(test_user_id, -(bal_start + 1000), "Invalid negative adjustment")

def test_subscription_plans_listing(subscription_service):
    plans = subscription_service.list_plans()
    assert len(plans) >= 4
    slugs = [p.slug for p in plans]
    assert "free" in slugs
    assert "pro" in slugs
    assert "business" in slugs
    assert "enterprise" in slugs

def test_subscription_change_and_allocation(subscription_service, credit_service, test_user_id):
    # Start on Free
    sub = subscription_service.get_user_subscription(test_user_id)
    assert sub.status == "active"

    bal_before = credit_service.get_balance(test_user_id).current_balance

    # Upgrade to Business
    updated_sub = subscription_service.change_subscription(test_user_id, "business")
    assert updated_sub.status == "active"
    plan = subscription_service.get_plan_by_id(updated_sub.plan_id)
    assert plan.slug == "business"

    # Verify credit allocation occurred for Business plan (5000 credits)
    bal_after = credit_service.get_balance(test_user_id).current_balance
    assert bal_after >= bal_before + 5000

def test_subscription_cancellation(subscription_service, test_user_id):
    sub = subscription_service.cancel_subscription(test_user_id)
    assert sub.status == "cancelled"
    assert sub.cancelled_at is not None

def test_concurrent_credit_consumption_race_condition(credit_service):
    """
    Mandatory Concurrency Test:
    User has 100 credits.
    2 simultaneous requests each try to consume 80 credits.
    Exactly 1 must succeed and 1 must fail.
    Final balance must be exactly 20 (never -60).
    """
    concurrent_user = "usr_concurrent_race_tester"
    # Ensure fresh account with exactly 100 balance
    credit_repo.update_account_balance(concurrent_user, new_balance=100, delta_granted=0, delta_used=0)

    results = []
    errors = []

    def try_consume(req_id: str):
        try:
            tx = credit_service.consume_credits(
                user_id=concurrent_user,
                amount=80,
                feature="ai_analysis",
                action="batch_run",
                reference_type="batch_job",
                reference_id=f"job_{req_id}"
            )
            results.append(tx)
        except Exception as e:
            errors.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(try_consume, "req_A")
        f2 = executor.submit(try_consume, "req_B")
        concurrent.futures.wait([f1, f2])

    assert len(results) == 1, f"Expected exactly 1 success, got {len(results)}"
    assert len(errors) == 1, f"Expected exactly 1 failure, got {len(errors)}"

    final_balance = credit_service.get_balance(concurrent_user).current_balance
    assert final_balance == 20, f"Expected balance 20, got {final_balance}"

def test_credits_and_subscription_api_endpoints():
    # 1. Login to get token
    login_res = client.post("/api/v1/auth/login", json={
        "email": "demo@trendpulse.ai",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. GET /api/v1/credits/balance
    bal_res = client.get("/api/v1/credits/balance", headers=headers)
    assert bal_res.status_code == 200
    assert "current_balance" in bal_res.json()["data"]

    # 3. GET /api/v1/credits/transactions
    tx_res = client.get("/api/v1/credits/transactions", headers=headers)
    assert tx_res.status_code == 200
    assert isinstance(tx_res.json()["data"], list)

    # 4. GET /api/v1/credits/usage
    use_res = client.get("/api/v1/credits/usage", headers=headers)
    assert use_res.status_code == 200
    assert isinstance(use_res.json()["data"], list)

    # 5. GET /api/v1/subscription/plans
    plans_res = client.get("/api/v1/subscription/plans")
    assert plans_res.status_code == 200
    assert len(plans_res.json()["data"]) >= 4

    # 6. GET /api/v1/subscription
    sub_res = client.get("/api/v1/subscription", headers=headers)
    assert sub_res.status_code == 200
    assert "status" in sub_res.json()["data"]

    # 7. POST /api/v1/subscription/change
    change_res = client.post("/api/v1/subscription/change", headers=headers, json={"plan_slug": "pro"})
    assert change_res.status_code == 200
    assert change_res.json()["data"]["plan_slug"] == "pro"

    # 8. POST /api/v1/subscription/cancel
    cancel_res = client.post("/api/v1/subscription/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "cancelled"
