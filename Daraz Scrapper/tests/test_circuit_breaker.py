"""Tests for CircuitBreaker states, thresholds, recovery timeouts, and transitions."""

import asyncio
import pytest
from app.core.circuit_breaker import CircuitBreaker
from app.core.constants import CircuitState
from app.core.exceptions import CircuitBreakerOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_initial_state():
    cb = CircuitBreaker(name="test_cb", failure_threshold=3, recovery_timeout=0.2, success_threshold=2)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.success_count == 0
    assert await cb.can_execute() is True


@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open_on_threshold():
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_timeout=0.2, success_threshold=2)

    async def _failing_task():
        raise RuntimeError("Target server unreachable")

    # First failure
    with pytest.raises(RuntimeError):
        await cb.execute(_failing_task)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    # Second failure -> trips to OPEN
    with pytest.raises(RuntimeError):
        await cb.execute(_failing_task)
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2

    # Subsequent execution is blocked
    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        await cb.execute(_failing_task)
    assert "is OPEN" in str(exc_info.value)
    assert exc_info.value.reset_timeout > 0


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_and_recovery():
    cb = CircuitBreaker(name="test_recovery_cb", failure_threshold=1, recovery_timeout=0.1, success_threshold=2)

    # Force open
    await cb.record_failure(RuntimeError("fail"))
    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(0.15)
    assert await cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # First success in HALF_OPEN
    await cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.success_count == 1

    # Second success in HALF_OPEN -> transitions to CLOSED
    await cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.success_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_manual_reset():
    cb = CircuitBreaker(name="test_reset_cb", failure_threshold=1)
    await cb.record_failure(RuntimeError("fail"))
    assert cb.state == CircuitState.OPEN

    await cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
